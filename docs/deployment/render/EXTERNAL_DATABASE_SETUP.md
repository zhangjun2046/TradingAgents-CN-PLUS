# 外部数据库服务配置指南

方案A：使用MongoDB Atlas和Upstash Redis免费服务

## 📋 准备工作

完成后您将获得：
- ✅ MongoDB Atlas连接URL（512MB免费存储）
- ✅ Upstash Redis连接URL（10K次/天免费）
- ✅ 两个服务都是**永久免费**

预计时间：**10分钟**

---

## 第一步：注册MongoDB Atlas

### 1.1 访问MongoDB Atlas

访问：https://www.mongodb.com/cloud/atlas/register

### 1.2 注册账号

- 使用邮箱注册
- 或使用Google账号快速登录

### 1.3 创建免费集群

1. 登录后点击 **"Build a Database"**
2. 选择 **"M0 Free"** 免费套餐
3. 选择云服务商和区域：
   - **Provider**: AWS
   - **Region**: Singapore (ap-southeast-1) **推荐**
   - 或选择 Hong Kong (ap-east-1)

4. 集群名称：`TradingAgents`（可自定义）

5. 点击 **"Create"**

### 1.4 创建数据库用户

1. 在弹出的安全设置页面：
   - **Username**: `tradingagents`
   - **Password**: 自动生成或自定义（**请记录下来**）
   - 点击 **"Create User"**

### 1.5 设置网络访问

1. 在 "Where would you like to connect from?" 页面
2. 选择 **"Cloud Environment"**
3. 点击 **"Add IP Address"**
4. 输入：`0.0.0.0/0` （允许所有IP访问）
5. 点击 **"Add Entry"**
6. 点击 **"Finish and Close"**

### 1.6 获取连接字符串

1. 点击 **"Connect"** 按钮
2. 选择 **"Connect your application"**
3. Driver选择：**Python**，Version：**3.12 or later**
4. 复制连接字符串，格式如下：

```
mongodb+srv://tradingagents:<password>@tradingagents.xxxxx.mongodb.net/?retryWrites=true&w=majority
```

5. **重要**：将 `<password>` 替换为您的实际密码
6. 在URL末尾添加数据库名：

```
mongodb+srv://tradingagents:YOUR_PASSWORD@tradingagents.xxxxx.mongodb.net/tradingagents?retryWrites=true&w=majority
```

**请保存此连接URL，稍后需要配置到Render！**

---

## 第二步：注册Upstash Redis

### 2.1 访问Upstash

访问：https://upstash.com/

### 2.2 注册账号

- 点击 **"Get Started"**
- 使用邮箱注册或Google账号登录

### 2.3 创建Redis数据库

1. 登录后点击 **"Create Database"**
2. 配置选项：
   - **Name**: `tradingagents-cache`
   - **Type**: **Regional**（选择区域数据库）
   - **Region**: **Asia Pacific (Singapore)** **推荐**
   - **Eviction**: 选择 **"allkeys-lru"**

3. 点击 **"Create"**

### 2.4 获取连接URL

1. 创建成功后，进入数据库详情页
2. 找到 **"Connect"** 部分
3. 选择 **"Redis"** 标签
4. 复制 **连接URL**，格式如下：

```
redis://default:YOUR_PASSWORD@ap-southeast-1-12345.upstash.io:6379
```

或使用TLS版本（更安全，推荐）：

```
rediss://default:YOUR_PASSWORD@ap-southeast-1-12345.upstash.io:6380
```

**请保存此连接URL，稍后需要配置到Render！**

---

## 第三步：配置Render环境变量

### 3.1 返回Render Dashboard

1. 访问：https://dashboard.render.com/
2. 进入您的 **TradingAgents-CN-PLUS** 服务
3. 点击左侧 **"Environment"** 菜单

### 3.2 修改数据库环境变量

找到并修改以下两个变量：

#### MongoDB配置

```
Key: TRADINGAGENTS_MONGODB_URL
Value: mongodb+srv://tradingagents:YOUR_PASSWORD@tradingagents.xxxxx.mongodb.net/tradingagents?retryWrites=true&w=majority
```

（粘贴您在步骤1.6获得的URL）

#### Redis配置

```
Key: TRADINGAGENTS_REDIS_URL
Value: rediss://default:YOUR_PASSWORD@ap-southeast-1-12345.upstash.io:6380
```

（粘贴您在步骤2.4获得的URL）

### 3.3 确认其他必需变量

确保以下变量已配置：

```
TRADINGAGENTS_CACHE_TYPE = redis
API_HOST = 0.0.0.0
API_PORT = 8000
TRADINGAGENTS_LOG_LEVEL = WARNING
```

### 3.4 保存配置

点击 **"Save Changes"**

---

## 第四步：更新Render部署配置

### 4.1 修改Dockerfile路径

1. 在Render服务页面
2. 点击 **"Settings"** 标签
3. 找到 **"Dockerfile Path"**
4. 修改为：`Dockerfile.render.external-db`
5. 点击 **"Save Changes"**

### 4.2 提交代码到GitHub

在本地项目目录执行：

```bash
git add Dockerfile.render.external-db docker-entrypoint.render.external-db.sh
git commit -m "Add external database deployment configuration"
git push origin main
```

### 4.3 触发重新部署

在Render Dashboard：
1. 点击 **"Manual Deploy"**
2. 选择 **"Deploy latest commit"**
3. 等待构建完成（预计5-8分钟）

---

## ✅ 验证部署

### 5.1 检查构建日志

在Render Dashboard查看日志，应该看到：

```
✓ FastAPI后端启动成功
✓ MongoDB连接正常
✓ Redis连接正常
✓ Nginx启动成功
```

### 5.2 访问应用

访问Render提供的URL：
```
https://tradingagents-cn-plus.onrender.com/
```

### 5.3 健康检查

```bash
curl https://tradingagents-cn-plus.onrender.com/health
# 应返回: ok

curl https://tradingagents-cn-plus.onrender.com/api/health
# 应返回: {"status":"ok",...}
```

---

## 🎯 配置总结

### 获得的连接信息

| 服务 | 连接URL | 免费额度 |
|------|---------|---------|
| **MongoDB Atlas** | `mongodb+srv://...` | 512MB存储 |
| **Upstash Redis** | `rediss://...` | 10K次请求/天 |

### 重要说明

✅ **数据持久化**：数据永久保存，容器重启不丢失  
✅ **专业托管**：由专业团队维护，更稳定  
✅ **备份功能**：MongoDB Atlas支持自动备份  
✅ **监控功能**：两个服务都提供性能监控  
✅ **免费永久**：不需要信用卡，永久免费使用  

---

## 🔧 故障排查

### 问题1：MongoDB连接失败

**错误**：`connection timeout` 或 `authentication failed`

**解决**：
1. 检查密码是否正确（URL中的`<password>`已替换）
2. 确认网络白名单包含 `0.0.0.0/0`
3. 检查连接URL格式是否正确
4. 确认数据库名称为 `tradingagents`

### 问题2：Redis连接失败

**错误**：`connection refused`

**解决**：
1. 检查URL是否正确复制
2. 确认使用的是TLS版本（`rediss://`，双s）
3. 检查密码是否包含特殊字符（需要URL编码）

### 问题3：构建仍然超时

**解决**：
1. 确认使用的是 `Dockerfile.render.external-db`
2. 检查前端构建是否正常
3. 查看构建日志定位卡在哪一步

---

## 📞 获取帮助

- MongoDB Atlas文档：https://docs.atlas.mongodb.com/
- Upstash文档：https://docs.upstash.com/redis
- 项目Issues：https://github.com/hsliuping/TradingAgents-CN/issues

---

**配置完成后，您将拥有一个免费、稳定、数据持久化的部署环境！** 🎉

