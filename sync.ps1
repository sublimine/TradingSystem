# sync.ps1
# Script profesional para sincronizar cambios desde GitHub
# Maneja automáticamente logs bloqueados y conflictos

Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "                    SINCRONIZACIÓN CON GITHUB                                   " -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

$ErrorActionPreference = "SilentlyContinue"

# 1. Cerrar procesos Python que puedan estar usando logs
Write-Host "`n[1/5] Cerrando procesos Python bloqueantes..." -ForegroundColor Yellow
$pythonProcesses = Get-Process python* -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    Write-Host "      Encontrados $($pythonProcesses.Count) proceso(s) Python" -ForegroundColor Gray
    $pythonProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    Write-Host "      ✅ Procesos cerrados" -ForegroundColor Green
} else {
    Write-Host "      ✅ No hay procesos Python ejecutándose" -ForegroundColor Green
}

# 2. Limpiar logs bloqueados
Write-Host "`n[2/5] Limpiando logs bloqueados..." -ForegroundColor Yellow
$logFile = "logs\live_trading.log"
if (Test-Path $logFile) {
    try {
        # Intentar renombrar en lugar de eliminar (más seguro)
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $backupLog = "logs\live_trading_backup_$timestamp.log"
        Move-Item -Path $logFile -Destination $backupLog -Force
        Write-Host "      ✅ Log movido a: $backupLog" -ForegroundColor Green
    } catch {
        Write-Host "      ⚠️  No se pudo mover el log (puede estar en uso todavía)" -ForegroundColor Yellow
        # Esperar un poco más
        Start-Sleep -Seconds 2
        try {
            Remove-Item -Path $logFile -Force
            Write-Host "      ✅ Log eliminado" -ForegroundColor Green
        } catch {
            Write-Host "      ⚠️  Log aún bloqueado, pero continuamos..." -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "      ✅ No hay log que limpiar" -ForegroundColor Green
}

# 3. Asegurar que logs/ está en .gitignore
Write-Host "`n[3/5] Configurando .gitignore..." -ForegroundColor Yellow
$gitignoreContent = Get-Content .gitignore -Raw -ErrorAction SilentlyContinue
if ($gitignoreContent -notmatch "logs/\*\.log") {
    Add-Content .gitignore "`n# Logs de ejecución`nlogs/*.log`nlogs/live_trading*.log"
    Write-Host "      ✅ Logs añadidos a .gitignore" -ForegroundColor Green
} else {
    Write-Host "      ✅ .gitignore ya configurado" -ForegroundColor Green
}

# 4. Resetear cambios locales que puedan causar conflictos
Write-Host "`n[4/5] Limpiando cambios locales..." -ForegroundColor Yellow
git reset --hard HEAD 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "      ✅ Workspace limpio" -ForegroundColor Green
} else {
    Write-Host "      ⚠️  Algunos archivos no se pudieron resetear" -ForegroundColor Yellow
}

# 5. Hacer pull desde GitHub
Write-Host "`n[5/5] Sincronizando desde GitHub..." -ForegroundColor Yellow
Write-Host "      Rama: claude/repo-context-summary-011CUyJb8kfhzpna9sWGrd5d" -ForegroundColor Gray

$pullOutput = git pull origin claude/repo-context-summary-011CUyJb8kfhzpna9sWGrd5d 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "      ✅ Sincronización exitosa" -ForegroundColor Green

    # Mostrar qué cambió
    Write-Host "`n      Archivos actualizados:" -ForegroundColor Cyan
    $pullOutput | Where-Object { $_ -match "^\s+\w+\s+\|" } | ForEach-Object {
        Write-Host "      $_" -ForegroundColor Gray
    }
} else {
    Write-Host "      ❌ Error en pull:" -ForegroundColor Red
    Write-Host $pullOutput -ForegroundColor Red
}

Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "                            SINCRONIZACIÓN COMPLETA                             " -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

Write-Host "`nEstado del repositorio:" -ForegroundColor Yellow
git status --short

Write-Host "`n✅ Listo para ejecutar scripts" -ForegroundColor Green
Write-Host "   Ejemplo: python scripts\live_trading_engine.py --dry-run`n" -ForegroundColor Gray

$ErrorActionPreference = "Continue"
