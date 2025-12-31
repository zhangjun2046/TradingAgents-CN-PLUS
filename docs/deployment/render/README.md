# Render平台部署文件说明

TradingAgents-CN v1.0.0-preview 的Render部署方案

## 📦 文件清单

### 根目录文件

| 文件 | 说明 | 位置 |
|------|------|------|
| `Dockerfile.render` | 单体容器构建文件 | 项目根目录 |
| `docker-entrypoint.render.sh` | 容器启动脚本 | 项目根目录 |
| `render.yaml` | Render平台配置 | 项目根目录 |
| `env.render.example` | 环境变量示例 | 项目根目录 |

### Nginx配置

| 文件 | 说明 | 位置 |
|------|------|------|
| `nginx.render.conf` | Nginx反向代理配置 | `nginx/` |

### 文档

| 文件 | 说明 | 位置 |
|------|------|------|
| `RENDER_DEPLOYMENT_GUIDE.md` | 部署操作指南 | `docs/deployment/render/` |
| `LOCAL_TEST_GUIDE.md` | 本地测试指南 | `docs/deployment/render/` |
| `README.md` | 本文件 | `docs/deployment/render/` |

## 🚀 快速开始

### 三步部署到Render

1. **提交代码到GitHub**
   ```bash
   git add .
   git commit -m "Add Render deployment"
   git push
   ```

2. **连接Render平台**
   - 访问 https://dashboard.render.com/
   - 选择 New + → Blueprint
   - 选择您的GitHub仓库

3. **配置环境变量**
   - 设置 `OPENAI_API_KEY`
   - 设置 `TUSHARE_TOKEN`（推荐）
   - 点击 Apply 开始部署

### 本地测试（可选）

```bash
# 构建镜像
docker build -f Dockerfile.render -t tradingagents-render:test .

# 运行容器
docker run -d -p 8080:80 \
  -e OPENAI_API_KEY=your-key \
  tradingagents-render:test

# 访问测试
curl http://localhost:8080/health
```

详细测试步骤请参考 [LOCAL_TEST_GUIDE.md](./LOCAL_TEST_GUIDE.md)

## 📋 部署架构

```
Render平台
  └─ Docker容器 (512MB)
      ├─ Nginx (80端口) - 前端 + 反向代理
      ├─ FastAPI (8000端口) - 后端API
      ├─ MongoDB (27017端口) - 数据库
      └─ Redis (6379端口) - 缓存
```

## ⚠️ 注意事项

### 免费套餐限制
- 512MB RAM（所有服务共享）
- 15分钟无活动自动休眠
- 容器重启数据丢失
- 仅适合测试和演示

### 生产环境建议
- 升级到付费套餐（$7/月起）
- 使用外部托管数据库
- 配置自动唤醒服务
- 定期备份数据

## 📚 详细文档

- [完整部署指南](./RENDER_DEPLOYMENT_GUIDE.md) - 详细的部署步骤和配置说明
- [本地测试指南](./LOCAL_TEST_GUIDE.md) - 部署前的本地验证测试
- [环境变量配置](../../../env.render.example) - 所有可配置的环境变量

## 🔗 相关链接

- Render官方文档: https://render.com/docs
- Render Dashboard: https://dashboard.render.com/
- 项目GitHub: https://github.com/hsliuping/TradingAgents-CN

## 📞 技术支持

遇到问题？

- 提交Issue: https://github.com/hsliuping/TradingAgents-CN/issues
- 微信公众号: TradingAgents-CN
- 邮箱: hsliup@163.com

