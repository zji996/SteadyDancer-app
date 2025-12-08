# SteadyDancer Monorepo Quickstart

本文档面向本仓库的本地开发者，帮助你从零到「能跑通一次 SteadyDancer 推理」的最小路径。

建议先通读根目录 `AGENTS.md` 与 `docs/architecture.md`，理解整体结构与约束。

---

## 1. 前置准备

- 基础工具：
  - Git（支持 submodule）
  - Docker + Docker Compose
  - Python 3.14（建议使用 uv 管理）
  - Node.js / npm（用于 Web 前端）
- 可选（GPU 推理）：
  - NVIDIA GPU + 对应版本的 CUDA 驱动 / toolkit

### 1.1 克隆仓库并拉取 submodule

```bash
git clone <this-repo-url> SteadyDancer-app
cd SteadyDancer-app

git submodule update --init --recursive
```

`third_party/` 下会包含：

- `third_party/SteadyDancer`
- `third_party/DFloat11`

---

## 2. Python 环境（uv）与后端依赖

本仓库的后端应用（API / Worker）均使用 uv 管理依赖，每个 app 是独立的 uv project。

### 2.1 安装 uv

参考 uv 官方文档进行安装，例如（如已安装可跳过）：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

确认版本（建议 0.5.3+）：

```bash
uv --version
```

### 2.2 同步依赖

在仓库根目录执行：

```bash
# API 依赖
uv sync --project apps/api

# Worker 依赖（包含 Celery + SteadyDancer 推理栈）
uv sync --project apps/worker
```

Worker 会按照 `apps/worker/pyproject.toml` 中的配置从 PyTorch 官方 cu130 索引安装 `torch` / `torchvision` 等依赖。

如在低内存环境编译 `flash-attn`，建议限制并发：

```bash
MAX_JOBS=3 uv sync --project apps/worker
```

---

## 3. 下载 SteadyDancer 模型权重

模型权重统一放在 `MODELS_DIR`（默认 `<repo_root>/models`）下，通过脚本下载，禁止手动提交权重到 Git。

### 3.1 配置 MODELS_DIR（可选）

在仓库根目录复制全局环境示例：

```bash
cp .env.example .env
```

根据需要调整其中的：

- `MODELS_DIR`（默认 `./models`）
- `STEADYDANCER_CKPT_DIR`（可留空，默认 `<MODELS_DIR>/SteadyDancer-14B`）

### 3.2 使用脚本下载模型


# 从仓库根目录运行
uv run --project apps/api python scripts/download_models.py
```

这会将 `MCG-NJU-SteadyDancer-14B` 模型下载到：

- 默认：`<MODELS_DIR>/SteadyDancer-14B`

如需改用 HuggingFace：

```bash
pip install "huggingface_hub>=0.23"

uv run --project apps/api python scripts/download_models.py --source huggingface
```

脚本结束时会打印实际下载路径，可将其填入 `.env` / `STEADYDANCER_CKPT_DIR` 中，以供 Worker 使用。

---

## 4. 启动本地依赖与服务

### 4.1 准备各服务的环境变量

首次启动前，建议先为 API / Worker / Web 准备 `.env` 文件（可根据实际需要调整）：

```bash
cp apps/api/.env.example apps/api/.env
cp apps/worker/.env.example apps/worker/.env
cp apps/web/.env.example apps/web/.env
```

### 4.2 一键启动 / 停止（推荐）

使用仓库内统一的一键脚本：

```bash
# 在仓库根目录
scripts/dev_up.sh
```

该脚本会：

- 调用 `scripts/dev_down.sh` 清理已存在的本地开发进程；
- 清空并准备仓库根目录下的 `log/` 目录（`log/*.log`）；
- 根据 `infra/docker-compose.dev.yml` 启动本地依赖（Postgres / Redis 等）；
- 后台启动：
  - API（日志写入 `log/api.log`）；
  - Worker（日志写入 `log/worker.log`）；
  - Web 前端（日志写入 `log/web.log`）。

停止所有本地服务（包含依赖 + API + Worker + Web）：

```bash
scripts/dev_down.sh
```

你可以通过以下方式查看日志（示例）：

```bash
tail -f log/api.log
tail -f log/worker.log
tail -f log/web.log
```

### 4.3 按需单独启动（可选）

如需单独调试某个服务，也可以直接使用底层脚本或命令：

- 仅启动 Worker：

  ```bash
  scripts/dev_worker.sh
  ```

  或等价的底层命令：

  ```bash
  uv run --project apps/worker celery -A apps.worker.celery_app worker -l info
  ```

- 仅启动 API：

  ```bash
  scripts/dev_api.sh
  ```

  或：

  ```bash
  uv run --project apps/api uvicorn apps.api.main:app --reload
  ```

---

## 5. 前端（可选）

前端位于 `apps/web`，用于构建简单的 Web 控制台。如果你已经通过 `scripts/dev_up.sh` 启动环境，则 Web 已经由脚本自动启动；也可以按需单独调试：

```bash
npm install
cp apps/web/.env.example apps/web/.env

npm run web:dev
```

默认前端会调用 `http://localhost:8000` 上的 API，可通过 `VITE_API_BASE_URL` 调整。

---

## 6. 跑通一次 SteadyDancer 推理（最小链路）

目前预处理流程沿用上游仓库（`third_party/SteadyDancer`）的脚本；本仓库只封装了「生成阶段」。

### 6.1 使用上游仓库完成预处理

参考 `third_party/SteadyDancer/README.md` 中的 “Pose extraction and alignment” 部分，在 `third_party/SteadyDancer` 目录下运行相应命令，得到类似结构的目录：

```text
<pair_dir>/
  ├─ ref_image.png
  ├─ driving_video.mp4
  ├─ prompt.txt
  ├─ positive/0000.jpg ...
  └─ negative/0000.jpg ...
```

你可以直接复用其 `preprocess/output/...` 例子作为 `<pair_dir>`。

### 6.2 通过 API 提交生成任务

确保 Worker 与 API 已按前文启动。

推荐通过以下两种方式之一提交生成任务：

- 使用 Web 前端（`apps/web`）作为控制台；
- 直接调用 HTTP API（包括 Project / Asset / Experiment / Job 等接口）。

具体接口路径、请求体示例以及返回字段说明，统一维护在接口与数据模型文档中。

### 6.3 查询任务状态并获取结果
任务状态查询与结果视频路径的获取，同样通过 HTTP API 完成，调用方式与字段说明请参考接口与数据模型文档。

---

## 7. 常见问题（简要）

- **CUDA 版本不匹配**  
  如果遇到「The detected CUDA version mismatches the version that was used to compile PyTorch」：
  - 确认系统 CUDA toolkit 与安装的 PyTorch cu130 版本兼容；
  - 或选择 CPU 版本 / 其它 cu 版本的 PyTorch（调整 `apps/worker/pyproject.toml` 中的 `tool.uv.sources` 配置）。

- **flash-attn 编译内存不足**  
  使用：

  ```bash
  MAX_JOBS=3 uv sync --project apps/worker
  ```

- **模型路径找不到**  
  确认：
  - `scripts/download_models.py` 执行成功；
  - `MODELS_DIR` / `STEADYDANCER_CKPT_DIR` 与实际路径一致（可访问 API 的 `GET /models/info` 检查）。
