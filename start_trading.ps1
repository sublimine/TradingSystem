# =============================================================================
# INSTITUTIONAL TRADING SYSTEM - AUTO LAUNCHER (PowerShell)
# Lanzamiento automatizado con checks de seguridad para Windows
# =============================================================================

# Configuración de errores
$ErrorActionPreference = "Stop"

# Colores
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

Write-ColorOutput Blue "============================================================================="
Write-ColorOutput Blue "  INSTITUTIONAL TRADING SYSTEM - AUTO LAUNCHER"
Write-ColorOutput Blue "============================================================================="
Write-Output ""

# =============================================================================
# PHASE 1: PRE-FLIGHT CHECKS
# =============================================================================

Write-ColorOutput Yellow "[1/5] Running pre-flight checks..."
python scripts/pre_flight_check.py
if ($LASTEXITCODE -ne 0) {
    Write-ColorOutput Red "❌ Pre-flight checks FAILED. Fix errors before launching."
    exit 1
}
Write-ColorOutput Green "✅ Pre-flight checks passed"
Write-Output ""

# =============================================================================
# PHASE 2: ENVIRONMENT SETUP
# =============================================================================

Write-ColorOutput Yellow "[2/5] Setting up environment..."

# Set Python path
$env:PYTHONPATH = "$PSScriptRoot;$PSScriptRoot\src;$env:PYTHONPATH"

# Create necessary directories
$directories = @("logs", "data\history", "models\saved", "checkpoints")
foreach ($dir in $directories) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

Write-ColorOutput Green "✅ Environment configured"
Write-Output ""

# =============================================================================
# PHASE 3: DATABASE CHECK
# =============================================================================

Write-ColorOutput Yellow "[3/5] Checking database connection..."

$dbCheckScript = @"
import sys
try:
    import psycopg2
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='trading_system',
        user='trading_user',
        password='abc'
    )
    conn.close()
    print('✅ Database connection OK')
except Exception as e:
    print(f'❌ Database connection FAILED: {e}')
    sys.exit(1)
"@

$dbCheckScript | python
if ($LASTEXITCODE -ne 0) {
    Write-ColorOutput Red "❌ Database not available"
    exit 1
}
Write-ColorOutput Green "✅ Database ready"
Write-Output ""

# =============================================================================
# PHASE 4: METATRADER 5 CHECK
# =============================================================================

Write-ColorOutput Yellow "[4/5] Checking MetaTrader 5..."

$mt5CheckScript = @"
import sys
try:
    import MetaTrader5 as mt5
    if not mt5.initialize():
        print(f'❌ MT5 initialization failed: {mt5.last_error()}')
        sys.exit(1)

    account_info = mt5.account_info()
    if account_info is None:
        print('❌ MT5 not logged in')
        sys.exit(1)

    print(f'✅ MT5 connected - Account: {account_info.login}, Balance: `${account_info.balance:.2f}')
    mt5.shutdown()
except Exception as e:
    print(f'❌ MT5 error: {e}')
    sys.exit(1)
"@

$mt5CheckScript | python
if ($LASTEXITCODE -ne 0) {
    Write-ColorOutput Red "❌ MetaTrader 5 not ready"
    exit 1
}
Write-ColorOutput Green "✅ MT5 ready"
Write-Output ""

# =============================================================================
# PHASE 5: LAUNCH TRADING ENGINE
# =============================================================================

Write-ColorOutput Yellow "[5/5] Launching trading engine..."
Write-Output ""
Write-ColorOutput Green "=========================================================================="
Write-ColorOutput Green "  SISTEMA EN VIVO - Trading institucional activo"
Write-ColorOutput Green "=========================================================================="
Write-Output ""

# Launch with auto-restart on crash
while ($true) {
    $dateStr = Get-Date -Format "yyyyMMdd"
    $logFile = "logs\trading_$dateStr.log"

    # Run trading engine and capture output
    python scripts/live_trading_engine_institutional.py 2>&1 | Tee-Object -FilePath $logFile -Append

    $exitCode = $LASTEXITCODE

    if ($exitCode -eq 0) {
        Write-ColorOutput Blue "Trading engine stopped gracefully"
        break
    } else {
        Write-ColorOutput Red "Trading engine crashed with code $exitCode"
        Write-ColorOutput Yellow "Restarting in 10 seconds..."
        Start-Sleep -Seconds 10
    }
}

Write-ColorOutput Blue "Trading session ended"
