#!/bin/bash
# Render平台容器启动脚本（简化版 - 外部数据库）
# TradingAgents-CN v1.0.0-preview
# 仅启动FastAPI后端和Nginx前端，数据库使用外部服务

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
log_info "TradingAgents-CN Render部署启动（外部数据库）"
log_info "版本: v1.0.0-preview"
log_info "=========================================="

# 确保必需的目录存在
log_info "创建必需的目录..."
mkdir -p /app/logs /app/data /app/config
mkdir -p /var/log/nginx

log_success "目录初始化完成"

# ============================================
# 2. 配置环境变量
# ============================================
log_info "配置环境变量..."

# 设置默认环境变量（如果未设置）
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1
export DOCKER_CONTAINER=true
export TZ=Asia/Shanghai

# 验证必需的环境变量
if [ -z "$TRADINGAGENTS_MONGODB_URL" ]; then
    log_error "错误：未设置 TRADINGAGENTS_MONGODB_URL 环境变量"
    log_error "请在Render Dashboard中配置MongoDB连接URL"
    exit 1
fi

if [ -z "$TRADINGAGENTS_REDIS_URL" ]; then
    log_error "错误：未设置 TRADINGAGENTS_REDIS_URL 环境变量"
    log_error "请在Render Dashboard中配置Redis连接URL"
    exit 1
fi

# API配置
export API_HOST=${API_HOST:-"0.0.0.0"}
export API_PORT=${API_PORT:-"8000"}

# 日志配置
export TRADINGAGENTS_LOG_LEVEL=${TRADINGAGENTS_LOG_LEVEL:-"WARNING"}
export TRADINGAGENTS_LOG_DIR=${TRADINGAGENTS_LOG_DIR:-"/app/logs"}
export TRADINGAGENTS_LOG_FILE=${TRADINGAGENTS_LOG_FILE:-"/app/logs/tradingagents.log"}

# CORS配置（允许Nginx反向代理）
export CORS_ORIGINS=${CORS_ORIGINS:-"*"}

# 缓存类型
export TRADINGAGENTS_CACHE_TYPE=${TRADINGAGENTS_CACHE_TYPE:-"redis"}

log_success "环境变量配置完成"

# 打印关键配置（隐藏敏感信息）
log_info "关键配置信息："
log_info "  - MongoDB: ${TRADINGAGENTS_MONGODB_URL%%@*}@***"
log_info "  - Redis: ${TRADINGAGENTS_REDIS_URL%%@*}@***"
log_info "  - API端口: $API_PORT"
log_info "  - 日志级别: $TRADINGAGENTS_LOG_LEVEL"

# ============================================
# 3. 测试数据库连接（可选）
# ============================================
log_info "验证外部服务连接..."

# 简单测试（仅记录，不阻塞启动）
if command -v mongosh &> /dev/null; then
    log_info "测试MongoDB连接..."
    if mongosh "$TRADINGAGENTS_MONGODB_URL" --eval "db.adminCommand('ping')" --quiet > /dev/null 2>&1; then
        log_success "MongoDB连接正常"
    else
        log_warning "MongoDB连接测试失败（将在应用启动时重试）"
    fi
else
    log_warning "跳过MongoDB连接测试（mongosh未安装）"
fi

# ============================================
# 4. 启动FastAPI后端
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

# 等待后端启动（最多90秒，增加容错时间）
log_info "等待FastAPI后端启动..."
BACKEND_READY=false
for i in {1..90}; do
    if curl -f http://localhost:8000/api/health > /dev/null 2>&1; then
        log_success "FastAPI后端启动成功"
        BACKEND_READY=true
        break
    fi
    # 每10秒打印一次等待信息
    if [ $((i % 10)) -eq 0 ]; then
        log_info "仍在等待后端启动... ($i/90秒)"
    fi
    sleep 1
done

# 如果后端未就绪，发出警告但继续启动Nginx
if [ "$BACKEND_READY" = false ]; then
    log_warning "FastAPI后端健康检查超时，但将继续启动Nginx"
    log_warning "应用可能需要额外时间建立数据库连接"
    log_warning "请在浏览器访问/api/health检查后端状态"
fi

# ============================================
# 5. 启动Nginx
# ============================================
log_info "启动Nginx服务..."

# 测试Nginx配置
nginx -t || {
    log_error "Nginx配置测试失败！"
    exit 1
}

log_success "Nginx配置测试通过"
log_info "启动Nginx（前台模式）..."

# ============================================
# 6. 启动完成
# ============================================
log_success "=========================================="
log_success "所有服务启动成功！"
log_success "=========================================="
log_info "服务状态："
log_info "  ✓ FastAPI    - 运行中 (PID: $BACKEND_PID)"
log_info "  ✓ Nginx      - 准备启动"
log_info "  ✓ MongoDB    - 外部托管"
log_info "  ✓ Redis      - 外部托管"
log_success "=========================================="
log_info "访问地址: http://localhost"
log_info "健康检查: http://localhost/health"
log_info "后端API: http://localhost/api"
log_success "=========================================="

# 启动Nginx（前台运行，保持容器运行）
exec nginx -g 'daemon off;'

