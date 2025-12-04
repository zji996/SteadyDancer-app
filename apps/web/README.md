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

