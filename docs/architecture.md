# SteadyDancer Monorepo Architecture

本文档描述 SteadyDancer monorepo 的整体结构、核心组件以及模型与基础设施约定。

## 1. 目录结构与职责

- `apps/`：可运行应用。
  - `apps/api`：FastAPI HTTP 服务，提供对外 API。
  - `apps/web`：React + Vite 前端应用。
  - `apps/worker`：基于 Celery 的后台 Worker。
- `libs/`：共享逻辑。
  - `libs/py_core`：后端共享 Python 工具与模型封装。
  - `libs/ts_ui`：前端共享 UI 组件库。
- `infra/`：部署与本地依赖。
  - `infra/docker-compose.dev.yml`：本地 Postgres / Redis 等。
  - `infra/docker/`：API / Worker 的 Dockerfile。
- `scripts/`：开发与运维脚本。
  - `scripts/dev_up.sh` / `dev_down.sh`：本地依赖服务的启动 / 停止。
  - `scripts/dev_api.sh`：启动 API 服务。
  - `scripts/dev_worker.sh`：启动 Worker。
  - `scripts/download_models.py`：模型下载与准备入口（占位实现）。
- `models/`：模型权重与运行时数据（仅本地存在，不提交到 Git）。
- `third_party/`：上游仓库 Git submodule，仅作参考。
  - `third_party/SteadyDancer`：SteadyDancer 原始代码仓库。
  - `third_party/DFloat11`：DFloat11 压缩精度库。

所有硬性规范和 Agent 约束见根目录 `AGENTS.md`。

## 2. 模型目录与 MODELS_DIR 约定

- `models/` 是唯一的模型根目录。
- 所有服务通过环境变量 `MODELS_DIR` 解析模型路径：
  - 本地默认：`MODELS_DIR=./models`（参见 `.env.example`）。
  - 线上环境：推荐挂载卷，例如 `/models`。
- 代码中通过 `libs.py_core.config.get_models_dir()` 获取模型目录：
  - 首先读取 `MODELS_DIR`；
  - 若未设置，则回落到 `<repo_root>/models`。

**禁止**在代码中写死具体文件系统路径（如 `/home/.../models`）。

### Z-Image 模型与变体（占位）

当前仅预留模型目录和上游 submodule：

- Turbo / Base / Edit 等具体模型变体及其路径规划，后续可在：
  - `libs/py_core/models/` 中通过适配器进行封装；
  - 在 `docs/architecture.md` 中补充各变体的职责与输入输出约定。

应用端（API / Worker）只能通过 `libs.py_core.models.*` 来访问模型逻辑，禁止直接引用 `third_party.*`。

## 3. 后端应用与 Worker

### 3.1 API（apps/api）

- 技术栈：FastAPI + Uvicorn。
- 入口：`apps/api/main.py`，FastAPI app 实例为 `app`。
- 健康检查：
  - `GET /health`：基础存活检查。
  - `GET /models/info`：返回当前解析到的 `MODELS_DIR`。
- 开发启动：

```bash
uv run --project apps/api uvicorn apps.api.main:app --reload
```

### 3.2 Worker（apps/worker）

- 技术栈：Celery（推荐使用 Redis broker）。
- 入口：
  - Celery app：`apps.worker.celery_app:celery_app`
  - 开发启动：

```bash
uv run --project apps/worker celery -A apps.worker.celery_app worker -l info
```

- 配置：
  - `CELERY_BROKER_URL`、`CELERY_RESULT_BACKEND`、`CELERY_DEFAULT_QUEUE`、`WORKER_CONCURRENCY` 等环境变量在 `apps/worker/.env.example` 中示例。
- 示例任务：
  - `worker.health_check`：用于验证 worker 与 broker 的连通性，并返回解析到的 `MODELS_DIR`。

未来可以在 `apps/worker` 中扩展实际的推理任务，逻辑实现放在 `libs/py_core`。

## 4. Web 前端（apps/web）

- 技术栈：React + Vite。
- 入口：`apps/web/src/main.tsx` 与 `App.tsx`。
- 环境变量：
  - `VITE_API_BASE_URL`：API 服务的基础 URL。
- 开发启动（在仓库根目录）：

```bash
npm install
cp apps/web/.env.example apps/web/.env
npm run web:dev
```

前端只通过 HTTP 调用 `apps/api` 提供的接口，不直接访问模型或 `third_party/`。

## 5. 数据库与缓存（高层设计）

- 数据库：Postgres（由 `infra/docker-compose.dev.yml` 提供）。
  - 默认数据库名：`steadydancer`。
  - 典型用途：用户信息、任务记录、审计日志等。
- 缓存 / 队列：Redis。
  - 用途：
    - API 缓存热数据；
    - Celery Broker / Result Backend（Worker 队列）。

字段级结构由迁移脚本或 ORM 模型定义，本文件只约束高层角色与连接方式。

## 6. 上游仓库与适配层

- 上游仓库放在 `third_party/`，当前包含：
  - `third_party/SteadyDancer`
  - `third_party/DFloat11`
- 这些仓库视为**只读**：
  - 不在其中添加业务逻辑。
  - 不直接在应用中 `import third_party...`。
- 如需使用上游逻辑：
  - 在 `libs/py_core/models/` 中创建适配器模块（例如 `steadydancer_adapter.py`）。
  - 应用（API / Worker）只 import 适配器，而不关心具体上游实现细节。

## 7. 运行方式与环境

- 推荐在仓库根目录执行所有 Python 相关命令，并指定 `--project`：
  - API：

    ```bash
    uv run --project apps/api uvicorn apps.api.main:app --reload
    ```

  - Worker：

    ```bash
    uv run --project apps/worker celery -A apps.worker.celery_app worker -l info
    ```

- 本地依赖服务：

  ```bash
  docker compose -f infra/docker-compose.dev.yml up -d
  ```

- 所有配置通过 `.env` / `.env.example` 管理，实际 `.env` 文件不提交到 Git。

如修改关键环境变量名、目录结构或核心 API，请同步更新本文件与各 app 的 README。

