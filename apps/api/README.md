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

