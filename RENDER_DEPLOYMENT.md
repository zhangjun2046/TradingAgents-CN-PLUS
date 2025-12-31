# Render平台快速部署指南

TradingAgents-CN v1.0.0-preview

## 🎯 一键部署到Render

### 步骤1：准备代码

```bash
# 提交所有部署文件到GitHub
git add Dockerfile.render docker-entrypoint.render.sh render.yaml nginx/nginx.render.conf env.render.example
git commit -m "Add Render deployment configuration"
git push origin main
```

### 步骤2：部署到Render

1. 访问 [Render Dashboard](https://dashboard.render.com/)
2. 点击 **New +** → **Blueprint**
3. 连接您的GitHub仓库
4. Render自动识别 `render.yaml`

### 步骤3：配置环境变量

在Render Dashboard设置：

- **必需**：`OPENAI_API_KEY` = `sk-your-key`
- **推荐**：`TUSHARE_TOKEN` = `your-token`

### 步骤4：启动部署

点击 **Apply** → 等待10-15分钟 → 完成！

## 📦 已创建的文件

| 文件 | 说明 |
|------|------|
| `Dockerfile.render` | 单体容器构建文件（前端+后端+MongoDB+Redis） |
| `docker-entrypoint.render.sh` | 容器启动脚本（自动启动所有服务） |
| `render.yaml` | Render平台配置（自动部署） |
| `nginx/nginx.render.conf` | Nginx反向代理配置 |
| `env.render.example` | 环境变量配置示例 |

## 🧪 本地测试（可选）

```bash
# 构建测试
docker build -f Dockerfile.render -t tradingagents-test .

# 运行测试
docker run -d -p 8080:80 \
  -e OPENAI_API_KEY=sk-your-key \
  tradingagents-test

# 访问测试
curl http://localhost:8080/health
open http://localhost:8080
```

## ⚠️ 重要提醒

**免费套餐限制**：
- 512MB RAM（所有服务共享）
- 15分钟无活动自动休眠
- 容器重启数据丢失
- 仅适合测试演示

**生产部署建议**：
- 升级付费套餐（$7/月）
- 使用外部数据库（MongoDB Atlas + Upstash Redis）

## 📚 详细文档

- [完整部署指南](docs/deployment/render/RENDER_DEPLOYMENT_GUIDE.md)
- [本地测试指南](docs/deployment/render/LOCAL_TEST_GUIDE.md)
- [文件说明](docs/deployment/render/README.md)

## ✅ 部署验证

部署完成后访问：

- 前端页面：`https://your-app.onrender.com/`
- 健康检查：`https://your-app.onrender.com/health`
- 后端API：`https://your-app.onrender.com/api/health`

## 🆘 问题排查

**构建失败？**
- 检查GitHub仓库权限
- 查看构建日志
- 确认文件路径正确

**无法访问？**
- 等待冷启动（30-60秒）
- 检查健康检查状态
- 查看Render日志

**内存不足？**
- 升级付费套餐
- 使用外部数据库

## 📞 获取帮助

- GitHub Issues: https://github.com/hsliuping/TradingAgents-CN/issues
- 微信公众号：TradingAgents-CN
- 邮箱：hsliup@163.com

---

**祝您部署顺利！🚀**

