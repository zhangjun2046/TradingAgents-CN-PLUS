# H5-Architecture：手机端工程交接

| 项 | 内容 |
|----|------|
| 生成单元 | P3.5 H5 我的报告列表 |
| 生成日期 | 2026-10-26 |
| 对应 Git 提交 | 验收通过并提交后回填（本文件与功能分支 `feat/report/P3.5-h5-report-list` 一起提交） |
| 主要读者 | B（P4 分享页）、A（P5.2 联调） |
| 设计依据 | `doc/tech_solution.md` 第 3 节、4.1、4.2；报告接口见 `doc/handoff/Backend-API-Report.md` |

本文件描述 `mobile/` 在 B 线 `line/report` 上的现状（含 P3.1 骨架、P3.3 单股分析、P3.4 进度、P3.5 报告列表）。A 的账号页仍是占位，由 A 在 `line/auth` 的 P3.2 填充，不要把对方线分支合并进来。

---

## 1. 技术栈与访问方式

| 项 | 值 |
|----|----|
| 框架 | Uniapp（Vue3 + `<script setup>` + TypeScript），只编译 H5 |
| 状态 | Pinia：`auth`、`analysis` |
| UI | `@dcloudio/uni-ui`（easycom，页面里直接写 `uni-xxx`） |
| 日期 | dayjs |
| 开发地址 | `http://localhost:3100/m/`（hash 路由） |
| 接口 | 开发期 Vite 把 `/api` 代理到 `http://localhost:8000` |
| 分享页 | 不在 `mobile/` 内。开发期打开 PC 前端 `http://localhost:3000/s/{token}` |

`manifest.json` 的 H5 段：`publicPath=/m/`，`router.mode=hash`，`router.base=/m/`，`devServer.port=3100`。

环境变量：

| 文件 | 变量 | 含义 |
|------|------|------|
| `mobile/.env.development` | `VITE_API_BASE` 为空 | 请求走当前域名的 `/api` |
| 同上 | `VITE_PUBLIC_APP_URL=http://localhost:3000` | 分享链接的站点。生产同域部署时留空，则用当前页面的 origin |
| `mobile/.env.production` | `VITE_API_BASE` 为空 | 与 PC 同域 |

## 2. 启动与构建

在仓库的 `mobile\` 目录执行（依赖已在该目录的 `node_modules`，不要全局安装）：

```powershell
cd D:\coding\TradingAgents-CN\mobile
npm run dev:h5
npm run build:h5
npm run type-check
```

后端与 PC 前端仍用仓库根目录的 `.\start.ps1`。手机模式验收地址：`http://localhost:3100/m/#/pages/reports/list`。

## 3. 目录结构（现状）

```text
mobile/
├── package.json
├── vite.config.ts              # 端口 3100，/api -> localhost:8000
├── .env.development
├── .env.production
└── src/
    ├── main.ts                 # createSSRApp + Pinia
    ├── App.vue                 # 引入 styles/common.scss
    ├── manifest.json
    ├── pages.json              # 页面清单 + 底部三个标签（P3.1 已登记，之后不要改页面列表）
    ├── pages/
    │   ├── analysis/single.vue # AI分析（tab）：表单 + 进度 + 完成后跳分享页
    │   ├── reports/list.vue    # 分析报告（tab）：我的报告列表（P3.5）
    │   ├── mine/index.vue      # 我的（tab）：最简登录态，账号内容由 A 的 P3.2 填充
    │   ├── auth/login.vue      # 最简用户名密码登录（A 的 P3.2 会替换）
    │   ├── auth/register.vue   # 空壳，归 A
    │   ├── auth/forgot.vue     # 空壳，归 A
    │   ├── auth/change-password.vue # 空壳，归 A
    │   ├── legal/agreement.vue # 空壳，归 A
    │   └── legal/privacy.vue   # 空壳，归 A
    ├── components/
    │   ├── AnalysisProgress.vue
    │   ├── AnalystCards.vue
    │   ├── DepthSelector.vue
    │   ├── ModelSelect.vue
    │   └── StockCodeInput.vue
    ├── api/
    │   ├── request.ts
    │   ├── auth.ts
    │   ├── analysis.ts
    │   ├── reports.ts          # 列表 + 创建/复用分享
    │   └── config.ts           # 公开模型；404 时用内置列表
    ├── stores/
    │   ├── auth.ts
    │   └── analysis.ts         # 提交、3 秒轮询、刷新恢复、完成后分享跳转
    ├── constants/              # 市场、深度、分析师、内置模型
    ├── utils/
    │   ├── storage.ts          # 与 PC 共用 localStorage
    │   ├── env.ts              # 公开地址与 /s/{token}
    │   └── validators.ts
    └── styles/
        ├── variables.scss      # 主色 #409EFF
        └── common.scss
```

方案里的 `utils/guard.ts`、`components/CaptchaImage.vue` 等账号组件归 A，B 线没有新建。登录检查写在各页面自己的 `onShow` 或按钮点击里。

## 4. 页面清单

底部三个标签：AI分析、分析报告、我的。`pages.json` 已打开报告页的下拉刷新（`enablePullDownRefresh: true`）。

| 路径 | 导航标题 | 谁填内容 | 是否需要登录 |
|------|----------|----------|----------------|
| `pages/analysis/single` | AI分析 | B（已完成） | 可先看表单；点「开始智能分析」才要求登录 |
| `pages/reports/list` | 分析报告 | B（P3.5） | 是。未登录跳登录页，登录后回到本页 |
| `pages/mine/index` | 我的 | A（P3.2） | 目前可看最简登录态，不强制跳转 |
| `pages/auth/login` | 登录 | A 将替换最简登录 | 公开 |
| `pages/auth/register` | 注册 | A | 公开，目前空壳 |
| `pages/auth/forgot` | 忘记密码 | A | 公开，目前空壳 |
| `pages/auth/change-password` | 修改密码 | A | 目前空壳 |
| `pages/legal/agreement` | 用户协议 | A | 公开，目前空壳 |
| `pages/legal/privacy` | 隐私政策 | A | 公开，目前空壳 |

登录成功后的回跳：登录页读取 `redirect`。目标是三个标签页之一时用 `switchTab`，否则 `reLaunch`。

## 5. 登录态（与 PC 共用）

`mobile/src/utils/storage.ts` 直接读写 `window.localStorage`，不用 `uni.setStorageSync`（后者会多包一层 JSON，和 PC 对不上）。

| 键 | 内容 |
|----|------|
| `auth-token` | access token 原文 |
| `refresh-token` | refresh token 原文 |
| `user-info` | 用户信息 JSON |

同域时，H5 登录后同一浏览器打开 PC（`localhost` 不同端口不算同域）才会共享登录态。开发期两个端口各自登录。生产同域部署后可以共享。

进行中的分析任务另存在 `sessionStorage`（键 `ha-current-task`），刷新单股分析页可以恢复进度。这与登录态无关。

## 6. 请求封装（`api/request.ts`）

1. `baseURL` 默认空，请求发到 `/api...`。
2. 自动带 `Authorization: Bearer <auth-token>`。
3. 成功体 `{ success, data, message }` 时，调用方拿到的是 `data`。
4. `success=false` 或 HTTP ≥ 400：默认 toast 并拒绝；`silent: true` 时不 toast，由页面自己提示。
5. 401：用 refresh token 调 `POST /api/auth/refresh`，并发请求只刷新一次，成功后重放原请求。刷新失败则清空登录态并跳到登录页，带上当前页 `redirect`。
6. 超时 30 秒。网络失败提示「网络异常，请稍后重试」。

## 7. 两个 store

| store | 文件 | 职责 |
|-------|------|------|
| `auth` | `stores/auth.ts` | 用户名密码登录、本地退出、从 localStorage 恢复。`isLoggedIn` 看 token 是否存在 |
| `analysis` | `stores/analysis.ts` | 单股分析提交、每 3 秒查进度、页面隐藏时暂停、刷新后恢复、完成后 `POST /api/reports/{id}/share` 并 `location.href` 到分享页 |

报告列表没有单独的 store，数据放在 `pages/reports/list.vue` 里。

## 8. 我的报告列表（P3.5）

页面：`pages/reports/list.vue`。接口封装：`api/reports.ts` 的 `getReportList`、`createOrReuseShare`。

| 行为 | 说明 |
|------|------|
| 列表 | `GET /api/reports/list?page=&page_size=20`。可带 `search_keyword`、`market_filter`（A股 / 港股 / 美股） |
| 展示 | 市场、代码、名称、分析日期（基准日）、状态、创建时间（`YYYY-MM-DD HH:mm`） |
| 刷新 | 每次进入页面重新拉第 1 页；支持下拉刷新 |
| 翻页 | 上拉或点「上拉加载更多」，每页 20 条 |
| 空状态 | 「暂无报告，去发起一次 AI 分析」，按钮切到 AI分析 |
| 点击 | 仅 `completed`（或状态为空，后端默认已完成）可点。`POST /api/reports/{id}/share` 后打开 `{VITE_PUBLIC_APP_URL}/s/{token}`。分享页顶部有「返回报告列表」：开发期（分享页在 `:3000`）回到 `http://localhost:3100/m/#/pages/reports/list`，同域部署回到当前站点 `/m/#/pages/reports/list` |
| 报告 id | 优先 `analysis_id`，否则列表 `id`，再否则 `task_id` |
| 未完成 | 非完成不可点。`failed` 显示「失败」，其余显示「分析中」 |
| 过期分享 | 列表上不显示剩余天数。点击时后端复用未过期链接，过期则新建 |

原型图上的观点、置信度、风险、分享剩余天数，列表接口没有这些字段，本页不展示，也不逐条再查分享。

日志：`[Reports] loaded`、`[Reports] open`、`[Reports] redirect`。

验收时用种子账号 `test_user_a` / `test_user_b`（密码见 `Backend-API-Report.md`）。`admin` 能看到全部报告，不能用来证明「只显示本人报告」。

## 9. 给下一单元的约定

- P4 改的是 PC 分享页 `frontend/src/views/Reports/ReportShare.vue`，H5 只负责跳到 `/s/{token}`。改版时保留分享页顶部的「返回报告列表」。
- 不要改 `pages.json` 的页面列表。下拉刷新已经打开。
- 不要新建 `utils/guard.ts`（归 A）。新的需登录页面在自己的 `onShow` 里检查 `auth.isLoggedIn`，跳转 `/pages/auth/login?redirect=当前路径`。
- 公开模型接口失败时，`api/config.ts` 使用内置列表，并 `console.info` 记录兜底。集成后接口可用会自动走真实数据。
