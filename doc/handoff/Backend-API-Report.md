# Backend-API-Report：B 线后端接口交接文档

| 项 | 内容 |
|----|------|
| 生成单元 | P1.7 分享 30 天 + 公开字段 + 免登录导出（含 P1.5 报告隔离的接口说明） |
| 生成日期 | 2026-10-23 |
| 对应代码 | 分支 `feat/report/P1.7-share-export`，叠在 P1.5（`feat/report/P1.5-report-isolation`，commit `e184456`）之上；本单元提交号见 PR |
| 主要读者 | B（P3、P4）、A（P5.2 联调） |
| 设计依据 | `doc/tech_solution.md` 7.4（报告隔离）、7.5（任务归属，P1.6 未完成）、7.6（分享改造） |

> 状态说明：报告隔离（P1.5）与分享 / 导出（P1.7）已实现；**分析任务归属校验（P1.6）尚未实现**，见第 3 节「已知限制」。

---

## 1. 通用约定

- 基础路径：报告相关 `/api/reports`，分析任务相关 `/api/analysis`。
- 需登录的接口带 `Authorization: Bearer <access_token>`；token 来自 `POST /api/auth/login`（用户名 + 密码，开发期可用 `admin` 或种子账号）。
- 成功响应形如 `{ "success": true, "data": ..., "message": "..." }`。
- 错误响应形如 `{ "detail": "..." }`，常见状态码：401 未登录、404 不存在（含越权）、400 参数错误或导出能力不可用、429 限流、500 服务内部错误。
- 时间字段：分享相关 `created_at` / `expires_at` 为带 `+08:00` 的 ISO 字符串。

## 2. 报告接口（`app/routers/reports.py`）

### 2.1 归属校验规则（P1.5）

| 角色 | 可见范围 |
|------|----------|
| 普通用户 | 仅 `analysis_reports.user_id == 自己 id` 的报告 |
| 管理员（`is_admin=true`） | 全部报告，含回填失败（`owner_unknown=true`、`user_id=null`）的历史报告 |
| 免登录分享访问 | 仅凭有效 `token` 读取该份报告的公开字段，见第 2.3 节 |

- 报告在 `simple_analysis_service` 保存时写入 `user_id`（字符串）。
- 越权一律返回 **404 "报告不存在"**，不暴露数据是否存在；日志 `report_access_denied report=... user=...`。
- 报告标识 `report_id` 可用：`_id`（ObjectId 字符串）、`analysis_id` 或 `task_id`。

### 2.2 需登录接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/reports/list` | 列表。参数：`page`、`page_size`（1~100）、`search_keyword`、`market_filter`、`start_date`、`end_date`、`stock_code`。普通用户只返回自己的报告 |
| GET | `/api/reports/{report_id}/detail` | 报告详情（完整内部字段，含 `model_info`、`tokens_used`、`decision`） |
| GET | `/api/reports/{report_id}/content/{module}` | 某个模块正文，如 `market_report`；模块不存在 404 |
| DELETE | `/api/reports/{report_id}` | 删除报告（先校验归属，再按主键删除） |
| GET | `/api/reports/{report_id}/download?format=markdown\|json\|pdf\|docx` | 登录态下载（私有导出，含完整内部字段，仅限有权限者） |
| POST | `/api/reports/{report_id}/share` | 创建或复用分享链接。Body：`{ "expires_days": 30, "regenerate": false }`，均可省略 |
| GET | `/api/reports/{report_id}/share` | 查询当前有效分享；无则 `data=null` |
| DELETE | `/api/reports/{report_id}/share` | 撤销该报告全部有效分享；返回 `{ "revoked": n }` |

分享创建规则（P1.7）：

- 默认有效期 **30 天**（`DEFAULT_EXPIRES_DAYS=30`），`expires_days` 取值 1~365。
- 复用：该报告存在**未撤销且未过期**的分享时直接返回原链接；已过期则自动新建；`regenerate=true` 先撤销旧链接再新建。
- 响应 `data`：`{ token, path: "/s/{token}", expires_at, created_at, view_count }`。
- 分享记录集合 `report_shares`：`token`（唯一）、`lookup_ids`、`created_by`、`created_at`、`expires_at`、`revoked_at`、`view_count`、`download_count`。
- 注意：**P1.7 之前创建的旧分享保持原有效期（多为 7 天）**，不会被自动延长；到期后再次分享即得到 30 天新链接。

### 2.3 免登录公开接口

#### `GET /api/reports/share/{token}`

凭 token 读取公开报告；无效、过期、撤销统一 404 `报告不存在或链接已失效`；每次成功读取 `view_count + 1`。

`data` 字段（白名单）：

| 字段 | 说明 |
|------|------|
| `stock_symbol`、`stock_name`、`analysis_date`、`created_at` | 基本信息 |
| `recommendation`、`risk_level`、`confidence_score`、`summary`、`key_points` | 结论摘要 |
| `analysts` | 参与分析师列表，如 `["market","fundamentals"]`，缺失为 `[]` |
| `research_depth` | 研究深度，缺失为 `1` |
| `decision` | 仅含 `action`、`target_price`、`confidence`、`risk_score`（缺失的键不输出；非字典为 `{}`）；**不含** `reasoning` |
| `expires_at` | 该分享的到期时间 |
| `reports` | 按固定模块顺序排列、剔除空内容的模块正文 |

不会输出：`model_info`、`tokens_used`、`execution_time`、`user_id`、`task_id`、`source`、`id` 等内部字段。

#### `GET /api/reports/share/{token}/download?format=markdown|pdf|docx`（新增，免登录）

| 项 | 说明 |
|----|------|
| 默认格式 | `markdown` |
| 内容 | 与公开页一致（使用公开序列化数据，不含内部字段） |
| 响应 | 文件流；`Content-Disposition: attachment; filename="{ASCII 兜底名}"; filename*=UTF-8''{股票代码}_{日期}_HunterAgent.{md\|pdf\|docx}` |
| Content-Type | md：`text/markdown; charset=utf-8`；pdf：`application/pdf`；docx：`application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| 日期取值 | 优先 `analysis_date`，缺失用 `created_at` 日期，再缺失用当天 |
| 计数 | 成功导出后 `report_shares.download_count + 1`；失败不计数 |
| 日志 | `share_download token=abc*** format=pdf`（token 仅显示前 3 位） |

错误码：

| 状态码 | 场景 |
|--------|------|
| 400 | `format` 不是 markdown / pdf / docx；或服务器缺少 PDF / Word 生成能力 |
| 404 | token 无效、过期、已撤销，或报告已被删除（`报告不存在或链接已失效`） |
| 429 | 同一 token 每分钟超过 10 次（`下载过于频繁，请稍后再试`） |
| 500 | 文档生成失败 |

限流实现：Redis 键 `share:dl:{token}:{yyyyMMddHHmm}`（UTC 分钟），`INCR` 后首次设置 120 秒过期，阈值 `DOWNLOAD_RATE_LIMIT_PER_MINUTE=10`。**Redis 不可用时放行**并记警告日志（限流是保护措施，不阻断正常导出）。先限流后查库。PDF / DOCX / Markdown 生成均放入线程池（`run_in_threadpool`），不阻塞事件循环。

PDF 中文字体：
- Windows 开发机使用系统 `simhei.ttf` / `msyh.ttc` 等（`app/utils/report_exporter.py` 自动探测）。
- Docker 后端镜像 `Dockerfile.backend` 已安装 `fonts-noto-cjk`，无需改动；若换镜像须保证装有中文字体，否则 PDF 中文乱码。

## 3. 分析任务接口（`app/routers/analysis.py`）

供 H5 / PC 发起与跟踪单股分析。**目前仍是原有行为，P1.6 才会增加归属校验。**

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/analysis/single` | 提交单股分析，返回 `data.task_id`；任务在后台异步执行，`user_id` 取自登录用户 |
| GET | `/api/analysis/tasks/{task_id}/status` | 进度轮询 |
| GET | `/api/analysis/tasks/{task_id}/result` | 结果；完成后 `data.analysis_id` 可用作 `report_id`，为空时直接用 `task_id` 调分享接口 |
| GET | `/api/analysis/tasks` | 当前用户的任务列表（按 `user_id` 过滤） |
| GET | `/api/analysis/tasks/all` | 全量任务列表（当前未限制管理员，任何已登录用户可调用；P1.6 将改为 `require_admin`） |
| POST | `/api/analysis/tasks/{task_id}/cancel`、DELETE `/api/analysis/tasks/{task_id}` | 取消 / 删除任务 |

已知限制（P1.6 前）：
- 按 `task_id` 操作的任务接口尚未校验任务归属，他人若猜到 `task_id` 可能查看进度；H5 开发时不要依赖"他人任务返回 404"。
- `GET /api/analysis/tasks/all` 与僵尸任务管理接口依赖 A 的 P1.4 `require_admin`，将在 P1.6 切换。

## 4. 脚本用法

均在仓库根目录、激活仓库 `venv` 后执行（遵守 codingplan 2.1：依赖只装在 `venv`，临时目录 `D:\temp`）。

### 4.1 历史报告 user_id 回填：`scripts/migrations/backfill_report_user_id.py`

```powershell
venv\Scripts\python scripts\migrations\backfill_report_user_id.py --dry-run   # 先只统计，不写库
venv\Scripts\python scripts\migrations\backfill_report_user_id.py             # 正式执行
```

- 通过 `task_id`（找不到再按 `result.analysis_id`）关联 `analysis_tasks`，取任务的 `user_id`（兼容旧字段 `user`），统一写成字符串。
- 无法关联的写 `user_id=null` 且 `owner_unknown=true`，仅管理员可见；`ObjectId` 类型的 `user_id` 会规整为字符串。
- 幂等；统计输出：`total`（待处理）、`filled`（已回填）、`unknown`（无法回填）、`normalized`（规整）。
- 上线顺序：先 `--dry-run` 核对，再正式执行，两次统计应一致。

### 4.2 开发种子账号：`scripts/dev/seed_test_users.py`

```powershell
venv\Scripts\python scripts\dev\seed_test_users.py
venv\Scripts\python scripts\dev\seed_test_users.py --password "MyPass123" --reset-password
```

- 在 MongoDB 直接创建普通用户 `test_user_a`、`test_user_b`，默认密码 `Test@123456`，均 `is_admin=false`。
- 幂等：已存在则跳过（不改密码），`--reset-password` 可重置。
- 仅开发环境：`DEBUG=false` 时拒绝执行，除非加 `--force`。

## 5. 联调与测试速查

自动化测试（在仓库根目录）：

```powershell
venv\Scripts\python -m pytest tests\test_share_download.py tests\test_report_share_api.py tests\test_report_isolation.py tests\test_backfill_script.py -q
```

手工验收示例：

1. `admin` 或 `test_user_a` 登录，`POST /api/reports/{report_id}/share` 得到 `token`，确认 `expires_at - created_at` 为 30 天。
2. 不带登录态，浏览器直接打开 `/api/reports/share/{token}/download?format=pdf`（再换 `markdown`、`docx`），下载后打开，确认中文正常、文件名为 `{股票代码}_{日期}_HunterAgent.{ext}`。
3. `DELETE /api/reports/{report_id}/share` 撤销后，再访问导出地址应返回 404。
4. `test_user_b` 访问 `test_user_a` 的 `/api/reports/{id}/detail` 返回 404。

## 6. 给前端 / 联调方的提示

- H5 / PC 分享页拿 `decision`、`analysts`、`research_depth`、`expires_at` 画图和展示有效期；`decision` 可能为 `{}`，需判空。
- 导出按钮直接使用 `/api/reports/share/{token}/download?format=...`（`<a href download>` 即可，无需带 token 头）。注意 429 提示与微信内置浏览器的下载限制（P4.4 处理引导）。
- 经 Nginx 反向代理时，限流以 token 计数，不依赖客户端 IP，无需透传真实 IP。
