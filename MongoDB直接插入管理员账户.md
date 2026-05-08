# MongoDB Atlas 直接插入管理员账户

最简单快速的方法：直接在 MongoDB Atlas Web 界面插入用户数据。

---

## 🚀 操作步骤（2 分钟完成）

### 第 1 步：打开 MongoDB Atlas

1. 访问 https://cloud.mongodb.com/v2/69030b348fc232478a43141b#/overview
2. 登录您的账户
3. 点击左侧菜单 **"Browse Collections"**（浏览集合）

### 第 2 步：选择数据库和集合

1. 在左侧选择您的数据库：`tradingagents`
2. 找到 `users` 集合
   - 如果不存在 `users` 集合，点击 **"Create Collection"** 创建一个名为 `users` 的集合

### 第 3 步：插入管理员用户

1. 点击 **"INSERT DOCUMENT"** 按钮
2. 切换到 **"JSON"** 视图（右上角）
3. **复制以下 JSON 代码**，粘贴到编辑器中：

```json
{
  "username": "admin",
  "email": "admin@tradingagents.cn",
  "hashed_password": "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9",
  "is_active": true,
  "is_verified": true,
  "is_admin": true,
  "created_at": {"$date": "2026-01-10T00:00:00.000Z"},
  "updated_at": {"$date": "2026-01-10T00:00:00.000Z"},
  "last_login": null,
  "preferences": {
    "default_market": "A股",
    "default_depth": "深度",
    "ui_theme": "light",
    "language": "zh-CN",
    "notifications_enabled": true,
    "email_notifications": false
  },
  "daily_quota": 10000,
  "concurrent_limit": 10,
  "total_analyses": 0,
  "successful_analyses": 0,
  "failed_analyses": 0,
  "favorite_stocks": []
}
```

4. 点击 **"Insert"** 按钮

### 第 4 步：验证插入成功

在 `users` 集合中应该能看到刚插入的管理员用户文档。

### 第 5 步：登录系统

1. 访问 https://tradingagents-cn-plus.onrender.com/login
2. 使用以下凭证登录：
   - **用户名**: `admin`
   - **密码**: `admin123`
3. ✅ 登录成功！

---

## 📋 字段说明

| 字段 | 值 | 说明 |
|-----|-----|-----|
| `username` | `admin` | 登录用户名 |
| `hashed_password` | `240be5...` | admin123 的 SHA-256 哈希值 |
| `is_admin` | `true` | 管理员权限 |
| `daily_quota` | `10000` | 每日分析配额 |
| `concurrent_limit` | `10` | 并发限制 |

---

## ⚠️ 重要提醒

1. **密码哈希值不要修改**
   - `240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9` 对应密码 `admin123`
   
2. **登录后立即修改密码**
   - 默认密码仅用于首次登录
   
3. **时间戳可以修改**
   - 将日期改为当前日期（格式保持不变）

---

## 🎯 常见问题

### Q: 找不到 `users` 集合？

**A**: 首次使用数据库时集合不存在，需要创建：
1. 在数据库 `tradingagents` 下
2. 点击 **"Create Collection"**
3. 集合名称输入：`users`
4. 点击 **"Create"**

### Q: 密码哈希值是什么？

**A**: 
- 系统使用 SHA-256 算法加密密码
- `admin123` → `240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9`
- **不要修改这个哈希值**，否则密码将不正确

### Q: 可以修改用户名和密码吗？

**A**: 可以！

**修改用户名**：
- 直接修改 JSON 中的 `"username": "admin"` 为您想要的用户名
- 例如：`"username": "myadmin"`

**修改密码**：
- 需要先计算新密码的 SHA-256 哈希值
- 在线工具：https://emn178.github.io/online-tools/sha256.html
- 输入您的密码，复制生成的哈希值
- 替换 JSON 中的 `"hashed_password"` 值

### Q: 已经插入了，但登录失败？

**检查项**：
1. 用户名和密码输入是否正确
2. `hashed_password` 字段值是否正确
3. `is_active` 是否为 `true`
4. `is_admin` 是否为 `true`

---

## 🔧 自定义密码哈希生成

如果您想使用自己的密码，可以使用以下方法生成哈希值：

### 方法 1：在线工具
访问 https://emn178.github.io/online-tools/sha256.html
- 输入您的密码
- 复制生成的 SHA-256 哈希值

### 方法 2：Python 命令
```bash
python3 -c "import hashlib; print(hashlib.sha256('您的密码'.encode()).hexdigest())"
```

### 方法 3：Node.js 命令
```bash
node -e "console.log(require('crypto').createHash('sha256').update('您的密码').digest('hex'))"
```

---

## ✅ 完成！

现在您可以：
1. ✅ 使用 `admin` / `admin123` 登录
2. ✅ 修改默认密码
3. ✅ 配置系统并开始使用

---

**这个方法只需 2 分钟，无需任何脚本！** 🎉

