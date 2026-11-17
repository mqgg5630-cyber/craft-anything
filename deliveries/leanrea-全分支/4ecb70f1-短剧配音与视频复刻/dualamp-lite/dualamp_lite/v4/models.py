"""Frozen M1 / M2 / M3 architectures (V4 section 9).

M1  ESM-2 mean (480) -> Linear 128, physchem (32) -> Linear 64,
    concat 192 -> MLP 64 -> 1                          [global semantics]

M2  residue (L, 480) -> Linear 480->128 -> Conv1d k=3/5/7 (64 channels each,
    GELU) -> masked global max per kernel -> concat 192 -> Linear 192->128
    -> GELU -> Dropout -> MLP -> 1                     [local patterns]

M3  M2's CNN branch (128) + physchem branch (64) -> concat 192
    -> Linear 64 -> GELU -> Dropout -> 1               [dual branch, NO extra
                                                        global pooling]

The channel counts, kernel sizes, pooling type and the absence of any extra
pooling in M3 are part of the frozen definition: changing them under the same
version name invalidates every reported number. Cross-attention / gated fusion /
LoRA are explicitly out of scope (V4 section 9).
"""

from __future__ import annotations

import torch
import torch.nn as nn

TORCH_MODELS = ("M1", "M2", "M3")
BASELINE_MODELS = ("M0_RF", "M0_HGB")
CNN_CHANNELS = 64
CNN_KERNELS = (3, 5, 7)
ESM_PROJ = 128
PHYS_PROJ = 64


def masked_max(x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    """Masked global max over the residue axis.

    ``x``    (B, C, L)
    ``mask`` (B, L) with 1 for real residues
    """

    if x.shape[-1] != mask.shape[-1]:
        raise ValueError(f"mask length {mask.shape[-1]} != feature length {x.shape[-1]}")
    keep = mask.unsqueeze(1).to(dtype=torch.bool)
    filled = x.masked_fill(~keep, torch.finfo(x.dtype).min)
    out = filled.max(dim=-1).values
    empty = ~keep.any(dim=-1).squeeze(1)
    if bool(empty.any()):
        raise ValueError("masked_max received an all-padding sequence")
    return out


class MLPHead(nn.Module):
    def __init__(self, in_dim: int, hidden: int = 64, dropout: float = 0.3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


class M1(nn.Module):
    """Global ESM-2 mean + physicochemical vector."""

    def __init__(self, embed_dim: int = 480, n_phys: int = 32, dropout: float = 0.3):
        super().__init__()
        self.esm_proj = nn.Sequential(nn.Linear(embed_dim, ESM_PROJ), nn.GELU())
        self.phys_proj = nn.Sequential(nn.Linear(n_phys, PHYS_PROJ), nn.GELU())
        self.head = MLPHead(ESM_PROJ + PHYS_PROJ, hidden=64, dropout=dropout)

    def forward(self, mean=None, phys=None, residue=None, mask=None) -> torch.Tensor:
        if mean is None or phys is None:
            raise ValueError("M1 needs mean and phys")
        return self.head(torch.cat([self.esm_proj(mean), self.phys_proj(phys)], dim=-1))


class ResidueBranch(nn.Module):
    """Residue projection + multi-scale CNN + masked max + 192->128 compression."""

    def __init__(self, embed_dim: int = 480, dropout: float = 0.3):
        super().__init__()
        self.proj = nn.Linear(embed_dim, ESM_PROJ)
        self.convs = nn.ModuleList(
            nn.Conv1d(ESM_PROJ, CNN_CHANNELS, k, padding=k // 2) for k in CNN_KERNELS
        )
        self.act = nn.GELU()
        self.compress = nn.Sequential(
            nn.Linear(CNN_CHANNELS * len(CNN_KERNELS), 128),
            nn.GELU(),
            nn.Dropout(dropout),
        )

    def forward(self, residue: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        if residue is None or mask is None:
            raise ValueError("the residue branch needs residue and mask")
        keep = mask.unsqueeze(-1).to(residue.dtype)
        residue = residue * keep  # padding embeddings must never leak into a convolution
        x = self.act(self.proj(residue)).transpose(1, 2)  # (B, 128, L)
        pooled = [masked_max(conv(x), mask) for conv in self.convs]
        return self.compress(torch.cat(pooled, dim=-1))


class M2(nn.Module):
    """Residue branch only."""

    def __init__(self, embed_dim: int = 480, n_phys: int = 32, dropout: float = 0.3):
        super().__init__()
        self.branch = ResidueBranch(embed_dim, dropout)
        self.head = MLPHead(128, hidden=64, dropout=dropout)

    def forward(self, mean=None, phys=None, residue=None, mask=None) -> torch.Tensor:
        return self.head(self.branch(residue, mask))


class M3(nn.Module):
    """Dual branch: residue CNN (128) + physicochemical MLP (64) = 192 -> 64."""

    def __init__(self, embed_dim: int = 480, n_phys: int = 32, dropout: float = 0.3):
        super().__init__()
        self.branch = ResidueBranch(embed_dim, dropout)
        self.phys_proj = nn.Sequential(nn.Linear(n_phys, PHYS_PROJ), nn.GELU())
        self.fuse = nn.Sequential(
            nn.Linear(128 + PHYS_PROJ, 64),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1),
        )

    def forward(self, mean=None, phys=None, residue=None, mask=None) -> torch.Tensor:
        fused = torch.cat([self.branch(residue, mask), self.phys_proj(phys)], dim=-1)
        return self.fuse(fused).squeeze(-1)


_REGISTRY = {"M1": M1, "M2": M2, "M3": M3}


def build_model(name: str, embed_dim: int = 480, n_phys: int = 32, dropout: float = 0.3) -> nn.Module:
    if name not in _REGISTRY:
        raise KeyError(f"unknown model {name!r}; available: {sorted(_REGISTRY)}")
    return _REGISTRY[name](embed_dim=embed_dim, n_phys=n_phys, dropout=dropout)


def count_parameters(model: nn.Module) -> int:
    return int(sum(p.numel() for p in model.parameters() if p.requires_grad))


def describe() -> dict[str, dict]:
    """Static description used in the config and the model card."""

    return {
        "M1": {
            "inputs": ["esm_mean(480)", "physchem(32)"],
            "layers": "Linear(480,128)+GELU | Linear(32,64)+GELU | concat 192 | Linear(192,64)+GELU+Dropout | Linear(64,1)",
            "pooling": "ESM-2 official mean over real residues",
        },
        "M2": {
            "inputs": ["esm_residue(L,480)", "mask(L)"],
            "layers": "Linear(480,128) | Conv1d k=3/5/7 x64 + GELU | masked max | concat 192 | Linear(192,128)+GELU+Dropout | Linear(128,64)+GELU+Dropout | Linear(64,1)",
            "pooling": "masked global max per kernel",
        },
        "M3": {
            "inputs": ["esm_residue(L,480)", "mask(L)", "physchem(32)"],
            "layers": "M2 CNN branch (128) + Linear(32,64)+GELU | concat 192 | Linear(192,64)+GELU+Dropout | Linear(64,1)",
            "pooling": "masked global max only - no extra global pooling",
        },
    }
