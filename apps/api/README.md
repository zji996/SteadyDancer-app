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

## 约定

- 仅从 `libs/` 导入共享逻辑，例如 `libs.py_core`。
- 不直接依赖 `third_party/` 中的任何代码或路径。
- 所有模型路径基于环境变量 `MODELS_DIR` 计算，禁止写死绝对路径。

## 项目 / Job 与文件目录

- 后端引入了「项目（Project）+ 任务（Job）」的层级，便于管理多次生成：
  - `POST /projects`：创建项目；
  - `POST /projects/{project_id}/steadydancer/jobs`：在项目下创建一次 SteadyDancer 生成任务；
  - `GET /projects/{project_id}/steadydancer/jobs/{job_id}`：查询任务状态与结果。
- 文件按项目与 Job 组织在 `STEADYDANCER_DATA_DIR`（默认为 `<repo_root>/assets/projects`）下：
  - `projects/{project_id}/jobs/{job_id}/input/`：本次 Job 的输入（预处理后的 ref_image.png、positive/negative 等）；
  - `projects/{project_id}/jobs/{job_id}/output/`：生成的视频等结果文件；
  - `projects/{project_id}/jobs/{job_id}/tmp/`：中间临时文件，按需清理。
