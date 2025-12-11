## 0. 适用范围与原则

本仓库为 **monorepo**，顶层目录结构与约定对 **所有应用与库** 生效。

*   **「Agent」定义**：包含各类代码生成模型、自动重构工具、脚本机器人等。
*   **关键字含义**（参考 RFC 2119）：
    *   **MUST / MUST NOT**：强制要求，禁止违反。
    *   **SHOULD**：强烈建议，除非有特殊理由。
    *   **MAY**：可选。

---

## 1. 顶层目录结构

仓库顶层目录结构 **MUST** 固定为：

```text
repo_root/
├─ apps/         # 可运行应用（独立环境）
├─ libs/         # 共享代码库（被 apps 引用）
├─ infra/        # 基础设施（Docker / K8s / Terraform）
├─ scripts/      # 自动化脚本（无独立环境，借用 app 环境）
├─ docs/         # 全局文档
├─ assets/       # 静态资源 / 示例素材
├─ models/       # (可选)模型权重（Git Ignored）
├─ data/         # 本地临时缓存/暂存（Git Ignored）
├─ logs/         # 本地日志（Git Ignored）
├─ tests/        # (可选) 全局集成测试
└─ third_party/  # 上游仓库（Git submodule，只读）
```

**约束：**
*   Agent **MUST NOT** 新增其他顶层目录。
*   `models/`、`data/`、`logs/`、`.venv/`、`__pycache__` **MUST** 在 `.gitignore` 中忽略。

---

## 2. apps/（应用）

每个子目录是一个独立应用（如 `apps/api`, `apps/worker`）。

**每个 app MUST 具备：**
*   **入口文件**：如 `main.py`。
*   **独立依赖声明**：`pyproject.toml` (Python) 或 `package.json` (Node)。
*   **README.md**：包含启动命令。
*   **env.example**：列出必需环境变量。
*   **tests/**：单元测试目录。

**依赖规则：**
*   **禁止横向引用**：`apps/A` **MUST NOT** import `apps/B`。
*   **下沉共享逻辑**：通用逻辑 **MUST** 放入 `libs/`。
*   **Agent 约束**：禁止在 `apps/` 下创建 `common/` 或 `utils/`，必须去 `libs/`。

---

## 3. libs/（共享代码）

`libs/` 存放可复用逻辑（如 `libs/py_core`, `libs/ts_ui`）。

**引用约束：**
*   **禁止反向引用**：libs **MUST NOT** import apps。
*   **防循环依赖**：允许 `libs/A` 引用 `libs/B`，但 **MUST NOT** 发生循环引用（A->B->A）。
*   **导入路径**：App 导入 Libs 时，**MUST** 使用绝对路径 `from libs.xxx import ...`，禁止使用 `../../` 相对路径。

---

## 4. 运行时目录 (本地)

### 4.1 models/ (模型权重)
*   **MUST** 通过环境变量 `MODELS_DIR` 获取路径（默认 `<repo_root>/models`）。
*   **MUST** 忽略 Git 提交。

### 4.2 data/ (本地缓存/暂存)
*   **定位**：仅用于 **临时缓存** 或 **上传 S3 前的中转**。
*   **MUST** 通过环境变量 `DATA_DIR` 获取路径。
*   **持久化原则**：重要的生成结果（如 AI 图像、处理后的数据集） **MUST NOT** 长期留存在此，**MUST** 上传至对象存储（S3/MinIO）。

### 4.3 logs/ (日志)
*   生产环境优先使用 `stdout`。
*   本地调试通过 `LOG_DIR` 写入此目录。

---

## 5. 对象存储与数据持久化 (S3/MinIO)

所有持久化文件（用户上传、AI 生成结果、数据集）**MUST** 使用 S3 协议存储。本地 `data/` 目录不可作为最终存储地。

### 5.1 可视化管理 (开发体验)
为了获得类文件系统的管理体验，开发人员 **SHOULD** 使用以下工具，而非直接查看 Docker 容器内部：

1.  **MinIO Web Console** (推荐)：
    *   Docker 部署默认端口：`9001` (如 `http://localhost:9001`)。
    *   功能：支持图片预览、多选删除、目录层级浏览。
2.  **桌面客户端**：
    *   **Cyberduck** / **S3 Browser** (Windows/Mac)：配置 Endpoint 为本地 MinIO 地址，体验如同管理本地文件夹。
3.  **IDE 插件**：
    *   VS Code 推荐安装 `AWS Toolkit` 或 `MinIO` 插件，实现侧边栏直接管理文件。

### 5.2 自动化清理 (Lifecycle Rules)
*   **禁止 Crontab**：Agent **MUST NOT** 编写 Python 脚本或 Crontab 任务来定期运行 `rm -rf` 清理过期文件。
*   **强制策略**：临时数据（如 `temp/` 目录下的中间产物），**MUST** 在 S3/MinIO Bucket 层面配置 **Lifecycle Rules (生命周期规则)**，实现“创建 X 天后自动删除”。

### 5.3 批量操作 (CLI)
*   对于海量文件（>1000 个）的删除或迁移，**SHOULD** 使用 `mc` (MinIO Client) 命令行工具，避免 GUI 卡顿。
*   示例：`mc rm --recursive --force myminio/data/temp/`。

---

## 6. scripts/（脚本与环境借用）

`scripts/` 仅存放脚本文件，**MUST NOT** 包含 `pyproject.toml`。

**运行原则（环境借用）：**
脚本必须“借用”某个 App 的环境运行，以复用依赖并确保环境一致性。

**Agent 执行策略：**

*   **重型任务 (CUDA/PyTorch/模型转换)**：
    *   **MUST** 借用 `apps/worker` 环境。
    *   命令：`uv run --project apps/worker scripts/compress_model.py`
*   **S3 维护任务 (使用 boto3 或 mc)**：
    *   **MUST** 借用 `apps/api` 环境 (通常包含 boto3)。
    *   命令：`uv run --project apps/api scripts/sync_s3_buckets.py`
*   **禁止**：Agent **MUST NOT** 直接运行 `uv run scripts/xxx.py`（裸跑）。

---

## 7. infra/（部署）

*   **Docker 构建上下文**：**MUST** 为 `repo_root`（以便 `COPY libs/`）。
*   **Dockerfile**：
    *   ✅ `COPY libs /app/libs`
    *   ❌ `COPY ../libs`
*   **docker-compose.dev.yml**：
    *   **MinIO 服务**
    *   **Redis/PG**

---

## 8. 环境变量

*   `.env`：禁止提交 Git。
*   `.env.example`：**必须**提交。
*   **S3 配置**：必须包含 `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET_NAME`。
*   **读取**：代码 **MUST** 通过环境变量读取配置，禁止硬编码路径或密钥。

---

## 9. Python 后端与 uv (Workspaces)

**基本原则：**
所有 Python 操作 **MUST** 在 `repo_root` 根目录下执行。

**依赖声明 (pyproject.toml)：**
App 必须显式声明对 libs 的本地依赖（Editable），以支持 `import libs.*`。

*示例 `apps/api/pyproject.toml`:*
```toml
[project]
dependencies = [
    "fastapi",
    "boto3",  # 用于 S3 操作
    "py_core @ {path = '../../libs/py_core', editable = true}",
]
```

**uv运行命令清单：**

*   **启动 API**：
    ```bash
    uv run --project apps/api uvicorn main:app --reload
    ```
*   **启动 Worker**：
    ```bash
    uv run --project apps/worker python main.py
    ```
*   **安装/同步依赖**：
    ```bash
    uv sync --project apps/api
    ```

**代码质量：**
Agent 生成代码后 **SHOULD** 运行 `ruff check --fix` 或 `ruff format`。