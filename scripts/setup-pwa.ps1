# PWA 应用设置脚本 (PowerShell)
# 用于快速生成图标并启动开发服务器

Write-Host "🎨 TradingAgents-CN PWA 设置向导" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# 检查是否在正确的目录
if (-not (Test-Path "frontend")) {
    Write-Host "❌ 错误：请在项目根目录运行此脚本" -ForegroundColor Red
    exit 1
}

Write-Host "📂 当前目录：$PWD" -ForegroundColor Gray
Write-Host ""

# 步骤1：检查 Node.js
Write-Host "1️⃣ 检查 Node.js 环境..." -ForegroundColor Yellow
try {
    $nodeVersion = node -v
    Write-Host "✅ Node.js 版本：$nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ 未找到 Node.js，请先安装 Node.js" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 步骤2：检查依赖
Write-Host "2️⃣ 检查项目依赖..." -ForegroundColor Yellow
Set-Location frontend
if (-not (Test-Path "node_modules")) {
    Write-Host "📦 正在安装依赖..." -ForegroundColor Cyan
    npm install
} else {
    Write-Host "✅ 依赖已安装" -ForegroundColor Green
}
Set-Location ..
Write-Host ""

# 步骤3：生成 PWA 图标
Write-Host "3️⃣ 生成 PWA 图标..." -ForegroundColor Yellow
$icon192Exists = Test-Path "frontend/public/icon-192.png"
$icon512Exists = Test-Path "frontend/public/icon-512.png"

if ($icon192Exists -and $icon512Exists) {
    Write-Host "⚠️  图标文件已存在" -ForegroundColor Yellow
    $response = Read-Host "是否重新生成？(y/N)"
    if ($response -eq "y" -or $response -eq "Y") {
        node scripts/generate-pwa-icons.js
    } else {
        Write-Host "✅ 跳过图标生成" -ForegroundColor Green
    }
} else {
    Write-Host "🚀 开始生成图标..." -ForegroundColor Cyan
    node scripts/generate-pwa-icons.js
}
Write-Host ""

# 步骤4：验证图标
Write-Host "4️⃣ 验证 PWA 资源..." -ForegroundColor Yellow
$missingFiles = @()

if (-not (Test-Path "frontend/public/icon-192.png")) {
    $missingFiles += "icon-192.png"
}

if (-not (Test-Path "frontend/public/icon-512.png")) {
    $missingFiles += "icon-512.png"
}

if (-not (Test-Path "frontend/public/apple-touch-icon.png")) {
    $missingFiles += "apple-touch-icon.png"
}

if ($missingFiles.Count -eq 0) {
    Write-Host "✅ 所有 PWA 资源已就绪" -ForegroundColor Green
} else {
    Write-Host "⚠️  缺少以下文件：" -ForegroundColor Yellow
    foreach ($file in $missingFiles) {
        Write-Host "   - $file" -ForegroundColor Gray
    }
    Write-Host ""
    Write-Host "💡 提示：可以访问以下地址手动生成图标：" -ForegroundColor Cyan
    Write-Host "   http://localhost:3000/generate-icons.html" -ForegroundColor Cyan
}
Write-Host ""

# 步骤5：启动开发服务器
Write-Host "5️⃣ 启动开发服务器..." -ForegroundColor Yellow
Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "🎉 PWA 设置完成！" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📝 接下来：" -ForegroundColor Cyan
Write-Host "   1. 访问 http://localhost:3000"
Write-Host "   2. 打开浏览器开发者工具 (F12)"
Write-Host "   3. 检查 Application > Manifest"
Write-Host "   4. 检查 Application > Service Workers"
Write-Host "   5. 测试移动端适配（设备模拟器）"
Write-Host ""
Write-Host "💡 提示：" -ForegroundColor Cyan
Write-Host "   - PWA 需要 HTTPS 或 localhost"
Write-Host "   - 首次加载会注册 Service Worker"
Write-Host "   - 5秒后会显示安装提示"
Write-Host ""
Read-Host "按 Enter 键启动开发服务器"

Set-Location frontend
npm run dev

