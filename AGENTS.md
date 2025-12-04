Monorepo 目录与约定（给 Agent）
================================

TL;DR：
- 业务在 `apps/`
- 共享逻辑在 `libs/`
- 模型在 `models/`
- 上游代码在 `third_party/`（Git submodule，只读）

这些约定对本仓库的所有 Agent 与贡献者均为**硬性规范**。

---

1. 目录结构（约定）
-------------------

仓库根目录结构约定如下：

- `apps/`：可运行应用（API、Web、Worker 等）。
- `libs/`：共享代码库。
- `infra/`：部署与基础设施（Docker、K8s、Terraform 等）。
- `scripts/`：开发 / 运维脚本。
- `docs/`：文档。
- `assets/`：静态资源 / 示例素材。
- `models/`：模型权重（运行时数据）。
- `third_party/`：上游仓库（Git submodule，仅参考）。

如需新增内容，应优先放入以上既有目录中，避免在根目录散落新顶层目录。

2. apps/ 规范
--------------

- `apps/` 下每个子目录是一个独立应用（如 `api/`、`web/`、`worker/`）。
- 每个 app 必须有自己的入口文件（如 `main.py` / `main.tsx`）。
- 每个 app 必须有自己的依赖声明（如 `pyproject.toml` / `package.json`）。
- app 之间禁止直接互相 import 代码，只能通过 `libs/` 共享逻辑。
- 新功能优先放到对应 app 下的 `api/`、`routes/`、`features/` 等业务目录。

Agent 必须遵守：
- 不得在一个 app 中通过相对路径引用另一个 app 目录的源码。
- 与「运行逻辑」相关的新代码优先放在对应 `apps/<app_name>/` 下。

3. libs/ 规范
--------------

- `libs/` 只存放可被多个 app 共享的代码。
- 后端共享逻辑建议放在 `libs/py_core/`（模型封装、推理管线、通用工具）。
- 前端共享组件建议放在 `libs/ts_ui/`（UI 组件、hooks、工具函数）。
- 应用代码只允许从 `libs/` import，不允许从其他 `apps/` 目录 import。
- 如需包装 `third_party/` 的功能，必须在 `libs/` 内写 adapter，app 只依赖 adapter。

4. models/ 规范（模型目录）
---------------------------

- 根目录 `models/` 是唯一的模型权重存储目录。
- 模型权重、缓存等大文件只能放在 `models/` 下，不得放在 `apps/` 或 `libs/` 中。
- `models/` 不提交到 Git：
  - `.gitignore` 中必须包含 `models/`，可以保留 `models/README.md` 说明。
- 所有服务使用统一环境变量 `MODELS_DIR` 指定模型根目录：
  - 默认值为 `<repo_root>/models`。
  - Docker / 线上环境可将 `MODELS_DIR` 指向挂载磁盘（例如 `/models`）。
- 加载模型时必须通过 `MODELS_DIR` 计算路径，不得写死绝对路径。
- 下载 / 更新模型必须通过 `scripts/` 下的脚本（如 `scripts/download_models.py`），不得手动提交模型文件。

Agent 必须遵守：
- 不得在仓库中提交 `models/` 下的大文件。
- 只能修改 `models/README.md` 或与路径约定相关的轻量文件。

5. third_party/ 规范（submodule）
---------------------------------

- `third_party/` 只允许存放 Git submodule，禁止直接创建普通源码目录。
- 每个子目录对应一个上游仓库子模块，例如：
  - `third_party/some_model_repo/`
  - `third_party/research_code/`
- `third_party/` 内容视为只读参考代码：
  - 不在其中添加业务逻辑。
  - 不在其中放置模型权重或运行时数据。
- 如需修改上游代码：
  - 优先在上游仓库 fork + 修改；
  - 然后更新对应 submodule 指向的 commit。
- 应用与库代码禁止直接依赖 `third_party` 路径：
  - 不允许出现 `import third_party.xxx` 这类引用。
- 需要用到其中逻辑时，在 `libs/` 中创建 adapter / wrapper，app 只依赖 `libs/`。
- 构建、测试、Lint 默认必须忽略 `third_party/`：
  - Type-check / Lint 工具需将 `third_party/` 配置为 `exclude` / `ignore`。
  - 测试框架需将 `third_party/` 配置为 `norecursedirs` / `testPathIgnorePatterns`。

Agent 必须遵守：
- 不得在 `third_party/` 中新增、修改业务代码或模型文件。
- 新增上游依赖时，只能通过 Git submodule 的方式引入。

6. scripts/ 规范
----------------

- `scripts/` 只放自动化脚本，如：
  - 本地启动脚本（如 `dev_up.sh`）。
  - 数据库迁移脚本。
  - 模型下载脚本（如 `download_models.py`）。
- 脚本应是幂等的，多次执行不会破坏环境。
- 脚本不得实现业务逻辑，业务逻辑必须在 `apps/` 或 `libs/` 内。

Agent 必须遵守：
- 如需新增启动方式，优先在 `scripts/` 下新增脚本，而不是在随机目录新建 shell 脚本。

7. infra/ 规范
---------------

- `infra/` 存放部署相关文件，例如：
  - `infra/docker/`：各 app 的 Dockerfile。
  - `infra/k8s/`：K8s manifests 或 Helm chart。
  - `infra/terraform/`：基础设施声明。
- Dockerfile 不直接 `COPY models/`：
  - 模型通过卷挂载或运行时下载。
- `docker-compose.yml` 统一挂载模型目录：
  - 例如 `./models:/models`，并设置 `MODELS_DIR=/models`。

Agent 必须遵守：
- 如需新增本地依赖服务（数据库 / 缓存等），只能修改 `infra/docker-compose*.yml`，不得在其他目录新建 Compose 文件。

8. docs/ 规范
--------------

- `docs/` 只存放对整个 monorepo 生效的文档，例如整体架构、模型说明、运维约定等。
- 各 app 私有的信息（启动命令、局部环境变量等）放在对应的 `apps/*/README.md` 中。
- 当前约定仅保留一份核心文档：
  - `docs/architecture.md`：整体架构与目录说明，包含：
    - 目录结构与各目录职责（`apps/` / `libs/` / `models/` / `scripts/` / `infra/` 等）。
    - Z-Image 模型目录、`MODELS_DIR` 约定，以及 Turbo / Base / Edit 等变体的角色划分。
    - 后端 / Worker / Web 的启动入口（dev 脚本、主要进程）。
    - 数据库在系统中的角色与核心实体/关系（高层设计）。
- 所有“硬性规范”和“Agent 约束”只在根目录 `AGENTS.md` 中维护。
- 文档中的路径、环境变量名、目录约定、关键概念应与代码保持一致：
  - 增加/修改环境变量、重要目录结构或核心 API 时，需要同步更新相关文档（优先是 `README.md` 与 `docs/architecture.md`）。
- 文档统一使用 Markdown，尽量保持结构清晰、示例简短。

9. 本地开发环境约定（DB / Cache / .env / 启动脚本）
--------------------------------------------------

TL;DR：本地依赖服务用 `infra/docker-compose.dev.yml`，启动脚本放 `scripts/`，配置用 `.env` + `.env.example`，Python 应用通过 `uv` 启动。

9.1 Docker Compose（数据库 / 缓存）

- 本地 Postgres / Redis 等依赖统一定义在 `infra/docker-compose.dev.yml`。
- 默认本地启动命令约定为：
  - `docker compose -f infra/docker-compose.dev.yml up -d`
- 不在 `apps/` 下创建散落的 `docker-compose.yml`，统一使用 `infra/`。

9.2 启动脚本（scripts/）

- 跨服务 / 项目级脚本统一放在 `scripts/` 目录。
- 命名需体现用途与环境，例如：
  - `scripts/dev_up.sh`：本地开发整体启动。
  - `scripts/dev_down.sh`：本地开发整体停止。
  - `scripts/dev_api.sh`：只启动某个后端应用。
- 避免语义不清的通用名（如 `start.sh` / `run.sh`），必须带上用途（`dev` / `api` / `web` 等）。
- 脚本只做启动与编排，不实现业务逻辑；业务逻辑必须在 `apps/` 或 `libs/` 中。
- 启动 Python 应用时，脚本内部应使用 `uv run`，例如：
  - `uv run python main.py`

9.3 环境变量与 .env

- 每个 app 使用独立的 `.env` 文件，路径为 `apps/<app_name>/.env`，不提交到 Git。
- 每个 app 必须维护 `apps/<app_name>/.env.example`，列出所需变量及示例值，提交到 Git。
- 如需全局配置，可在根目录使用 `.env` / `.env.example`，规则相同：
  - 仅 `.env.example` 提交到 Git。
- 所有服务需通过环境变量读取配置（如 `MODELS_DIR`、数据库连接、缓存地址等），禁止在代码中写死。

Agent 必须遵守：
- 不得在仓库中提交任何实际 `.env` 文件，只允许提交 `*.env.example`。

10. Python 环境与依赖（uv）
---------------------------

TL;DR：后端 Python 应用统一用 `uv` 管理依赖和环境。每个 app 在自己的目录下维护 `pyproject.toml` + `uv.lock`，`uv sync` 自动创建 `.venv/`。Git 只提交 `pyproject.toml` 和 `uv.lock`，不提交任何虚拟环境目录。运行时推荐在仓库根目录配合 `--project` 使用 `uv run`，确保可以正常导入 `apps/` 和 `libs/`。

基本原则

- 后端 Python 应用统一使用 `uv` 管理环境与依赖。
- 每个 Python app（如 `apps/api/`、`apps/worker/`）都是一个独立的 uv project。

项目文件

- `pyproject.toml`：依赖声明文件。
- `uv.lock`：依赖锁定文件，必须提交到 Git（由 `uv` 生成）。
- 不在仓库根目录放全局 `pyproject.toml`，而是按 app 分目录管理。

虚拟环境

- 虚拟环境目录由 `uv` 自动创建和管理：
  - 允许在各 app 目录下存在 `.venv/`（由 `uv sync` 创建）。
  - `.venv/` 必须被 `.gitignore` 排除，不得提交到 Git。
- 禁止手动使用 `python -m venv`、`virtualenv` 等方式在仓库内创建额外虚拟环境目录。

依赖管理（在对应 app project 下）

- 安装依赖：`uv add <package>`
- 移除依赖：`uv remove <package>`
- 同步 / 升级依赖：`uv sync` / `uv sync --upgrade`
- 修改依赖后，记得提交更新后的 `uv.lock`。

运行方式（重点：从仓库根目录 + --project）

- 为了让顶层包 `apps/` 和 `libs/` 都在 import 路径里，推荐在仓库根目录运行命令，并显式指定 project：
  - 启动 API：`uv run --project apps/api uvicorn apps.api.main:app --reload`
  - 启动 Worker：`uv run --project apps/worker python -m apps.worker.main`
- 不推荐先 `cd apps/api` 再直接 `uv run ...`，否则可能出现 `ModuleNotFoundError: No module named 'apps'` 之类的问题。
- 启动 Python 程序时，统一使用 `uv run` 包裹命令，而不是直接用系统 `python` 或手动激活 `.venv`。

共享库 libs/ 的使用

- `libs/` 中的 Python 代码（如 `libs/py_core`）供各 app 复用。
- 如需使用 `libs/`，应通过各 app 的 `pyproject.toml` 声明本地依赖 / workspace 配置，不得在代码中直接修改 `sys.path` 或 `PYTHONPATH`。
- 通过“仓库根目录 + `uv run --project ...`”的约定，保证运行时能够正常导入 `apps.*` 和 `libs.*`。

---

如有与本文件不一致的说明，以本文件为准。新增约定时，请更新本文件并在相关目录下的 README 中作简要说明。

