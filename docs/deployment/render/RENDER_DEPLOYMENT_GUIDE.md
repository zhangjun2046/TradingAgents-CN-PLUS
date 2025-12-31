# Render平台部署指南

TradingAgents-CN v1.0.0-preview - 单体Docker部署方案

## 📋 快速开始

### 前置要求

- ✅ GitHub账号
- ✅ Render账号（通过GitHub登录）
- ✅ OpenAI API密钥
- ✅ 代码已推送到GitHub仓库

### 部署步骤

#### 1. 准备GitHub仓库

确认以下文件已提交到GitHub：

```bash
git add Dockerfile.render docker-entrypoint.render.sh render.yaml nginx/nginx.render.conf env.render.example
git commit -m "Add Render deployment configuration"
git push origin main
```

#### 2. 连接Render平台

1. 访问 https://dashboard.render.com/
2. 点击 **New +** → **Blueprint**
3. 选择您的GitHub仓库
4. Render会自动识别 `render.yaml` 配置文件

#### 3. 配置环境变量

在Render Dashboard中设置以下**必需**环境变量：

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `OPENAI_API_KEY` | OpenAI API密钥 | `sk-xxx...` |
| `TUSHARE_TOKEN` | Tushare数据源令牌（推荐） | `xxx...` |

其他环境变量已在 `render.yaml` 中自动配置。

#### 4. 启动部署

1. 点击 **Apply** 开始部署
2. 等待构建完成（约10-15分钟）
3. 构建成功后，访问Render提供的URL

#### 5. 验证部署

访问以下端点验证：

- **前端页面**: `https://your-app.onrender.com/`
- **健康检查**: `https://your-app.onrender.com/health`
- **后端API**: `https://your-app.onrender.com/api/health`

## ⚠️ 重要说明

### 免费套餐限制

- **内存**: 512MB RAM（所有服务共享）
- **自动休眠**: 15分钟无活动后休眠
- **冷启动**: 首次访问需等待30-60秒唤醒
- **数据丢失**: 容器重启后数据全部丢失

### 数据持久化警告

⚠️ **免费套餐不支持持久化存储！**

- 容器重启 = 数据清空
- 每次休眠唤醒 = 数据清空
- 请定期备份重要数据

### 性能预期

- 单用户使用正常
- 分析任务较慢（内存限制）
- 不支持高并发
- 仅适合测试和演示

## 🔧 故障排查

### 构建失败

**问题**: 构建超时（15分钟）

**解决**:
- 检查网络连接
- 重新触发构建
- 查看构建日志定位问题

### 服务无法访问

**问题**: 访问URL返回错误

**解决**:
1. 检查健康检查是否通过：`/health`
2. 查看Render日志：Dashboard → Logs
3. 确认环境变量是否正确设置
4. 重启服务：Dashboard → Manual Deploy → Deploy latest commit

### 容器内存不足

**问题**: 服务频繁重启

**解决**:
- 升级到付费套餐（$7/月，1GB RAM）
- 使用外部数据库（MongoDB Atlas + Upstash Redis）

## 🚀 升级建议

### 从免费套餐升级

**推荐配置**（生产环境）：

1. **Web Service**: Starter套餐（$7/月，1GB RAM）
2. **MongoDB**: MongoDB Atlas免费套餐（512MB存储）
3. **Redis**: Upstash Redis免费套餐（10K次/天）

### 外部数据库配置

修改 `render.yaml` 中的环境变量：

```yaml
- key: TRADINGAGENTS_MONGODB_URL
  value: mongodb+srv://user:pass@cluster.mongodb.net/tradingagents

- key: TRADINGAGENTS_REDIS_URL
  value: redis://default:xxx@region.upstash.io:6379
```

## 📞 获取帮助

- **项目Issues**: https://github.com/hsliuping/TradingAgents-CN/issues
- **微信公众号**: TradingAgents-CN
- **邮箱**: hsliup@163.com

## 📚 相关文档

- [Render官方文档](https://render.com/docs)
- [Docker部署指南](../docker/DOCKER_DEPLOYMENT_v1.0.0.md)
- [环境变量配置](../../env.render.example)

