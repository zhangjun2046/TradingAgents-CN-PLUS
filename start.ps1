param(
    [ValidateSet("start", "stop", "status")]
    [string]$Action = "start",
    [switch]$SkipDb,
    [switch]$NoInstall
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$FrontendDir = Join-Path $ProjectRoot "frontend"
$RunDir = Join-Path $ProjectRoot ".run"
$LogDir = Join-Path $ProjectRoot "logs"

if (-not (Test-Path $RunDir)) { New-Item -Path $RunDir -ItemType Directory | Out-Null }
if (-not (Test-Path $LogDir)) { New-Item -Path $LogDir -ItemType Directory | Out-Null }

function Info([string]$msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Ok([string]$msg) { Write-Host "[ OK ] $msg" -ForegroundColor Green }
function Warn([string]$msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }

function Require-Command([string]$name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        throw "Missing command: $name. Please install it and add to PATH."
    }
}

function Get-EnvValue([string]$key, [string]$defaultValue = "") {
    $envFile = Join-Path $ProjectRoot ".env"
    if (-not (Test-Path $envFile)) { return $defaultValue }
    $pattern = '^\s*' + [regex]::Escape($key) + '=(.*)$'
    $line = Select-String -Path $envFile -Pattern $pattern -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($line) { return $line.Matches[0].Groups[1].Value.Trim() }
    return $defaultValue
}

function Start-Db {
    Require-Command "docker"

    $mongoName = "tradingagents-mongodb"
    $redisName = "tradingagents-redis"
    $mongoUser = Get-EnvValue "MONGODB_USERNAME" "admin"
    $mongoPass = Get-EnvValue "MONGODB_PASSWORD" "tradingagents123"
    $mongoDb = Get-EnvValue "MONGODB_DATABASE" "tradingagents"
    $redisPass = Get-EnvValue "REDIS_PASSWORD" ""

    $mongoRunning = docker ps --filter "name=^/$mongoName$" --format "{{.Names}}"
    if (-not $mongoRunning) {
        $mongoExists = docker ps -a --filter "name=^/$mongoName$" --format "{{.Names}}"
        if ($mongoExists) {
            Info "Starting existing MongoDB container..."
            docker start $mongoName | Out-Null
        } else {
            Info "Creating MongoDB container..."
            docker run -d --name $mongoName -p 27017:27017 `
                -e "MONGO_INITDB_ROOT_USERNAME=$mongoUser" `
                -e "MONGO_INITDB_ROOT_PASSWORD=$mongoPass" `
                -e "MONGO_INITDB_DATABASE=$mongoDb" `
                --restart unless-stopped mongo:4.4 | Out-Null
        }
    }
    Ok "MongoDB ready on localhost:27017"

    $redisRunning = docker ps --filter "name=^/$redisName$" --format "{{.Names}}"
    if (-not $redisRunning) {
        $redisExists = docker ps -a --filter "name=^/$redisName$" --format "{{.Names}}"
        if ($redisExists) {
            Info "Starting existing Redis container..."
            docker start $redisName | Out-Null
        } else {
            Info "Creating Redis container..."
            if ([string]::IsNullOrWhiteSpace($redisPass)) {
                docker run -d --name $redisName -p 6379:6379 --restart unless-stopped `
                    redis:7-alpine redis-server --appendonly yes | Out-Null
            } else {
                docker run -d --name $redisName -p 6379:6379 --restart unless-stopped `
                    redis:7-alpine redis-server --appendonly yes --requirepass $redisPass | Out-Null
            }
        }
    }
    Ok "Redis ready on localhost:6379"
}

function Get-PythonExe {
    $venvPy = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPy) { return $venvPy }
    return "python"
}

function Ensure-BackendDeps([string]$pythonExe) {
    if ($NoInstall) { return }
    & $pythonExe -c "import fastapi,uvicorn" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Info "Installing backend dependencies (pip install -e .)..."
        Set-Location $ProjectRoot
        & $pythonExe -m pip install -e .
        Ok "Backend dependencies installed"
    }
}

function Ensure-FrontendDeps {
    if ($NoInstall) { return }
    $nodeModules = Join-Path $FrontendDir "node_modules"
    if (-not (Test-Path $nodeModules)) {
        Info "Installing frontend dependencies (npm install)..."
        Set-Location $FrontendDir
        npm install
        Ok "Frontend dependencies installed"
    }
}

function Start-Backend {
    $pidFile = Join-Path $RunDir "backend.pid"
    if (Test-Path $pidFile) {
        $pid = Get-Content $pidFile
        if (Get-Process -Id $pid -ErrorAction SilentlyContinue) {
            Warn "Backend already running (PID: $pid)"
            return
        }
        Remove-Item $pidFile -Force
    }

    $pythonExe = Get-PythonExe
    Ensure-BackendDeps $pythonExe

    $outLog = Join-Path $LogDir "backend.log"
    $errLog = Join-Path $LogDir "backend.error.log"

    $proc = Start-Process -FilePath $pythonExe `
        -ArgumentList "-m", "app" `
        -WorkingDirectory $ProjectRoot `
        -RedirectStandardOutput $outLog `
        -RedirectStandardError $errLog `
        -PassThru

    $proc.Id | Out-File $pidFile -Encoding ascii -Force
    Ok "Backend started: http://localhost:8000"
}

function Start-Frontend {
    $pidFile = Join-Path $RunDir "frontend.pid"
    if (Test-Path $pidFile) {
        $pid = Get-Content $pidFile
        if (Get-Process -Id $pid -ErrorAction SilentlyContinue) {
            Warn "Frontend already running (PID: $pid)"
            return
        }
        Remove-Item $pidFile -Force
    }

    Ensure-FrontendDeps

    $outLog = Join-Path $LogDir "frontend.log"
    $errLog = Join-Path $LogDir "frontend.error.log"

    $proc = Start-Process -FilePath "cmd.exe" `
        -ArgumentList "/c", "npm run dev" `
        -WorkingDirectory $FrontendDir `
        -RedirectStandardOutput $outLog `
        -RedirectStandardError $errLog `
        -PassThru

    $proc.Id | Out-File $pidFile -Encoding ascii -Force
    Ok "Frontend started: http://localhost:3000"
}

function Stop-ByPidFile([string]$pidFile, [string]$name) {
    if (-not (Test-Path $pidFile)) {
        Info "$name not running"
        return
    }
    $pid = Get-Content $pidFile
    $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
    if ($proc) {
        Stop-Process -Id $pid -Force
        Ok "$name stopped (PID: $pid)"
    } else {
        Warn "$name pid file found but process is not alive"
    }
    Remove-Item $pidFile -Force
}

function Stop-All {
    Stop-ByPidFile (Join-Path $RunDir "backend.pid") "Backend"
    Stop-ByPidFile (Join-Path $RunDir "frontend.pid") "Frontend"

    if (Get-Command docker -ErrorAction SilentlyContinue) {
        docker stop tradingagents-mongodb tradingagents-redis 2>$null | Out-Null
        Info "Tried to stop MongoDB/Redis containers"
    }
}

function Show-Status {
    $backendPidFile = Join-Path $RunDir "backend.pid"
    $frontendPidFile = Join-Path $RunDir "frontend.pid"

    if (Test-Path $backendPidFile) {
        $pid = Get-Content $backendPidFile
        if (Get-Process -Id $pid -ErrorAction SilentlyContinue) { Ok "Backend running (PID: $pid)" } else { Warn "Backend pid file stale" }
    } else {
        Info "Backend not running"
    }

    if (Test-Path $frontendPidFile) {
        $pid = Get-Content $frontendPidFile
        if (Get-Process -Id $pid -ErrorAction SilentlyContinue) { Ok "Frontend running (PID: $pid)" } else { Warn "Frontend pid file stale" }
    } else {
        Info "Frontend not running"
    }

    if (Get-Command docker -ErrorAction SilentlyContinue) {
        $mongo = docker ps --filter "name=^/tradingagents-mongodb$" --format "{{.Status}}"
        $redis = docker ps --filter "name=^/tradingagents-redis$" --format "{{.Status}}"
        if ($mongo) { Ok "MongoDB: $mongo" } else { Info "MongoDB not running" }
        if ($redis) { Ok "Redis: $redis" } else { Info "Redis not running" }
    }
}

Write-Host ""
Write-Host "TradingAgents-CN MVP launcher" -ForegroundColor Magenta
Write-Host "Action: $Action" -ForegroundColor DarkGray
Write-Host ""

switch ($Action) {
    "start" {
        Require-Command "python"
        Require-Command "node"
        if ((-not $SkipDb) -and (-not (Get-Command docker -ErrorAction SilentlyContinue))) {
            throw "Docker is required to start DB containers. Use -SkipDb if DB is already running."
        }

        if (-not (Test-Path (Join-Path $ProjectRoot ".env"))) {
            Warn ".env not found. Script continues, but you should configure .env first."
        }

        if (-not $SkipDb) { Start-Db } else { Info "Skip DB startup (-SkipDb)" }
        Start-Backend
        Start-Frontend

        Write-Host ""
        Ok "All services started"
        Write-Host "Frontend: http://localhost:3000"
        Write-Host "Backend : http://localhost:8000"
        Write-Host "Docs    : http://localhost:8000/docs"
        Write-Host "Logs    : logs/backend.log, logs/frontend.log"
        Write-Host ""
    }
    "stop" {
        Stop-All
        Ok "Stop completed"
    }
    "status" {
        Show-Status
    }
}
