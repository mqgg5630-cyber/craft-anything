"""Torch model zoo of plan §3.2 (M0-CNN-BiGRU, M1, M2, M3 + optional M4/M5).

The V3 review killed the original single-token "cross-attention": with Key/Value
length 1, softmax is identically 1 and the block is a scaled identity. The main
model is therefore a **Concat** fusion (128-d CNN branch + 64-d biophys MLP =
192-d); M4 here is a *real* multi-token cross-attention (35 feature tokens as
queries, residue states as keys/values) and stays optional, as the plan requires.

All models take:

    residue  (B, L, D) float32   ESM-2 residue states (or one-hot for M0)
    mask     (B, L)    bool      True for real residues
    physio   (B, F)    float32   standardised biophysical features

and return a single logit per peptide.
"""

from __future__ import annotations

from typing import Sequence

import torch
import torch.nn as nn
import torch.nn.functional as F

from .config import STANDARD_AA

AA_TO_INDEX = {aa: i + 1 for i, aa in enumerate(STANDARD_AA)}  # 0 = padding


# --------------------------------------------------------------------------- #
# building blocks
# --------------------------------------------------------------------------- #


def masked_max(x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    """x: (B, L, C), mask: (B, L) -> (B, C)."""

    neg = torch.finfo(x.dtype).min
    x = x.masked_fill(~mask.unsqueeze(-1), neg)
    out = x.max(dim=1).values
    return out.masked_fill(~mask.any(dim=1, keepdim=True), 0.0)


def masked_mean(x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    weights = mask.unsqueeze(-1).to(x.dtype)
    return (x * weights).sum(1) / weights.sum(1).clamp_min(1.0)


class MultiScaleCNN(nn.Module):
    """k = 3/5/7 convolutions over residue states -> 128-d motif vector."""

    def __init__(self, in_dim: int, hidden: int = 64, out_dim: int = 128,
                 kernels: Sequence[int] = (3, 5, 7), dropout: float = 0.1) -> None:
        super().__init__()
        self.convs = nn.ModuleList(
            nn.Conv1d(in_dim, hidden, kernel_size=k, padding=k // 2) for k in kernels
        )
        self.norms = nn.ModuleList(nn.BatchNorm1d(hidden) for _ in kernels)
        self.proj = nn.Linear(hidden * len(kernels), out_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, residue: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        h = residue.transpose(1, 2)  # (B, D, L)
        pooled = []
        for conv, norm in zip(self.convs, self.norms):
            z = F.gelu(norm(conv(h)))  # (B, hidden, L)
            z = z.transpose(1, 2)      # (B, L, hidden)
            pooled.append(masked_max(z, mask))
        return self.dropout(F.gelu(self.proj(torch.cat(pooled, dim=-1))))


class PhysioEncoder(nn.Module):
    """Biophysical priors -> 64-d embedding (no BatchNorm: F is small and noisy)."""

    def __init__(self, in_dim: int, out_dim: int = 64, dropout: float = 0.1) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.LayerNorm(in_dim),
            nn.Linear(in_dim, out_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(out_dim, out_dim),
            nn.GELU(),
        )

    def forward(self, physio: torch.Tensor) -> torch.Tensor:
        return self.net(physio)


class MLPHead(nn.Module):
    def __init__(self, in_dim: int, hidden: int = 64, dropout: float = 0.3) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


# --------------------------------------------------------------------------- #
# peptide models
# --------------------------------------------------------------------------- #


class MeanPoolMLP(nn.Module):
    """M1 - ESM-2 masked-mean + shallow MLP (the honest baseline of §3.2)."""

    def __init__(self, embed_dim: int = 480, n_physio: int = 0, hidden: int = 256,
                 dropout: float = 0.3) -> None:
        super().__init__()
        self.use_physio = n_physio > 0
        self.physio = PhysioEncoder(n_physio, 64, dropout) if self.use_physio else None
        in_dim = embed_dim + (64 if self.use_physio else 0)
        self.head = MLPHead(in_dim, hidden, dropout)

    def forward(self, residue, mask, physio, mean=None):
        if mean is None:
            mean = masked_mean(residue, mask)
        x = mean
        if self.use_physio:
            x = torch.cat([x, self.physio(physio)], dim=-1)
        return self.head(x)


class ResidueCNN(nn.Module):
    """M2 - ESM-2 residue states + multi-scale CNN (no biophysical branch)."""

    def __init__(self, embed_dim: int = 480, n_physio: int = 0, cnn_dim: int = 128,
                 dropout: float = 0.3) -> None:
        super().__init__()
        self.use_physio = n_physio > 0
        self.cnn = MultiScaleCNN(embed_dim, hidden=64, out_dim=cnn_dim, dropout=dropout * 0.5)
        self.head = MLPHead(cnn_dim, 64, dropout)

    def forward(self, residue, mask, physio, mean=None):
        return self.head(self.cnn(residue, mask))


class ConcatDual(nn.Module):
    """M3 - the main model: 128-d CNN branch + 64-d biophys branch -> MLP.

    Concat is deliberate (plan §3.2): stable, cheap, easy to ablate. ``use_physio``
    toggles the ablation "M3 minus biophysical priors", which must be compared
    against M3 before claiming the dual branch helps.
    """

    def __init__(self, embed_dim: int = 480, n_physio: int = 35, cnn_dim: int = 128,
                 physio_dim: int = 64, dropout: float = 0.3, use_physio: bool = True) -> None:
        super().__init__()
        self.use_physio = use_physio and n_physio > 0
        self.cnn = MultiScaleCNN(embed_dim, hidden=64, out_dim=cnn_dim, dropout=dropout * 0.5)
        self.physio = PhysioEncoder(n_physio, physio_dim, dropout) if self.use_physio else None
        fused = cnn_dim + (physio_dim if self.use_physio else 0)
        self.fusion_dim = fused
        self.head = MLPHead(fused, 64, dropout)

    def forward(self, residue, mask, physio, mean=None):
        parts = [self.cnn(residue, mask)]
        if self.use_physio:
            parts.append(self.physio(physio))
        return self.head(torch.cat(parts, dim=-1))


class CrossAttentionDual(nn.Module):
    """M4 (optional) - biophysical features as 35 query tokens attend to residues.

    This is a genuine cross-attention: query length = n_physio > 1, key/value
    length = peptide length > 1, so the attention weights are not degenerate.
    """

    def __init__(self, embed_dim: int = 480, n_physio: int = 35, d_model: int = 64,
                 heads: int = 4, dropout: float = 0.3) -> None:
        super().__init__()
        self.n_physio = n_physio
        self.query = nn.Parameter(torch.randn(1, n_physio, d_model) * 0.02)
        self.feature_embed = nn.Parameter(torch.randn(1, n_physio, d_model) * 0.02)
        self.physio_proj = nn.Sequential(nn.LayerNorm(n_physio), nn.Linear(n_physio, n_physio * d_model))
        self.key_value = nn.Linear(embed_dim, d_model)
        self.attn = nn.MultiheadAttention(d_model, heads, dropout=dropout, batch_first=True)
        self.norm = nn.LayerNorm(d_model)
        self.head = MLPHead(d_model, 64, dropout)

    def forward(self, residue, mask, physio, mean=None):
        b = residue.size(0)
        # query tokens = learned feature-type tokens modulated by the peptide's values
        phi = self.physio_proj(physio).view(b, self.n_physio, -1)
        query = self.query.expand(b, -1, -1) + self.feature_embed.expand(b, -1, -1) + phi
        kv = self.key_value(residue)
        attn, _ = self.attn(query, kv, kv, key_padding_mask=~mask, need_weights=False)
        pooled = self.norm(attn).mean(dim=1)
        return self.head(pooled)


class GatedFusionDual(nn.Module):
    """M5 (optional) - sigmoid gate over the two branches (FiLM-style variant)."""

    def __init__(self, embed_dim: int = 480, n_physio: int = 35, dim: int = 96,
                 dropout: float = 0.3) -> None:
        super().__init__()
        self.cnn = MultiScaleCNN(embed_dim, hidden=64, out_dim=dim, dropout=dropout * 0.5)
        self.physio = PhysioEncoder(n_physio, dim, dropout)
        self.gate = nn.Sequential(nn.Linear(2 * dim, dim), nn.Sigmoid())
        self.head = MLPHead(dim, 64, dropout)

    def forward(self, residue, mask, physio, mean=None):
        a = self.cnn(residue, mask)
        b = self.physio(physio)
        g = self.gate(torch.cat([a, b], dim=-1))
        return self.head(g * a + (1.0 - g) * b)


class CNNBiGRU(nn.Module):
    """M0-CNN-BiGRU - trained from scratch, no ESM-2 (baseline of §3.2)."""

    def __init__(self, vocab: int = len(STANDARD_AA) + 1, embed_dim: int = 32, cnn_dim: int = 64,
                 gru_hidden: int = 64, dropout: float = 0.3, n_physio: int = 0) -> None:
        super().__init__()
        self.embedding = nn.Embedding(vocab, embed_dim, padding_idx=0)
        self.convs = nn.ModuleList(nn.Conv1d(embed_dim, cnn_dim, k, padding=k // 2) for k in (3, 5, 7))
        self.gru = nn.GRU(cnn_dim * 3, gru_hidden, batch_first=True, bidirectional=True)
        self.attention = nn.Linear(2 * gru_hidden, 1)
        self.head = MLPHead(2 * gru_hidden, 64, dropout)

    def forward_tokens(self, tokens, mask):
        x = self.embedding(tokens)
        h = x.transpose(1, 2)
        feats = torch.cat([F.gelu(conv(h)) for conv in self.convs], dim=1)
        seq, _ = self.gru(feats.transpose(1, 2))
        scores = self.attention(seq).squeeze(-1).masked_fill(~mask, -1e4)
        weights = torch.softmax(scores, dim=1).unsqueeze(-1)
        pooled = (seq * weights).sum(1)
        return self.head(pooled)


# --------------------------------------------------------------------------- #
# factory
# --------------------------------------------------------------------------- #


def build_model(name: str, embed_dim: int = 480, n_physio: int = 35, dropout: float = 0.3):
    name = name.upper()
    if name == "M1":
        return MeanPoolMLP(embed_dim=embed_dim, n_physio=0, dropout=dropout)
    if name == "M1P":
        return MeanPoolMLP(embed_dim=embed_dim, n_physio=n_physio, dropout=dropout)
    if name == "M2":
        return ResidueCNN(embed_dim=embed_dim, n_physio=0, dropout=dropout)
    if name == "M3":
        return ConcatDual(embed_dim=embed_dim, n_physio=n_physio, dropout=dropout, use_physio=True)
    if name == "M3_NOPHYS":
        return ConcatDual(embed_dim=embed_dim, n_physio=n_physio, dropout=dropout, use_physio=False)
    if name == "M4":
        return CrossAttentionDual(embed_dim=embed_dim, n_physio=n_physio, dropout=dropout)
    if name == "M5":
        return GatedFusionDual(embed_dim=embed_dim, n_physio=n_physio, dropout=dropout)
    if name in ("M0_CNN_BIGRU", "M0-CNN-BIGRU"):
        return CNNBiGRU(n_physio=n_physio, dropout=dropout)
    raise ValueError(f"unknown model {name!r}")


TORCH_MODELS = ("M1", "M1P", "M2", "M3", "M3_NOPHYS", "M4", "M5", "M0_CNN_BIGRU")
BASELINE_MODELS = ("M0_RF", "M0_HGB", "M0_LOGREG")


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
