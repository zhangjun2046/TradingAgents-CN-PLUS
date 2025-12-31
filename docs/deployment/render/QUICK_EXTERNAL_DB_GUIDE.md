# 快速配置指南（外部数据库）

10分钟完成配置 - 方案A

## 🚀 三个服务，三个URL

### 1️⃣ MongoDB Atlas（3分钟）

**访问**：https://www.mongodb.com/cloud/atlas/register

**操作**：
1. 注册/登录
2. 创建M0免费集群（选择Singapore区域）
3. 创建用户：`tradingagents` / 自定义密码
4. 网络白名单：添加 `0.0.0.0/0`
5. 获取连接URL

**得到URL格式**：
```
mongodb+srv://tradingagents:密码@cluster.mongodb.net/tradingagents?retryWrites=true&w=majority
```

---

### 2️⃣ Upstash Redis（2分钟）

**访问**：https://upstash.com/

**操作**：
1. 注册/登录
2. 创建数据库（选择Singapore区域）
3. 复制连接URL

**得到URL格式**：
```
rediss://default:密码@region.upstash.io:6380
```

---

### 3️⃣ 配置Render（5分钟）

#### 步骤1：修改环境变量

在Render Dashboard → Environment，设置：

```
TRADINGAGENTS_MONGODB_URL = (粘贴MongoDB URL)
TRADINGAGENTS_REDIS_URL = (粘贴Redis URL)
```

#### 步骤2：修改Dockerfile路径

Settings → Dockerfile Path 改为：
```
Dockerfile.render.external-db
```

#### 步骤3：提交代码

```bash
git add .
git commit -m "Use external databases"
git push origin main
```

#### 步骤4：重新部署

Render Dashboard → Manual Deploy → Deploy latest commit

---

## ✅ 完成检查

- [ ] MongoDB URL已配置
- [ ] Redis URL已配置
- [ ] Dockerfile路径已修改为 `Dockerfile.render.external-db`
- [ ] 代码已推送到GitHub
- [ ] 已触发重新部署
- [ ] 构建成功（约5-8分钟）
- [ ] 可以访问应用

---

## 💡 重要提示

### 连接URL示例

**MongoDB（注意替换密码和集群地址）**：
```
mongodb+srv://tradingagents:YOUR_PASSWORD@cluster0.abc123.mongodb.net/tradingagents?retryWrites=true&w=majority
```

**Redis（注意使用TLS版本，双s）**：
```
rediss://default:YOUR_PASSWORD@ap-southeast-1-12345.upstash.io:6380
```

### 常见错误

❌ **错误1**：MongoDB URL忘记替换 `<password>`  
✅ **解决**：确保替换为实际密码

❌ **错误2**：Redis使用 `redis://`（单s）  
✅ **解决**：改为 `rediss://`（双s，TLS版本）

❌ **错误3**：Dockerfile路径没改  
✅ **解决**：确认使用 `Dockerfile.render.external-db`

---

## 🎯 预期结果

### 构建时间
- 以前：10-15分钟（可能超时）
- 现在：**5-8分钟**

### 内存使用
- 以前：~500MB（接近限制）
- 现在：**~150MB**（轻松运行）

### 数据持久化
- 以前：容器重启数据丢失
- 现在：**数据永久保存**

---

**配置完成！享受免费且稳定的部署环境！** 🎉

