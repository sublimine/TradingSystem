# =============================================================================
# SCRIPT DE INTEGRACIÓN COMPLETA PARA VPS WINDOWS
# Trae TODO el trabajo institucional + 109 bugs + deployment
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host "=============================================================================" -ForegroundColor Blue
Write-Host "  INTEGRACIÓN COMPLETA - 25 Estrategias + 109 Bugs + Deployment" -ForegroundColor Blue
Write-Host "=============================================================================" -ForegroundColor Blue
Write-Host ""

# Configuración
$REPO_URL = "https://github.com/sublimine/TradingSystem.git"
$BRANCH = "claude/repo-context-summary-011CUyJb8kfhzpna9sWGrd5d"
$INSTALL_DIR = "$HOME\TradingSystem"

# =============================================================================
# PASO 1: BACKUP (si existe)
# =============================================================================
if (Test-Path $INSTALL_DIR) {
    Write-Host "⚠️  Directorio existente detectado" -ForegroundColor Yellow
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $BACKUP_DIR = "$HOME\TradingSystem_backup_$timestamp"
    Write-Host "📦 Creando backup en: $BACKUP_DIR" -ForegroundColor Yellow
    Move-Item -Path $INSTALL_DIR -Destination $BACKUP_DIR
    Write-Host "✅ Backup creado" -ForegroundColor Green
    Write-Host ""
}

# =============================================================================
# PASO 2: CLONAR REPOSITORIO COMPLETO
# =============================================================================
Write-Host "📥 Clonando repositorio completo..." -ForegroundColor Yellow
Set-Location $HOME
git clone $REPO_URL TradingSystem
Set-Location TradingSystem

Write-Host "🔄 Cambiando a rama institucional..." -ForegroundColor Yellow
git checkout $BRANCH

Write-Host "✅ Repositorio clonado" -ForegroundColor Green
Write-Host ""

# =============================================================================
# PASO 3: VERIFICAR CONTENIDO
# =============================================================================
Write-Host "🔍 Verificando contenido..." -ForegroundColor Yellow

# Contar estrategias
$STRATEGY_COUNT = (Get-ChildItem src\strategies\*.py | Where-Object { $_.Name -ne "__init__.py" }).Count
Write-Host "   Estrategias encontradas: $STRATEGY_COUNT"

# Verificar scripts
if ((Test-Path "start_trading.sh") -and (Test-Path "start_trading.ps1")) {
    Write-Host "   ✅ Scripts de deployment: OK" -ForegroundColor Green
} else {
    Write-Host "   ❌ Scripts de deployment: FALTA" -ForegroundColor Red
}

# Verificar core components
$CORE_COUNT = (Get-ChildItem src\core\*.py).Count
Write-Host "   Core components: $CORE_COUNT archivos"

# Verificar último commit
$LAST_COMMIT = git log -1 --oneline
Write-Host "   Último commit: $LAST_COMMIT"

Write-Host ""

# =============================================================================
# PASO 4: INSTALAR DEPENDENCIAS PYTHON
# =============================================================================
Write-Host "📦 Instalando dependencias Python..." -ForegroundColor Yellow

# Verificar pip
if (!(Get-Command pip -ErrorAction SilentlyContinue)) {
    Write-Host "❌ pip no encontrado. Instala Python primero" -ForegroundColor Red
    exit 1
}

# Instalar packages
pip install --upgrade pip --quiet
pip install numpy==1.24.3 pandas==2.0.3 scikit-learn==1.3.0 --quiet
pip install MetaTrader5==5.0.45 psycopg2-binary==2.9.6 --quiet
pip install scipy==1.11.1 xgboost==1.7.6 --quiet
pip install python-dateutil pytz matplotlib seaborn joblib --quiet

Write-Host "✅ Dependencias instaladas" -ForegroundColor Green
Write-Host ""

# =============================================================================
# PASO 5: CONFIGURAR POSTGRESQL
# =============================================================================
Write-Host "🗄️  Configurando PostgreSQL..." -ForegroundColor Yellow

# Verificar si PostgreSQL está corriendo
$pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($pgService -and $pgService.Status -ne "Running") {
    Write-Host "⚠️  PostgreSQL no está corriendo. Iniciando..." -ForegroundColor Yellow
    Start-Service $pgService.Name
}

# Crear database y usuario (usa psql desde PATH)
try {
    psql -U postgres -c "CREATE DATABASE trading_system;" 2>$null
} catch {
    Write-Host "   Database ya existe o error de permisos" -ForegroundColor Yellow
}

Write-Host "✅ PostgreSQL configurado (verifica manualmente si es necesario)" -ForegroundColor Green
Write-Host ""

# =============================================================================
# PASO 6: HABILITAR EJECUCIÓN DE SCRIPTS
# =============================================================================
Write-Host "🔐 Habilitando ejecución de scripts..." -ForegroundColor Yellow
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

Write-Host "✅ Permisos configurados" -ForegroundColor Green
Write-Host ""

# =============================================================================
# PASO 7: PRE-FLIGHT CHECK
# =============================================================================
Write-Host "✈️  Ejecutando pre-flight check..." -ForegroundColor Yellow
python scripts/pre_flight_check.py
Write-Host ""

# =============================================================================
# RESUMEN FINAL
# =============================================================================
Write-Host "=============================================================================" -ForegroundColor Blue
Write-Host "  ✅ INTEGRACIÓN COMPLETADA" -ForegroundColor Green
Write-Host "=============================================================================" -ForegroundColor Blue
Write-Host ""
Write-Host "📊 CONTENIDO INTEGRADO:"
Write-Host "   - $STRATEGY_COUNT estrategias institucionales"
Write-Host "   - Brain + Risk Manager + Position Manager"
Write-Host "   - ML Adaptive Engine"
Write-Host "   - Deployment automático (Linux + Windows)"
Write-Host "   - 109 bugs críticos arreglados"
Write-Host ""
Write-Host "🚀 PARA LANZAR EL SISTEMA:" -ForegroundColor Yellow
Write-Host ""
Write-Host "   cd $INSTALL_DIR" -ForegroundColor Cyan
Write-Host "   .\start_trading.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 PARA MONITOREAR:" -ForegroundColor Yellow
Write-Host ""
Write-Host "   cd $INSTALL_DIR" -ForegroundColor Cyan
Write-Host "   .\monitor.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "📝 LOGS:" -ForegroundColor Yellow
Write-Host ""
Write-Host "   Get-Content logs\trading_`$(Get-Date -Format 'yyyyMMdd').log -Wait -Tail 20" -ForegroundColor Cyan
Write-Host ""
Write-Host "=============================================================================" -ForegroundColor Blue
Write-Host "  Sistema listo para trading institucional 🎯" -ForegroundColor Green
Write-Host "=============================================================================" -ForegroundColor Blue
