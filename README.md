# SteadyDancer Monorepo

本仓库采用 monorepo 结构，主要目录如下：

- `apps/`：业务应用（API / Web / Worker 等）。
- `libs/`：共享代码库。
- `infra/`：部署与基础设施。
- `scripts/`：开发与运维脚本。
- `docs/`：总体文档。
- `assets/`：静态资源与示例素材。
- `models/`：模型权重与运行时数据（不提交到 Git）。
- `third_party/`：上游仓库 Git submodule（只读）。

硬性规范与 Agent 约束见根目录 `AGENTS.md`。
整体架构说明见 `docs/architecture.md`，快速上手指南见 `docs/quickstart.md`。

