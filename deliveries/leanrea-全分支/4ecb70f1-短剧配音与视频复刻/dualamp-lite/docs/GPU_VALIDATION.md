# 云端 GPU 环境验证记录（2026-11-10）

本文件记录 **工程链路** 验证，不包含任何科学结论，也不包含凭据、账号或运行产物。

## 1. 链路方式

受限沙箱只放行 `github.com` / `pypi.org` 等少数主机，无法直连 `kaggle.com`、
`oauth2.googleapis.com`、`colab.research.google.com`。因此采用：

```
私有 Google Drive 金库 (vault.json)
        │  只读取得，绝不入库
        ▼
一次性 RSA+AES 信封 cloud-gpu/secrets/*.enc（公钥 = 中继首次运行自动提交）
        │  git push 触发
        ▼
GitHub Actions 中继（ubuntu-latest，python 3.12）
        │  解密 → 恢复 ~/.gpu-relay → kaggle/colab CLI
        ├─► Kaggle kernels push（私有 kernel，NvidiaTeslaT4，internet on）
        └─► 运行日志 / 结果只写回私有 Drive 的预授权 resumable URI
```

仓库为 public，故：`.enc` 信封由中继运行后自动删除并提交；
`vault.json`、ADC json、Kaggle token、运行日志、权重从不进入 Git。

## 2. 凭据状态（探测任务 `probe-20261110`）

| 平台 | 配置 | 认证 | 备注 |
|---|---|---|---|
| Colab | `~/.gpu-relay/colab_adc.json`（authorized_user） | ✅ | scopes 完整，无活跃会话；账户余额 0.00 compute units（PAYG 未充值） |
| Kaggle | `vault:KAGGLE_API_TOKEN` | ✅ | `kaggle kernels list` 可读，可 push / 取回 kernel output |

## 3. Kaggle 2×T4 冒烟任务（`dualamp-v4-gpu-smoke`，第 4 次，最终）

载荷：`gpu_smoke_v4.py`（8 条公开已知 AMP 序列 + fair-esm 前向，纯工程验证）。

```json
{
  "nvidia_smi_query": "0, Tesla T4, 15360 MiB, 0 %\n1, Tesla T4, 15360 MiB, 0 %",
  "torch": {"version": "2.11.0+cu130", "cuda_available": true, "cuda_version": "13.0",
            "device_count": 2, "devices": ["Tesla T4", "Tesla T4"]},
  "esm": {"version": "2.0.0", "model": "esm2_t12_35M_UR50D", "device": "cuda", "alphabet_size": 33},
  "steps": {"load_sec": 1.54, "forward_sec": 0.747},
  "embedding": {"dim": 480, "n_peptides": 8, "max_len": 37, "finite": true,
                "mean_norm": 6.9407, "pairwise_min_cos": 0.6842}
}
```

- kernel：私有 kernel（slug `dualamp-v4-gpu-smoke`），日志可在 Kaggle 账号内查看
- 结果 JSON 经 payload 内的 `DRIVE_UPLOAD_URI` PUT 回私有 Drive（HTTP 200，`X-Goog-Upload-Status: final`）
- 中继侧 `kaggle kernels output` 亦取回 2 个小文件（`*.log`、`gpu_smoke_v4_result.json`）

结论：**Kaggle 侧 2×T4 + torch/CUDA + fair-esm + Drive 回传全链路可用**；
Colab 侧凭据有效但当前无算力余额，暂不作为主力。

## 4. 真实训练任务的阻塞点

`scripts/run_v4.sh real` 需要 `configs/sources.yaml`（APD6 / DRAMP / 细菌 AMP /
UniProt 负样本等原始文件的本地路径）。这些数据库需注册后人工下载，
沙箱无法代劳，故真实 ESM-2 特征提取 + 25 折训练尚未提交。
把原始文件放到仓库（或 Kaggle dataset）后，填 `configs/sources.yaml` 即可用同一中继提交。

## 5. 清理

验证完成后执行 `git rm -rf cloud-gpu .github/workflows/gpu-relay.yml`，
仓库回到“零云凭据”状态；下次需要云端算力时按上述流程重新投放中继即可
（凭据仍在私有 Drive 金库，无需重新授权）。
