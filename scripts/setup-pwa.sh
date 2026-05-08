#!/bin/bash

# PWA 应用设置脚本
# 用于快速生成图标并启动开发服务器

echo "🎨 TradingAgents-CN PWA 设置向导"
echo "=================================="
echo ""

# 检查是否在正确的目录
if [ ! -d "frontend" ]; then
    echo "❌ 错误：请在项目根目录运行此脚本"
    exit 1
fi

echo "📂 当前目录：$(pwd)"
echo ""

# 步骤1：检查 Node.js
echo "1️⃣ 检查 Node.js 环境..."
if ! command -v node &> /dev/null; then
    echo "❌ 未找到 Node.js，请先安装 Node.js"
    exit 1
fi
echo "✅ Node.js 版本：$(node -v)"
echo ""

# 步骤2：检查依赖
echo "2️⃣ 检查项目依赖..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "📦 正在安装依赖..."
    npm install
else
    echo "✅ 依赖已安装"
fi
cd ..
echo ""

# 步骤3：生成 PWA 图标
echo "3️⃣ 生成 PWA 图标..."
if [ -f "frontend/public/icon-192.png" ] && [ -f "frontend/public/icon-512.png" ]; then
    echo "⚠️  图标文件已存在"
    read -p "是否重新生成？(y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        node scripts/generate-pwa-icons.js
    else
        echo "✅ 跳过图标生成"
    fi
else
    echo "🚀 开始生成图标..."
    node scripts/generate-pwa-icons.js
fi
echo ""

# 步骤4：验证图标
echo "4️⃣ 验证 PWA 资源..."
MISSING_FILES=()

if [ ! -f "frontend/public/icon-192.png" ]; then
    MISSING_FILES+=("icon-192.png")
fi

if [ ! -f "frontend/public/icon-512.png" ]; then
    MISSING_FILES+=("icon-512.png")
fi

if [ ! -f "frontend/public/apple-touch-icon.png" ]; then
    MISSING_FILES+=("apple-touch-icon.png")
fi

if [ ${#MISSING_FILES[@]} -eq 0 ]; then
    echo "✅ 所有 PWA 资源已就绪"
else
    echo "⚠️  缺少以下文件："
    for file in "${MISSING_FILES[@]}"; do
        echo "   - $file"
    done
    echo ""
    echo "💡 提示：可以访问以下地址手动生成图标："
    echo "   http://localhost:3000/generate-icons.html"
fi
echo ""

# 步骤5：启动开发服务器
echo "5️⃣ 启动开发服务器..."
echo ""
echo "=================================="
echo "🎉 PWA 设置完成！"
echo "=================================="
echo ""
echo "📝 接下来："
echo "   1. 访问 http://localhost:3000"
echo "   2. 打开浏览器开发者工具 (F12)"
echo "   3. 检查 Application > Manifest"
echo "   4. 检查 Application > Service Workers"
echo "   5. 测试移动端适配（设备模拟器）"
echo ""
echo "💡 提示："
echo "   - PWA 需要 HTTPS 或 localhost"
echo "   - 首次加载会注册 Service Worker"
echo "   - 5秒后会显示安装提示"
echo ""
read -p "按 Enter 键启动开发服务器..."

cd frontend
npm run dev

