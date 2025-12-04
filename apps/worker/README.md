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

## 约定

- 仅从 `libs/` 导入共享逻辑，例如 `libs.py_core`。
- 不直接依赖 `third_party/` 中的任何代码或路径。
- 所有模型路径基于环境变量 `MODELS_DIR` 计算。
