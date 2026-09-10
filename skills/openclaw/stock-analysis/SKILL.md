---
name: stock-analysis
description: 用 TradingAgents-CN 发起单股分析。对话里只收股票代码和例外参数，完成后由飞书推送摘要和手机报告链接。
---

# TradingAgents-CN 股票分析

把本文件复制到 OpenClaw 的 skills 目录后启用。本技能**提交任务后立刻结束**，不要轮询进度；结果走飞书。

## 默认参数（不要让用户再填一遍）

除非用户明确改口，一律使用：

- 研究深度：`标准`（3 级）
- 分析师：`market`、`fundamentals`
- 快模型：`qwen-turbo`
- 深模型：`qwen-max`
- 市场：按代码推断（6 位 A 股 → `A股`；含 `.HK` → `港股`；否则 `美股`）
- 语言：`zh-CN`

## 只从对话里取这些

- **必填**：股票代码或名称能对应的代码（如 `000001`、`600519`、`1810.HK`）
- **例外**（可无）：
  - 「今天用 5 级 / 全面」→ `research_depth=全面`
  - 「4 级 / 深度」→ `深度`；「2 级 / 基础」→ `基础`；「1 级 / 快速」→ `快速`
  - 「加上新闻」→ `selected_analysts` 增加 `news`
  - 「加上社媒」→ 增加 `social`

## 环境变量

- `PUBLIC_APP_URL`：站点根地址，默认 `http://118.144.76.8:3000`（不要末尾斜杠）
- `TA_API_TOKEN`：登录后的 Bearer。没有则先登录：

```http
POST {PUBLIC_APP_URL}/api/auth/login
Content-Type: application/json

{"username":"<账号>","password":"<密码>"}
```

从 `data.access_token` 取出，本轮会话内复用。

## 提交分析（唯一必要请求）

```http
POST {PUBLIC_APP_URL}/api/analysis/single
Authorization: Bearer {TA_API_TOKEN}
Content-Type: application/json

{
  "symbol": "000001",
  "parameters": {
    "market_type": "A股",
    "research_depth": "标准",
    "selected_analysts": ["market", "fundamentals"],
    "include_sentiment": true,
    "include_risk": true,
    "language": "zh-CN",
    "quick_analysis_model": "qwen-turbo",
    "deep_analysis_model": "qwen-max"
  }
}
```

成功会返回 `data.task_id`。**不要**再请求 `/status` 或 `/result`。

## 对用户说的话

提交成功后只回复类似：

> 已提交 000001 的标准分析（任务 `<task_id>`）。完成后飞书会推结论摘要和手机阅读链接，无需在这边等待。

提交失败则复述接口错误，不要假装已排队。

## 禁止事项

- 不要在对话里展开完整研报
- 不要为了等结果而保活、轮询或开长任务
- 不要把密码、Webhook、完整 JWT 回显给用户
