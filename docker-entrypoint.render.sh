#!/bin/bash
# Render平台容器启动脚本
# TradingAgents-CN v1.0.0-preview
# 按序启动MongoDB、Redis、FastAPI后端、Nginx前端

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 错误处理函数
handle_error() {
    log_error "启动失败！请查看日志排查问题。"
    exit 1
}

trap handle_error ERR

# ============================================
# 1. 初始化环境
# ============================================
log_info "=========================================="
log_info "TradingAgents-CN Render部署启动脚本"
log_info "版本: v1.0.0-preview"
log_info "=========================================="

# 确保必需的目录存在
log_info "创建必需的目录..."
mkdir -p /app/logs /app/data /app/config
mkdir -p /data/db /data/redis
mkdir -p /var/log/mongodb /var/log/redis /var/log/nginx
mkdir -p /run/mongodb /var/run

# 设置目录权限
chmod -R 755 /data/db /data/redis
chmod -R 755 /var/log/mongodb /var/log/redis

log_success "目录初始化完成"

# ============================================
# 2. 启动MongoDB
# ============================================
log_info "启动MongoDB服务..."

# 检查MongoDB配置文件
if [ ! -f /etc/mongodb/mongod.conf ]; then
    log_error "MongoDB配置文件不存在！"
    exit 1
fi

# 启动MongoDB（后台运行）
mongod --config /etc/mongodb/mongod.conf &
MONGODB_PID=$!

log_info "MongoDB进程ID: $MONGODB_PID"

# 等待MongoDB启动（最多30秒）
log_info "等待MongoDB启动..."
for i in {1..30}; do
    if mongosh --eval "db.adminCommand('ping')" --quiet > /dev/null 2>&1; then
        log_success "MongoDB启动成功"
        break
    fi
    if [ $i -eq 30 ]; then
        log_error "MongoDB启动超时！"
        exit 1
    fi
    sleep 1
done

# ============================================
# 3. 初始化MongoDB数据库
# ============================================
log_info "初始化MongoDB数据库..."

# 创建管理员用户
mongosh admin --eval "
try {
    db.createUser({
        user: 'admin',
        pwd: 'tradingagents123',
        roles: [{role: 'root', db: 'admin'}]
    });
    print('✓ 管理员用户创建成功');
} catch (e) {
    print('⚠ 管理员用户可能已存在');
}
" || log_warning "管理员用户创建失败（可能已存在）"

# 执行初始化脚本
if [ -f /app/scripts/mongo-init.js ]; then
    log_info "执行MongoDB初始化脚本..."
    mongosh < /app/scripts/mongo-init.js || log_warning "MongoDB初始化脚本执行警告"
    log_success "MongoDB数据库初始化完成"
else
    log_warning "MongoDB初始化脚本不存在，跳过数据库初始化"
fi

# ============================================
# 4. 启动Redis
# ============================================
log_info "启动Redis服务..."

# 检查Redis配置文件
if [ ! -f /etc/redis/redis.conf ]; then
    log_error "Redis配置文件不存在！"
    exit 1
fi

# 启动Redis（后台运行）
redis-server /etc/redis/redis.conf &
REDIS_PID=$!

log_info "Redis进程ID: $REDIS_PID"

# 等待Redis启动（最多10秒）
log_info "等待Redis启动..."
for i in {1..10}; do
    if redis-cli ping > /dev/null 2>&1; then
        log_success "Redis启动成功"
        break
    fi
    if [ $i -eq 10 ]; then
        log_error "Redis启动超时！"
        exit 1
    fi
    sleep 1
done

# ============================================
# 5. 配置环境变量
# ============================================
log_info "配置环境变量..."

# 设置默认环境变量（如果未设置）
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1
export DOCKER_CONTAINER=true
export TZ=Asia/Shanghai

# 数据库连接配置（localhost内部连接）
export TRADINGAGENTS_MONGODB_URL=${TRADINGAGENTS_MONGODB_URL:-"mongodb://localhost:27017/tradingagents"}
export TRADINGAGENTS_REDIS_URL=${TRADINGAGENTS_REDIS_URL:-"redis://localhost:6379"}
export TRADINGAGENTS_CACHE_TYPE=${TRADINGAGENTS_CACHE_TYPE:-"redis"}

# API配置
export API_HOST=${API_HOST:-"0.0.0.0"}
export API_PORT=${API_PORT:-"8000"}

# 日志配置
export TRADINGAGENTS_LOG_LEVEL=${TRADINGAGENTS_LOG_LEVEL:-"WARNING"}
export TRADINGAGENTS_LOG_DIR=${TRADINGAGENTS_LOG_DIR:-"/app/logs"}
export TRADINGAGENTS_LOG_FILE=${TRADINGAGENTS_LOG_FILE:-"/app/logs/tradingagents.log"}

# CORS配置（允许Nginx反向代理）
export CORS_ORIGINS=${CORS_ORIGINS:-"*"}

log_success "环境变量配置完成"

# 打印关键配置
log_info "关键配置信息："
log_info "  - MongoDB: $TRADINGAGENTS_MONGODB_URL"
log_info "  - Redis: $TRADINGAGENTS_REDIS_URL"
log_info "  - API端口: $API_PORT"
log_info "  - 日志级别: $TRADINGAGENTS_LOG_LEVEL"

# ============================================
# 6. 启动FastAPI后端
# ============================================
log_info "启动FastAPI后端服务..."

cd /app

# 启动FastAPI（后台运行，单worker节省内存）
python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level warning \
    --no-access-log &

BACKEND_PID=$!
log_info "FastAPI进程ID: $BACKEND_PID"

# 等待后端启动（最多60秒）
log_info "等待FastAPI后端启动..."
for i in {1..60}; do
    if curl -f http://localhost:8000/api/health > /dev/null 2>&1; then
        log_success "FastAPI后端启动成功"
        break
    fi
    if [ $i -eq 60 ]; then
        log_error "FastAPI后端启动超时！"
        exit 1
    fi
    sleep 1
done

# ============================================
# 7. 启动Nginx
# ============================================
log_info "启动Nginx服务..."

# 测试Nginx配置
nginx -t || {
    log_error "Nginx配置测试失败！"
    exit 1
}

# 启动Nginx（前台运行）
log_success "Nginx配置测试通过"
log_info "启动Nginx（前台模式）..."

# ============================================
# 8. 启动完成
# ============================================
log_success "=========================================="
log_success "所有服务启动成功！"
log_success "=========================================="
log_info "服务状态："
log_info "  ✓ MongoDB    - 运行中 (PID: $MONGODB_PID)"
log_info "  ✓ Redis      - 运行中 (PID: $REDIS_PID)"
log_info "  ✓ FastAPI    - 运行中 (PID: $BACKEND_PID)"
log_info "  ✓ Nginx      - 准备启动"
log_success "=========================================="
log_info "访问地址: http://localhost"
log_info "健康检查: http://localhost/health"
log_info "后端API: http://localhost/api"
log_success "=========================================="

# 启动Nginx（前台运行，保持容器运行）
exec nginx -g 'daemon off;'

