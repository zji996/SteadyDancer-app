# SteadyDancer API

HTTP API 服务，负责对外提供 SteadyDancer 相关能力（如图像生成、编辑等）的统一入口。

## 启动方式（开发环境）

在仓库根目录执行：

```bash
uv run --project apps/api uvicorn apps.api.main:app --reload
```

推荐先复制并修改环境变量示例：

```bash
cp apps/api/.env.example apps/api/.env
```

再使用 `scripts/dev_api.sh` 脚本（会自动加载 `.env`）：

```bash
scripts/dev_api.sh
```

## 认证与安全边界

### API Key 认证

- API 通过一个简单的 API Key 控制访问权限：
  - 环境变量：`STEADYDANCER_API_KEY`；
  - HTTP 头：`X-API-Key: <你的 API Key>`。
- 行为约定：
  - 当 **未设置** `STEADYDANCER_API_KEY` 时，API Key 校验关闭（开发环境方便使用）；
  - 当 **设置** 了 `STEADYDANCER_API_KEY` 时：
    - 所有业务路由（`/projects/**`、`/steadydancer/**`）都必须携带正确的 `X-API-Key`；
    - 否则返回 `401`，错误码为 `INVALID_API_KEY`；
    - `/health` 与 `/models/info` 仍然保持无需认证，方便做存活探针。

### 错误返回格式（统一约定）

所有通过 FastAPI 抛出的业务错误都统一为如下结构：

```json
{
  "detail": {
    "code": "PROJECT_NOT_FOUND",
    "message": "Project not found.",
    "extra": {
      "...": "可选的调试信息"
    }
  }
}
```

- `code`：稳定的机器可读错误码，前端可以据此做分支处理；
- `message`：人类可读的错误信息，可直接展示给用户（或稍作本地化）；
- `extra`：可选字段，用于携带 task_id / state / 路径 等调试信息（不保证字段完全固定）。

常见错误码示例：

- 认证相关：
  - `INVALID_API_KEY`：缺失或错误的 `X-API-Key`；
- Project / Asset / Experiment：
  - `PROJECT_NOT_FOUND`
  - `PROJECT_NAME_CONFLICT`
  - `REFERENCE_ASSET_NOT_FOUND` / `MOTION_ASSET_NOT_FOUND`
  - `ASSET_NOT_FOUND`
  - `EXPERIMENT_NOT_FOUND`
  - `SOURCE_FILE_NOT_FOUND`
  - `SOURCE_INPUT_DIR_NOT_FOUND`
- Job / Celery：
  - `JOB_NOT_FOUND`
  - `JOB_NO_VIDEO_RESULT`
  - `RESULT_FILE_NOT_FOUND`
  - `INPUT_DIR_NOT_FOUND`
  - `JOB_PREPARATION_FAILED`
  - `CELERY_TASK_ERROR`（`extra` 里会包含 `task_id` / `state` / `error` 文本）。

前端推荐处理方式：

- 先根据 HTTP 状态码做一级分支（4xx/5xx）；
- 再读取 `detail.code` 做细粒度逻辑（如 `PROJECT_NOT_FOUND` 提示“项目不存在或已删除”）；
- `detail.message` 用于默认提示文案；`detail.extra` 仅在调试面板中展示。

## 路径与数据目录约定

- 仅从 `libs/` 导入共享逻辑，例如 `libs.py_core`。
- 不直接依赖 `third_party/` 中的任何代码或路径。
- 所有模型路径基于环境变量 `MODELS_DIR` 计算，禁止写死绝对路径。

### 请求体中的文件 / 目录路径

以下字段在文档和实现中都遵循同一约定：**“绝对路径或仓库根目录相对路径”**：

- `ReferenceAssetCreate.source_image_path`
- `MotionAssetCreate.source_video_path`
- `ExperimentCreate.source_input_dir`
- `SteadyDancerJobCreate.input_dir`

解析规则（后端实现于 `libs.py_core.projects.resolve_repo_relative`）：

- 若字段为 **绝对路径**：直接按该路径使用；
- 若字段为 **相对路径**：相对于仓库根目录（repo root）解析，而不是当前工作目录。

典型用法：

- 在本仓库根目录下有 `assets/examples/ref.png` 时：
  - 前端可以传 `source_image_path: "assets/examples/ref.png"`；
- 如果有单独挂载的数据盘 `/data/steadydancer`：
  - 前端可以传 `source_input_dir: "/data/steadydancer/my_pair_dir"` 作为绝对路径。

## 项目 / Job 与文件目录

- 后端引入了「项目（Project）+ 任务（Job）」的层级，便于管理多次生成：
  - `POST /projects`：创建项目；
  - `POST /projects/{project_id}/steadydancer/jobs`：在项目下创建一次 SteadyDancer 生成任务；
  - `GET /projects/{project_id}/steadydancer/jobs/{job_id}`：查询任务状态与结果。
- 文件按项目与 Job 组织在 `STEADYDANCER_DATA_DIR`（若未设置则回退到 `DATA_DIR`，再回退到 `<repo_root>/data`）下：
  - `projects/{project_id}/jobs/{job_id}/input/`：本次 Job 的输入（预处理后的 ref_image.png、positive/negative 等）；
  - `projects/{project_id}/jobs/{job_id}/output/`：生成的视频等结果文件；
  - `projects/{project_id}/jobs/{job_id}/tmp/`：中间临时文件，按需清理。
