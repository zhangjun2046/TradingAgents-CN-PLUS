# 部署与上线检查清单（A 线 P5.4）

给最终集成后的内测/上线用。A 线相关项由 A 确认；**部署项在最终集成后由 B 确认并在本文件打勾**。

登记：本文件随 P5.4 合入 `line/auth`。  
`doc/` 备份：本机 `Desktop/TradingAgents-CN-doc-backup/2026-10-26/doc`（对应计划中的 `D:\coding\TradingAgents-CN-doc-backup\{日期}\`，A 当前工作区为 Mac）。

---

## 0. 协议文案适配说明（供业务确认）

原稿为「蒙关牧」**微信小程序商城**。本产品是 **HunterAgent** 股票分析 PC + H5。仓库已写入**改写后**的正文，不能使用商城条款原文。请 A 对照下一节「必须改 / 已改」审阅页面后再点验收。

---

## 1. A 线上线检查

| # | 项 | 状态 | 说明 |
|---|----|------|------|
| A1 | PC《用户协议》《隐私政策》为正式文案 | 已替换，待 A 审阅 | `frontend/public/legal/*.md`；PC 协议页 `fetch /legal/` |
| A2 | H5 协议页与 PC 同步 | 已替换，待 A 审阅 | `mobile/src/static/legal/*.md` 与 `mobile/src/utils/legal-texts.ts` |
| A3 | 生产 HTTPS | 待最终集成后由 B 确认 | 正式环境必须 HTTPS；裸 IP + HTTP 仅内测 |
| A4 | 生产 `DEBUG=false`（关闭 `/docs`） | 待生产写入 `.env` | 代码已支持：`DEBUG=false` 时 `docs_url`/`redoc_url` 为 None。**不要把开发机 `.env` 的 DEBUG 改掉后提交 Git**。`.env.example` 仍为开发默认 `true` |
| A5 | mock 短信已关闭（`SMS_PROVIDER=tencent`） | **阻塞：须 P5.3** | 生产若 `DEBUG=false` 且仍为 mock，启动会警告。签名/模板/密钥只进 `.env` |
| A6 | `admin` 默认密码已修改 | **待 A 人工确认** | 勿把新密码写入 Git 或本文件 |
| A7 | 迁移脚本已执行 | 待部署环境执行 | 见第 3 节；应用启动 `ensure_indexes` 会尝试建手机号/邮箱索引 |
| A8 | 来源与许可说明保留 | 已保留 | 根目录 `README.md` / `LICENSE` 未改 |

---

## 2. 部署项（待 B 确认）

P5.1 合入并最终集成 2 完成后，B 在 P5.2 前打勾。

| # | 项 | 状态 | 说明 |
|---|----|------|------|
| B1 | Nginx：`/` PC、`/m/` H5、`/s/:token` 分享、`/api` 后端 | 待最终集成后由 B 确认 | P5.1 |
| B2 | Nginx 透传真实 IP（短信 IP 限流） | 待最终集成后由 B 确认 | `X-Forwarded-For` / `X-Real-IP` |
| B3 | Docker 构建含 H5 | 待最终集成后由 B 确认 | P5.1 |
| B4 | 同一备案域名 HTTPS 证书 | 待最终集成后由 B 确认 | |

---

## 3. 迁移执行顺序（部署时）

在目标环境 MongoDB 可连后执行（工作区仓库根目录、使用项目 venv）：

1. `python scripts/migrations/fix_users_email_index.py`（P1.1：email 部分唯一 + phone 稀疏唯一；同键冲突则跳过）
2. `python scripts/migrations/backfill_report_user_id.py`（P1.5：历史报告 user_id；B 线脚本，最终集成后执行）
3. 按需：`scripts/dev/seed_test_users.py`（仅测试环境）

启动应用后 `ensure_indexes` 会补齐用户索引。

---

## 4. 回滚方式（概要）

- 应用：回退到上一 Git 标签 / 上一镜像，保留 MongoDB。
- 协议文案：回退 `frontend/public/legal/` 与 `mobile/src/utils/legal-texts.ts`。
- 索引迁移：一般不自动删除索引；回滚应用代码即可登录。
- 短信：将 `.env` 的 `SMS_PROVIDER` 临时改回 `mock` 仅用于紧急内测，**生产内测目标仍应走腾讯云**。

---

## 5. 生产环境变量（A 线相关，密钥不入库）

| 变量 | 生产建议 |
|------|----------|
| `DEBUG` | `false` |
| `SMS_PROVIDER` | `tencent`（P5.3 后） |
| `SMS_SECRET_ID` / `SMS_SECRET_KEY` / `SMS_SDK_APP_ID` / `SMS_SIGN_NAME` / `SMS_TEMPLATE_ID` | 仅 `.env` |
| `SMS_REGION` | 默认 `ap-guangzhou` |

---

## 6. 建议启动顺序（内测）

1. MongoDB、Redis
2. 后端（8000）
3. PC（3000）
4. H5（3100，`/m/`）
5. 打开协议页确认正文；用非 admin 账号走注册（发短信须先过图形码）
