# 后端认证 / 短信 / 权限交接（A 线 P1.1～P1.4）

给 B 线（P1.6、P3.3）和 A 线后续（P2、P3.2）用。合入 `dev/h5-1.0` 后以该分支为准。

统一响应：`{ "success": true, "data": {}, "message": "ok" }`。业务错误多为 HTTP 状态 + `detail: { "code", "message" }`。`require_admin` 的 403 为 `detail: "FORBIDDEN"`（字符串，不是对象）。

JWT 不变：`sub = username`。手机号用户注册时 `username = phone`。

---

## 1. 公开接口（无需登录）

| 方法 | 路径 | 入参 | `data` |
|------|------|------|--------|
| GET | `/api/auth/captcha` | — | `{ captcha_id, image_base64 }` PNG Base64 |
| POST | `/api/auth/sms/send` | `{ phone, scene, platform, captcha_id, captcha_code }` | 成功即可再发倒计时信息（含冷却秒） |
| POST | `/api/auth/register` | `{ phone, code, password, agreed }` | token 包（见下） |
| POST | `/api/auth/login` | `{ username, password }` | 兼容：`username` 可以是用户名或 11 位手机号 |
| POST | `/api/auth/login/sms` | `{ phone, code }` | token 包 |
| POST | `/api/auth/password/reset-by-sms` | `{ phone, code, new_password }` | `{}` |
| POST | `/api/auth/refresh` | `{ refresh_token }` | 新 access_token |
| POST | `/api/auth/logout` | 登录可选 | — |

`scene`：`register` / `login` / `reset`。`platform`：`h5` / `pc`。

注册 / 验证码登录返回的 token 包：

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "expires_in": 3600,
  "user": {
    "id": "...",
    "username": "13800138000",
    "email": null,
    "name": "13800138000",
    "is_admin": false,
    "phone": "138****8000"
  }
}
```

密码登录仍返回原有 `LoginResponse` 形态（`access_token` / `user` 等）。`GET /api/auth/me` 的 `phone` 为脱敏。

---

## 2. 发短信顺序与 Mock

`POST /api/auth/sms/send` 任一步失败即中止、不发短信：

1. `platform` 必须是 `h5` 或 `pc`，否则 `PLATFORM_INVALID`
2. 核销图形验证码（忽略大小写，一次性）。Mock **不豁免** captcha
3. 冷却三元组 `(platform, scene, phone)`，60 秒；H5 / PC、不同 scene 互不影响 → `SMS_TOO_FREQUENT`
4. 日上限按手机号（不按端拆）→ `SMS_DAILY_LIMIT`
5. IP 限流 → `IP_RATE_LIMITED`
6. `scene=register` 且手机号已注册 → `PHONE_REGISTERED`（captcha 已消耗，前端须刷新图形码）
7. `scene=login` / `reset` 且未注册：接口仍返回成功但不发送（防枚举）

开发默认 `SMS_PROVIDER=mock`，固定码 **`123456`**（`SMS_MOCK_CODE`）。生产不要用 mock。

图形验证码：SpecCaptcha 130×48、4 位；Redis `captcha:{id}` 存答案 SHA256，TTL 300s。

---

## 3. 登录后接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/auth/me` | 含脱敏 `phone` |
| POST | `/api/auth/change-password` | `{ old_password, new_password }` |
| GET | `/api/config/public/models` | 普通用户可选模型（P1.4） |

`GET /api/config/settings`、`GET /api/config/llm`、`GET /api/config/models` 现为**管理员**接口，H5 表单不要再调它们。

---

## 4. 公开模型接口（B 的 P3.3）

`GET /api/config/public/models`  
鉴权：需要登录，**不需要**管理员。

```json
{
  "success": true,
  "data": {
    "default_quick_model": "qwen-plus",
    "default_deep_model": "qwen-plus",
    "models": [
      {
        "name": "qwen-plus",
        "display_name": "Qwen Plus",
        "provider": "dashscope",
        "capability_level": 3,
        "roles": ["both"]
      }
    ]
  },
  "message": "ok"
}
```

白名单字段只有以上项，**不含** `api_key` / `api_base` / secret。未合入前 B 可用写死列表占位。

---

## 5. `require_admin`（B 的 P1.6）

```python
from fastapi import Depends
from app.core.deps import require_admin

# 整路由
router = APIRouter(..., dependencies=[Depends(require_admin)])

# 单接口（分析任务全量 / 僵尸任务请在 P1.6 改 analysis.py）
@router.get("/tasks/all")
async def list_all(user: dict = Depends(require_admin)):
    ...
```

普通用户 → HTTP 403，`detail == "FORBIDDEN"`。未登录仍是 401。

P1.4 已套用（路由级）：`config`、`database`、`logs`、`operation_logs`、`system_config`（含 `/config/validate`）、`scheduler`、`sync`、`multi_source_sync`、`multi_period_sync`、`stock_sync`、`tushare_init` / `akshare_init` / `baostock_init`、`usage_statistics`。

**未改** `app/routers/analysis.py`。`GET /api/analysis/tasks/all` 与僵尸任务仍按原逻辑，由 B 在 P1.6 换成 `require_admin`。

---

## 6. 错误码

| code | HTTP | 何时 |
|------|------|------|
| `PLATFORM_INVALID` | 400 | platform 非法 |
| `CAPTCHA_INVALID` | 400 | 图形码错误或未带 |
| `CAPTCHA_EXPIRED` | 400 | 图形码不存在或过期 |
| `SMS_TOO_FREQUENT` | 429 | 同三元组 60s 内重发 |
| `SMS_DAILY_LIMIT` | 429 | 该手机号当日达上限 |
| `IP_RATE_LIMITED` | 429 | IP 限流 |
| `SMS_CODE_INVALID` | 400 | 短信码错/过期；登录或重置时未注册也统一此码 |
| `PHONE_REGISTERED` | 409 | 注册或发注册短信时号已占用 |
| `TERMS_NOT_AGREED` | 400 | `agreed` 不为 true |
| `PASSWORD_INVALID` | 400 | 密码长度不是 6～64；此时**不消耗**短信码 |
| `FORBIDDEN` | 403 | 非管理员打管理接口（`detail` 为字符串） |

注册：先校验 `agreed`、密码，再核销短信码。

---

## 7. 手机号索引迁移（运维）

`scripts/migrations/fix_users_email_index.py`：email 改为部分唯一（仅非空）；`phone` 稀疏唯一。应用启动 `ensure_indexes` 也会尝试建同样索引；若同键已有别名则跳过。

老用户无 `phone` 时用用户名+密码登录仍可用。

---

## 8. 环境变量（短信 / 图形码）

| 变量 | 默认 | 说明 |
|------|------|------|
| `SMS_PROVIDER` | `mock` | `mock` / `tencent` |
| `SMS_MOCK_CODE` | `123456` | 仅 mock |
| `SMS_SECRET_ID` / `SMS_SECRET_KEY` / `SMS_SDK_APP_ID` | 空 | 腾讯云 |
| `SMS_SIGN_NAME` / `SMS_TEMPLATE_ID` | 空 | 审核通过后填 |
| `SMS_REGION` | `ap-guangzhou` | |
| `SMS_CODE_TTL_SECONDS` | 300 | |
| `SMS_RESEND_INTERVAL_SECONDS` | 60 | 冷却 |
| `SMS_DAILY_LIMIT_PER_PHONE` | 10 | |
| `SMS_HOURLY_LIMIT_PER_IP` | 20 | |
| `CAPTCHA_TTL_SECONDS` | 300 | |
| `CAPTCHA_LENGTH` | 4 | |

勿把真实密钥提交进 Git。
