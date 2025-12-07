# SteadyDancer Web

基于 React + Vite 的前端应用，主要作为 SteadyDancer 的 Web 控制台与演示界面。

## 开发启动

在仓库根目录安装依赖（使用 npm workspaces）：

```bash
npm install
```

启动 web：

```bash
cp apps/web/.env.example apps/web/.env
npm run web:dev
```

默认将通过 `VITE_API_BASE_URL` 调用 `apps/api` 提供的 HTTP 接口。

## 约定

- 共享 UI 组件从 `libs/ts_ui` 引入（包名 `@steadydancer/ts-ui`）。
- 不直接依赖 `third_party/` 中的任何代码。

## API 集成指引（给前端 / Agent）

### 环境变量

- `VITE_API_BASE_URL`：后端 API 基础地址，例如 `http://localhost:8000`。
- `VITE_API_KEY`（可选但推荐）：
  - 对应后端的 `STEADYDANCER_API_KEY`；
  - 所有业务请求应在 Header 中带上：`X-API-Key: ${VITE_API_KEY}`。

### 请求约定

- 请求头：
  - `Content-Type: application/json`（除下载接口外）；
  - `X-API-Key: <来自 VITE_API_KEY>`（若后端启用了 API Key）。
- 错误处理：
  - 所有业务错误统一为：

    ```json
    {
      "detail": {
        "code": "SOME_ERROR_CODE",
        "message": "Human readable message",
        "extra": { "..." : "调试信息（可选）" }
      }
    }
    ```

  - 前端可统一从 `detail.code` 做分支逻辑，从 `detail.message` 做提示文案。

### 典型调用流程（建议的 Web 控制台流程）

1. **选择或创建 Project**
   - `GET /projects`：列出所有项目（最近创建的在前）。
   - `POST /projects`：
     - 请求体：`{ "name": string, "description"?: string }`
     - 返回：`ProjectOut`（含 `id`），若重名返回错误码 `PROJECT_NAME_CONFLICT`。

2. **在 Project 下注册资产（可选但推荐）**
   - 参考图（ReferenceAsset）：
     - `POST /projects/{project_id}/refs`
     - 请求体字段：
       - `name`: 显示用名称；
       - `source_image_path`: 绝对路径或「仓库根目录相对路径」，例如 `assets/examples/ref.png`；
       - `meta`?: 任意 JSON 元数据。
   - 动作资产（MotionAsset）：
     - `POST /projects/{project_id}/motions`
     - 字段类似，只是 `source_video_path` 替换为 driving video 路径。

3. **创建 Experiment**
   - 两种方式：
     1. 已有预处理好的输入目录（pair_dir）：
        - `POST /projects/{project_id}/experiments`
        - 重点字段：
          - `source_input_dir`: 绝对或 repo 根相对目录；
          - `reference_id` / `motion_id`: 可选绑定到已有资产；
          - `config`: 对应 SteadyDancer 配置（尺寸、帧数、prompt 覆盖等）。
     2. 让 Worker 做预处理：
        - `POST /projects/{project_id}/experiments/preprocess`
        - 使用已有的 `reference_id` + `motion_id`，后端会触发 Celery 预处理任务；
        - 返回中包含 `experiment_id` 和 `task_id`，可用于在 Worker 侧查询预处理进度。

4. **发起生成 Job**
   - 直接从 Experiment 发起：
     - `POST /projects/{project_id}/experiments/{experiment_id}/steadydancer/jobs`
     - 请求体为 `SteadyDancerJobCreate`，可覆盖部分配置，例如帧数、尺寸等；
     - 返回：`{ project_id, job_id, task_id }`。
   - 或者直接从任意输入目录发起（不经过 Experiment）：
     - `POST /projects/{project_id}/steadydancer/jobs`
     - 请求体同样是 `SteadyDancerJobCreate`，`input_dir` 会被复制到 Job 自己的 `input/` 目录。

5. **轮询 Job 状态 + 获取结果**
   - 查询单个 Job 状态：
     - `GET /projects/{project_id}/steadydancer/jobs/{job_id}`
     - 成功时返回：

       ```json
       {
         "project_id": "...",
         "job_id": "...",
         "task_id": "...",
         "state": "PENDING|STARTED|SUCCESS|FAILURE|REVOKED|EXPIRED|...",
         "result": {
           "success": true,
           "video_path": "绝对路径（后端本地文件）或 null",
           "stdout": "...",
           "stderr": "...",
           "return_code": 0
         }
       }
       ```

   - 列出 Project 下所有 Job：
     - `GET /projects/{project_id}/steadydancer/jobs`
   - 下载结果视频：
     - `GET /projects/{project_id}/steadydancer/jobs/{job_id}/download`
     - 返回 `video/mp4` 文件流。

6. **取消 Job（可选）**
   - `POST /projects/{project_id}/steadydancer/jobs/{job_id}/cancel`
   - 请求体可选字段：`{ "reason"?: string }`。

以上流程仅是推荐的 UI 设计顺序，前端 / Agent 可以在此基础上自由组合页面和交互，只要遵守：

- 使用 `VITE_API_BASE_URL` + `VITE_API_KEY`；
- 遵循路径和错误码约定（详见 `apps/api/README.md`），即可稳定接入后端。
