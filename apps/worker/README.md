# SteadyDancer Worker

后台 Worker 服务，用于执行耗时任务（如模型推理、图像后处理等）。

Worker 基于 Celery 队列实现任务消费。

## 启动方式（开发环境：Celery worker）

在仓库根目录执行：

```bash
cp apps/worker/.env.example apps/worker/.env
uv run --project apps/worker celery -A apps.worker.celery_app worker -l info
```

后续会提供脚本：

```bash
scripts/dev_worker.sh
```

用于自动加载 `.env` 并以统一参数启动 worker。

## 使用 DFloat11 压缩模型

Worker 已内置对 `models/SteadyDancer-14B-df11` 的推理支持，建议在显存较小的显卡上开启：

- 首先在仓库根目录运行一次离线压缩脚本（使用 worker 环境）：

  ```bash
  uv run --project apps/worker python scripts/compress_steadydancer_dfloat11.py
  ```

  默认会将 `${MODELS_DIR}/SteadyDancer-14B` 压缩到 `${MODELS_DIR}/SteadyDancer-14B-df11`。

- 在 `apps/worker/.env` 中开启 DF11：

  ```env
  STEADYDANCER_USE_DF11=1
  # 可选：显式指定 DF11 目录
  # STEADYDANCER_DF11_DIR=./models/SteadyDancer-14B-df11
  # 可选：启用 CPU Offload（默认 1，适合 3080）
  STEADYDANCER_DF11_CPU_OFFLOAD=1
  # 可选：多卡自动切分（实验性，双 3080 可尝试设为 1）
  STEADYDANCER_DF11_DEVICE_MAP_AUTO=0
  ```

- 多卡建议：
  - 最简单的方式是在 shell 层通过 `CUDA_VISIBLE_DEVICES` 启动多个 worker，每个 worker 固定到一张卡；
  - 若希望单次推理横跨多张 GPU，可尝试将 `STEADYDANCER_DF11_DEVICE_MAP_AUTO` 设为 `1`，由 Accelerate 自动将 DF11 主干切到多卡（实验性特性，出现问题时建议关闭）。

## 约定

- 仅从 `libs/` 导入共享逻辑，例如 `libs.py_core`。
- 不直接依赖 `third_party/` 中的任何代码或路径。
- 所有模型路径基于环境变量 `MODELS_DIR` 计算。
