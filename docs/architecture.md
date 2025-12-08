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
  - `scripts/dev_up.sh` / `dev_down.sh`：一键启动 / 停止本地依赖 + API + Worker + Web，并将日志写入仓库根目录下的 `log/`。
  - `scripts/dev_api.sh`：仅启动 API 服务（前台），供按需单独调试使用。
  - `scripts/dev_worker.sh`：仅启动 Worker（前台），供按需单独调试使用。
  - `scripts/download_models.py`：模型下载与准备入口（支持 ModelScope / HuggingFace）。
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

SteadyDancer 适配约定（当前设计）：

- SteadyDancer 权重目录：
  - 默认：`<MODELS_DIR>/SteadyDancer-14B`
  - 可通过 `STEADYDANCER_CKPT_DIR` 覆盖。
- libs 中提供 CLI 适配器：
  - `libs.py_core.models.steadydancer_cli.run_i2v_generation`：
    - 调用 `third_party/SteadyDancer/generate_dancer.py` 子进程；
    - 输入为已经完成姿态预处理的目录（`ref_image.png`、`prompt.txt`、`positive/`、`negative/`）。
- Worker 侧通过 Celery 任务调用该适配器，API 只与 Celery 队列交互，不直接操作模型。

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

> 更详细的 HTTP 接口定义、认证与错误码约定，请参考应用本地文档 `apps/api/README.md`。

#### 3.1.1 项目（Project）与任务（Job）分层

为了方便长期管理生成记录与文件，API 引入了「项目（Project）+ 任务（Job）」的抽象：

- `Project`：一组相关生成任务的逻辑集合，例如同一个角色 / 拍摄项目。
- `Job`：一次具体的 SteadyDancer 生成调用，对应一份输入和一份输出视频。

核心 HTTP 接口：

- `POST /projects`
  - 创建项目：接收 `name` / `description`，返回 `project_id`（UUID）。
- `GET /projects/{project_id}`
  - 查询项目基础信息。
- `POST /projects/{project_id}/steadydancer/jobs`
  - 在指定项目下创建 SteadyDancer I2V 任务；
  - 请求体与 `/steadydancer/jobs` 相同（尺寸、帧数、seed 等），并传入预处理完成的 `input_dir`；
  - API 会：
    - 为该 Job 生成 `job_id`（UUID）；
    - 在数据目录下创建标准 Job 目录结构，并将 `input_dir` 拷贝到 job 的 `input/`；
    - 通过 Celery 将任务入队，并在数据库中记录一条 `Job` 记录。
- `GET /projects/{project_id}/steadydancer/jobs/{job_id}`
  - 查询该 Job 状态；
  - 通过 Celery 读取任务状态和结果（`success` / `video_path` / `stdout` / `stderr` / `return_code`），并与数据库中的 Job 元数据合并返回。

此外保留了低级接口：

- `POST /steadydancer/jobs` / `GET /steadydancer/jobs/{task_id}`  
  直接以 `task_id` 封装 Celery 队列，适合调试或临时调用；推荐业务侧优先使用 Project + Job 路径。

#### 3.1.2 资产（Asset）与实验（Experiment）分层

为了支持「一张参考图对应多段舞蹈」以及「多张参考图复用同一段舞蹈」等工作流，在 Project 内进一步引入资产与实验的抽象：

- `ReferenceAsset`：参考图资产（角色 / 人物），通常是一张或多张图；
- `MotionAsset`：动作 / 舞蹈资产，对应一段 driving video；
- `Experiment`：一次实验配置，描述「用哪个 Reference + 哪个 Motion + 一组默认参数」，其下可以有多个实际运行的 `Job`。

典型链路：

- 注册资产：
  - `POST /projects/{project_id}/refs`：登记参考图（传入本地文件路径，API 拷贝到 `refs/{ref_id}`）；
  - `POST /projects/{project_id}/motions`：登记舞蹈视频（拷贝到 `motions/{motion_id}`）。
- 创建实验：
  - `POST /projects/{project_id}/experiments`：
    - 指定 `reference_id` / `motion_id`；
    - 指定 `source_input_dir`（已有的 SteadyDancer 预处理目录，兼容上游脚本生成的 pair_dir）；
    - 可选传入一份默认的 SteadyDancer 配置（尺寸、帧数、seed 等），作为 `config` 存储。
  - API 会将 `source_input_dir` 拷贝到：

    ```text
    <STEADYDANCER_DATA_DIR>/projects/{project_id}/experiments/{experiment_id}/input/
    ```

    并在 DB 的 `experiments.input_dir` 中记录这一「规范化输入目录」。
  - `POST /projects/{project_id}/experiments/preprocess`：
    - 指定 `reference_id` / `motion_id` 与实验配置 `config`；
    - 由 API 创建 Experiment 记录并调用 worker 侧 Celery 任务 `steadydancer.preprocess.experiment`，以当前 Project 下的 `ReferenceAsset` / `MotionAsset` 为输入，在实验目录下生成规范化 pair_dir（`ref_image.png`、`driving_video.mp4`、`positive/`、`negative/` 等）；
    - 若 `config.prompt_override` 不为空，会写入 `prompt.txt`。
- 从实验创建 Job：
  - `POST /projects/{project_id}/experiments/{experiment_id}/steadydancer/jobs`：
    - 默认使用 Experiment 的 `input_dir` 作为 Job 的输入源；
    - 请求体参数可覆盖实验级配置（例如修改 seed / 尺寸）；
    - API 为该 Job 创建单独的工作目录并入队 Celery 推理。

这样，一个 Project 就成为「工作平台」：

- `ReferenceAsset` 和 `MotionAsset` 分别复用角色图与舞蹈视频；
- `Experiment` 固定「角色 + 舞蹈 + 默认参数」；
- `Job` 则记录每次具体的生成运行（不同种子 / 不同微调）。

#### 3.1.3 API 内部分层与解耦

`apps/api` 内部采用「路由层（HTTP）+ 服务层 + 持久化层」的轻量分层：

- 路由层（`apps/api/routes/*`）：
  - 只负责 HTTP 相关逻辑（参数解析、状态码、错误映射）；
  - 调用下层服务完成业务操作。
- 服务层（`apps/api/services/*`）：
  - `services/projects.py`：项目的创建与查询；
  - `services/assets.py`：Project 下参考图 / 动作资产的创建与查询；
  - `services/experiments.py`：实验的创建与查询（包含规范化输入目录的准备）；
  - `services/steadydancer_jobs.py`：
    - 构造 SteadyDancer Celery 任务 payload；
    - 统一的 `enqueue_steadydancer_task` / `query_celery_task`；
    - 针对 Project / Experiment 下 Job 的创建与状态刷新（包含目录准备、结果视频规范化迁移等）。
- 持久化层（`apps/api/db.py`）：
  - 基于 SQLAlchemy 2.x + asyncpg：
    - `Project` ORM：`id`（UUID）、`name`（唯一）、`description`、`created_at`、`updated_at`；
    - `ReferenceAsset` / `MotionAsset`：
      - `id`（UUID）、`project_id`、`name`、`image_path` / `video_path`（相对于 `STEADYDANCER_DATA_DIR` 的相对路径）、`meta`（JSONB）、时间戳；
    - `Experiment`：
      - `id`（UUID）、`project_id`、`reference_id`、`motion_id`、`name`、`description`；
      - `input_dir`（实验级规范化输入目录，相对于 `STEADYDANCER_DATA_DIR` 的相对路径）、`config`（JSONB）、`preprocess_task_id?`、时间戳；
    - `Job`（表名 `generation_jobs`）：
      - `id`（UUID）、`project_id`、`experiment_id`、`task_id`（Celery 任务 ID）、`job_type`；
      - `status`（Celery 状态 + 少量自定义状态，如 `EXPIRED`）、`input_dir`（Job 级别输入目录，相对于 `STEADYDANCER_DATA_DIR` 的相对路径）、`params`（JSONB）；
      - `success`、`result_video_path`（统一迁移到 Job 的 `output/` 后的路径，相对于 `STEADYDANCER_DATA_DIR` 的相对路径）、`error_message`；
      - `created_at`、`updated_at`、`started_at`、`finished_at`、`canceled_at`、`cancel_reason`。
  - 暴露 `engine`、`AsyncSessionFactory` 与 `get_session` 作为 FastAPI 依赖。

API 的启动生命周期（`lifespan`）中会在开发环境通过 `init_db()` 调用 `Base.metadata.create_all()` 初始化表结构，生产环境推荐使用独立迁移工具。

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
    - `steadydancer.preprocess.experiment`：从 ReferenceAsset / MotionAsset 读取图像与视频，调用上游 SteadyDancer 预处理脚本生成规范化 pair_dir。
    - `steadydancer.generate.i2v`：从预处理好的输入目录调用 SteadyDancer DF11 / BF16 CLI 或 Wan API 生成视频。

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
  - 典型用途：用户信息、任务记录（Project / Job）、审计日志等。
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
  - 在 `libs/py_core/models/` 中创建适配器模块（例如 `steadydancer_cli.py`，后续可扩展为更细粒度的 adapter）。
  - 应用（API / Worker）只 import 适配器，而不关心具体上游实现细节。

### 6.1 项目 / 资产 / 实验 / Job 数据目录适配（libs/py_core/projects.py）

与模型目录解耦，项目及其资产 / 实验 / Job 的业务数据统一放在 `STEADYDANCER_DATA_DIR` 下，由 `libs.py_core.projects` 提供路径计算：

- 根目录：
  - `STEADYDANCER_DATA_DIR`（可配置环境变量），默认：`<repo_root>/assets/projects`；
  - `STEADYDANCER_TMP_DIR`（可选），默认：`<STEADYDANCER_DATA_DIR>/tmp`。
- 单个 Project：

  ```text
  <STEADYDANCER_DATA_DIR>/projects/{project_id}/
  ```

- 参考图资产（ReferenceAsset）：

  ```text
  <STEADYDANCER_DATA_DIR>/projects/{project_id}/refs/{ref_id}/
    source/      # 原始参考图文件（由 API 从 source_image_path 拷贝而来）
    meta.json    # 可选：角色名、提示词等元信息
  ```

- 动作资产（MotionAsset）：

  ```text
  <STEADYDANCER_DATA_DIR>/projects/{project_id}/motions/{motion_id}/
    source/      # 原始 driving video 文件
    meta.json    # 可选：风格标签、时长等
  ```

- 实验（Experiment）：

  ```text
  <STEADYDANCER_DATA_DIR>/projects/{project_id}/experiments/{experiment_id}/
    input/       # 规范化的 SteadyDancer 输入目录（pair_dir 拷贝）
    config.json  # 可选：SteadyDancer 默认配置快照
  ```

- Job：

  ```text
  <STEADYDANCER_DATA_DIR>/projects/{project_id}/jobs/{job_id}/
    input/   # 本 Job 的输入（从 Experiment.input 或用户传入目录拷贝）
    output/  # 推理生成的视频等结果（API 在任务完成后会将结果视频规范化移动到该目录）
    tmp/     # 中间临时文件（一次性缓存，可按策略清理）
    logs/    # 可选：stdout/stderr 等日志落地
  ```

`libs.py_core.projects` 提供：

- `ensure_reference_dirs` / `ensure_motion_dirs`：保证资产目录存在；
- `ensure_experiment_dirs`：为 Experiment 创建 `input/` 与 `config.json` 所在目录；
- `ensure_job_dirs`：为 Job 创建 `input/` / `output/` / `tmp/` / `logs/` 目录。

API 在创建 Experiment / Job 时会调用这些工具函数，确保文件布局稳定且可预期。

## 7. 运行方式与环境

- 推荐在仓库根目录执行所有 Python 相关命令，并指定 `--project`。
- 一键启动 / 停止本地开发环境（包含 Postgres / Redis 依赖、API、Worker、Web）：

  ```bash
  # 启动全部服务，并将日志写入仓库根目录下 log/ 目录
  scripts/dev_up.sh

  # 停止全部服务（包括通过 dev_up.sh 启动的 API / Worker / Web 和 docker-compose 依赖）
  scripts/dev_down.sh
  ```

  - `dev_up.sh` 会在启动前调用 `dev_down.sh` 清理旧进程，并清空 `log/*.log`；
  - API 日志写入 `log/api.log`，Worker 日志写入 `log/worker.log`，Web 日志写入 `log/web.log`。
- 如需分别单独调试 API / Worker，也可以直接运行底层命令：

  - API：

    ```bash
    uv run --project apps/api uvicorn apps.api.main:app --reload
    ```

  - Worker：

    ```bash
    uv run --project apps/worker celery -A apps.worker.celery_app worker -l info
    ```

- 所有配置通过 `.env` / `.env.example` 管理，实际 `.env` 文件不提交到 Git。

如修改关键环境变量名、目录结构或核心 API，请同步更新本文件与各 app 的 README。
