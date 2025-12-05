# SteadyDancer API 与数据模型文档

本文档专门维护 SteadyDancer 后端的 HTTP 接口定义与核心数据模型（数据库表结构）。  
建议配合 `docs/architecture.md` 一起阅读：架构文档负责描述高层组件和职责，本文件聚焦在「接口 + 表结构」细节。

---

## 1. 总览

- API 基于 FastAPI 实现，入口：`apps/api/main.py`。
- 默认监听地址：`http://0.0.0.0:8000`（开发环境通过 `scripts/dev_api.sh` 启动）。
- 后端主要分为两类接口：
  - 元信息与健康检查；
  - 业务接口：Project / Asset / Experiment / Job / 低级 SteadyDancer 队列接口。

文中所有路径均以 `http://localhost:8000` 为示例基准 URL。

---

## 2. 元信息接口

- `GET /health`
  - 功能：基础存活检查。
  - 返回示例：`{ "status": "ok" }`

- `GET /models/info`
  - 功能：返回当前解析到的 `MODELS_DIR` 信息。
  - 返回字段：
    - `models_dir`: 实际使用的模型目录绝对路径。
    - `env_MODELS_DIR`: 环境变量 `MODELS_DIR` 的原始值（若设置）。

---

## 3. Project / Asset / Experiment / Job 接口

这一部分是推荐使用的「工作台」层接口，用于管理项目、参考图、舞蹈视频、实验配置以及具体的生成任务。

### 3.1 Project（项目）

#### 3.1.1 列出项目

- `GET /projects`
- 返回：`ProjectOut[]`
  - `id: UUID`
  - `name: string`
  - `description?: string`

#### 3.1.2 创建项目

- `POST /projects`
- 请求体：

  ```json
  {
    "name": "Demo Project",
    "description": "可选描述"
  }
  ```

- 返回：`ProjectOut`

#### 3.1.3 查询项目

- `GET /projects/{project_id}`
- 返回：`ProjectOut`

---

### 3.2 ReferenceAsset（参考图资产）

参考图资产用于表示一个「角色 / 人物」，通常对应一张或多张图片。

#### 3.2.1 创建参考图资产

- `POST /projects/{project_id}/refs`
- 请求体：

  ```json
  {
    "name": "角色 A",
    "source_image_path": "path/to/ref_image.png",
    "meta": {
      "prompt": "a dancer in red dress"
    }
  }
  ```

  - `source_image_path` 可以是绝对路径，或相对仓库根目录的路径；
  - API 会将该文件拷贝到  
    `<STEADYDANCER_DATA_DIR>/projects/{project_id}/refs/{ref_id}/source/` 下。

- 返回：`ReferenceAssetOut`
  - `id: UUID`
  - `project_id: UUID`
  - `name: string`
  - `image_path: string`（拷贝后的绝对路径）
  - `meta?: object`

#### 3.2.2 查询参考图资产

- `GET /projects/{project_id}/refs/{ref_id}`
- 返回：`ReferenceAssetOut`

#### 3.2.3 列出参考图资产

- `GET /projects/{project_id}/refs`
- 返回：`ReferenceAssetOut[]`

---

### 3.3 MotionAsset（动作 / 舞蹈资产）

动作资产用于表示一段 driving video，可以被多个实验复用。

#### 3.3.1 创建动作资产

- `POST /projects/{project_id}/motions`
- 请求体：

  ```json
  {
    "name": "舞蹈片段 1",
    "source_video_path": "path/to/driving_video.mp4",
    "meta": {
      "style": "hiphop"
    }
  }
  ```

  - 文件会被拷贝到  
    `<STEADYDANCER_DATA_DIR>/projects/{project_id}/motions/{motion_id}/source/`。

- 返回：`MotionAssetOut`
  - `id, project_id, name, video_path, meta`

#### 3.3.2 查询动作资产

- `GET /projects/{project_id}/motions/{motion_id}`
- 返回：`MotionAssetOut`

#### 3.3.3 列出动作资产

- `GET /projects/{project_id}/motions`
- 返回：`MotionAssetOut[]`

---

### 3.4 Experiment（实验）

实验描述「参考图 + 动作 + 默认 SteadyDancer 配置 + 一个规范化输入目录」，用于在其上重复跑多个 Job。

#### 3.4.1 创建实验

- `POST /projects/{project_id}/experiments`
- 请求体示例：

  ```json
  {
    "name": "角色 A 跳舞蹈片段 1",
    "description": "一图一舞实验",
    "reference_id": "ref-uuid",
    "motion_id": "motion-uuid",
    "source_input_dir": "third_party/SteadyDancer/preprocess/output/example_pair",
    "config": {
      "size": "1024*576",
      "frame_num": 81,
      "sample_guide_scale": 5.0,
      "condition_guide_scale": 1.0,
      "end_cond_cfg": 0.4,
      "base_seed": 106060,
      "cuda_visible_devices": null
    }
  }
  ```

  - `source_input_dir` 必须是一个已经完成预处理的 pair_dir；
  - API 会将其拷贝到  
    `<STEADYDANCER_DATA_DIR>/projects/{project_id}/experiments/{experiment_id}/input/`。

- 返回：`ExperimentOut`
  - `id, project_id, reference_id?, motion_id?`
  - `name, description?`
  - `input_dir?`：实验级规范化输入目录绝对路径
  - `config?`：JSON，对应请求体中的 `config`

#### 3.4.2 查询实验

- `GET /projects/{project_id}/experiments/{experiment_id}`
- 返回：`ExperimentOut`

#### 3.4.3 列出实验

- `GET /projects/{project_id}/experiments`
- 返回：`ExperimentOut[]`

---

### 3.5 Job（生成任务）

Job 是一次实际的 SteadyDancer I2V 生成任务。可以直接挂在 Project 下，也可以通过 Experiment 创建。

#### 3.5.1 直接在 Project 下创建 Job（快捷路径）

- `POST /projects/{project_id}/steadydancer/jobs`
- 请求体：`SteadyDancerJobCreate`

  ```json
  {
    "input_dir": "<pair_dir 绝对路径或相对仓库根路径>",
    "prompt_override": null,
    "size": "1024*576",
    "frame_num": 81,
    "sample_guide_scale": 5.0,
    "condition_guide_scale": 1.0,
    "end_cond_cfg": 0.4,
    "base_seed": 106060,
    "cuda_visible_devices": null
  }
  ```

  - API 会为该 Job 创建目录：  
    `<STEADYDANCER_DATA_DIR>/projects/{project_id}/jobs/{job_id}/`；
  - 将 `input_dir` 拷贝到 `jobs/{job_id}/input/`；
  - 将 `jobs/{job_id}/input/` 作为 Celery 任务的 `input_dir`。

- 返回：`ProjectJobCreated`
  - `project_id, job_id, task_id`

#### 3.5.2 从 Experiment 创建 Job（推荐）

- `POST /projects/{project_id}/experiments/{experiment_id}/steadydancer/jobs`
- 请求体：同 `SteadyDancerJobCreate`，但 `input_dir` 通常可以忽略（使用实验的规范化输入目录），仍然可以通过其它字段覆盖 experiment-level config。
- 返回：`ProjectJobCreated`

#### 3.5.3 查询 Job 状态

- `GET /projects/{project_id}/steadydancer/jobs/{job_id}`
- 返回：`ProjectJobStatus`
  - `project_id, job_id, task_id`
  - `state: string`（Celery 状态：`PENDING` / `STARTED` / `SUCCESS` / `FAILURE` 等）
  - `result?: object`（当任务成功时）
    - `success: bool`
    - `video_path: string | null`：规范化后的结果视频路径（位于 Job 的 `output/` 目录）
    - `stdout: string`
    - `stderr: string`
    - `return_code: int`

#### 3.5.4 列出项目下的所有 Job

- `GET /projects/{project_id}/steadydancer/jobs`
- 返回：`ProjectJobSummary[]`
  - `id: UUID`（job_id）
  - `project_id: UUID`
  - `experiment_id?: UUID`
  - `task_id: string`
  - `job_type: string`（当前为 `"steadydancer_i2v"`）
  - `status: string`
  - `result_video_path?: string`

#### 3.5.5 列出某个实验下的 Job

- `GET /projects/{project_id}/experiments/{experiment_id}/steadydancer/jobs`
- 返回：`ProjectJobSummary[]`（仅该实验下的 Job）

#### 3.5.6 下载结果视频

- `GET /projects/{project_id}/steadydancer/jobs/{job_id}/download`
  - 功能：直接以 HTTP 文件流返回该 Job 的结果视频。
  - 前置条件：
    - Job 属于给定 `project_id`；
    - Job 已成功完成（`success = true`），且 `result_video_path` 非空；
    - 磁盘上存在该文件。
  - 返回：
    - 成功：`200 OK`, `Content-Type: video/mp4`，`Content-Disposition` 带文件名；
    - 各类错误：返回 `404`，带有相应错误说明。

---

### 3.6 低级 SteadyDancer 队列接口（兼容 / 调试用）

这部分接口直接包装 Celery 任务，不经过 Project / Experiment / Job 的管理层，主要用于兼容或调试。

#### 3.6.1 提交任务

- `POST /steadydancer/jobs`
- 请求体：`SteadyDancerJobCreate`（同上）
- 行为：
  - 将请求转化为 Celery 任务 `steadydancer.generate.i2v`；
  - 不在数据库中记录 Job（仅依赖 Celery）。
- 返回：`{ "task_id": "..." }`

#### 3.6.2 查询任务状态

- `GET /steadydancer/jobs/{task_id}`
- 返回：

  ```json
  {
    "task_id": "...",
    "state": "PENDING|STARTED|SUCCESS|FAILURE|...",
    "result": {
      "success": true,
      "video_path": "...",
      "stdout": "...",
      "stderr": "...",
      "return_code": 0
    } | null
  }
  ```

---

## 4. 数据库表结构（概要）

数据库使用 Postgres，连接字符串通过 `DATABASE_URL` 配置，ORM 模型定义在 `apps/api/db.py` 中。  
本节给出关键表的逻辑结构，字段类型略去具体 SQL 细节。

### 4.1 projects

- `id UUID PRIMARY KEY`
- `name TEXT NOT NULL`
- `description TEXT NULL`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

### 4.2 reference_assets

- `id UUID PRIMARY KEY`
- `project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE`
- `name TEXT NOT NULL`
- `image_path TEXT NOT NULL`（参考图文件路径）
- `meta JSONB NULL`（可选元信息）
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

### 4.3 motion_assets

- `id UUID PRIMARY KEY`
- `project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE`
- `name TEXT NOT NULL`
- `video_path TEXT NOT NULL`（driving video 文件路径）
- `meta JSONB NULL`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

### 4.4 experiments

- `id UUID PRIMARY KEY`
- `project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE`
- `reference_id UUID NULL REFERENCES reference_assets(id) ON DELETE SET NULL`
- `motion_id UUID NULL REFERENCES motion_assets(id) ON DELETE SET NULL`
- `name TEXT NOT NULL`
- `description TEXT NULL`
- `input_dir TEXT NULL`（实验级规范化输入目录）
- `config JSONB NULL`（默认 SteadyDancer 配置）
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

### 4.5 generation_jobs（Job）

- `id UUID PRIMARY KEY`
- `project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE`
- `experiment_id UUID NULL REFERENCES experiments(id) ON DELETE SET NULL`
- `task_id TEXT UNIQUE NOT NULL`（Celery 任务 ID）
- `job_type TEXT NOT NULL`（当前为 `"steadydancer_i2v"`）
- `status TEXT NOT NULL`（Celery 状态）
- `input_dir TEXT NOT NULL`（Job 级别输入目录）
- `params JSONB NOT NULL`（请求参数快照）
- `success BOOLEAN NULL`
- `result_video_path TEXT NULL`（结果视频规范化路径）
- `error_message TEXT NULL`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`
- `finished_at TIMESTAMPTZ NULL`

---

## 5. 说明与约定

- 本文档是接口 / 数据模型的「单一事实来源」：
  - 如新增或修改 HTTP 接口、重要字段或表结构，需同步更新本文件；
  - 高层架构变化则更新 `docs/architecture.md`。
- 实际请求 / 返回示例可根据需要扩展到单独的 API 参考文档或 OpenAPI 描述；
  当前版本以文字说明为主，避免与代码重复维护过多样例。

