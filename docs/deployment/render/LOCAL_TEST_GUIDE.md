# 本地Docker验证测试指南

在部署到Render之前，建议先在本地测试Docker容器。

## 🧪 本地测试步骤

### 1. 构建Docker镜像

```bash
# 在项目根目录执行
docker build -f Dockerfile.render -t tradingagents-render:test .
```

构建时间约5-10分钟，取决于网络速度。

### 2. 运行容器

```bash
docker run -d \
  --name tradingagents-test \
  -p 8080:80 \
  -e OPENAI_API_KEY=your-openai-key \
  -e TUSHARE_TOKEN=your-tushare-token \
  tradingagents-render:test
```

### 3. 查看启动日志

```bash
# 实时查看日志
docker logs -f tradingagents-test
```

等待所有服务启动完成（约30-60秒）：

```
✓ MongoDB启动成功
✓ Redis启动成功
✓ FastAPI后端启动成功
✓ Nginx启动成功
```

### 4. 测试访问

**健康检查**:
```bash
curl http://localhost:8080/health
# 预期输出: ok
```

**后端API**:
```bash
curl http://localhost:8080/api/health
# 预期输出: {"status":"ok",...}
```

**前端页面**:
- 浏览器访问: http://localhost:8080

### 5. 检查服务状态

```bash
# 进入容器
docker exec -it tradingagents-test bash

# 检查MongoDB
mongosh --eval "db.adminCommand('ping')"

# 检查Redis
redis-cli ping

# 检查Nginx
curl -I http://localhost

# 退出容器
exit
```

### 6. 清理测试环境

```bash
# 停止并删除容器
docker stop tradingagents-test
docker rm tradingagents-test

# 删除镜像（可选）
docker rmi tradingagents-render:test
```

## 🐛 常见问题

### 构建失败

**错误**: `failed to fetch metadata`

**解决**: 检查网络连接，重试构建

### 容器启动失败

**错误**: `MongoDB启动超时`

**解决**: 
```bash
# 查看详细日志
docker logs tradingagents-test

# 增加内存限制（Docker Desktop设置）
# 至少分配2GB内存
```

### 端口冲突

**错误**: `port is already allocated`

**解决**:
```bash
# 使用其他端口
docker run -p 8888:80 ...
```

## 📊 性能测试

### 内存使用监控

```bash
# 查看容器资源使用
docker stats tradingagents-test
```

预期内存使用：
- 空闲状态: ~300-400MB
- 运行分析: ~450-500MB
- Render限制: 512MB

### 压力测试（可选）

```bash
# 测试API响应时间
time curl http://localhost:8080/api/health

# 测试并发请求
for i in {1..10}; do curl http://localhost:8080/health & done
```

## ✅ 验证清单

部署前确认：

- [ ] Docker镜像构建成功
- [ ] 容器启动无错误日志
- [ ] 健康检查端点正常
- [ ] 前端页面可访问
- [ ] 后端API响应正常
- [ ] MongoDB连接正常
- [ ] Redis连接正常
- [ ] 内存使用在限制范围内

全部通过后，即可部署到Render平台！

