# SCRIPT DE OPTIMIZACION - Ejecucion segura
$ErrorActionPreference = "Stop"

Write-Host "`nINICIANDO OPTIMIZACION..." -ForegroundColor Green

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = "C:\TradingSystem\backups\pre_optimization_$timestamp"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

Write-Host "Creando backups..." -ForegroundColor Yellow

$strategies = @(
    "liquidity_sweep.py",
    "mean_reversion_statistical.py",
    "volatility_regime_adaptation.py",
    "order_flow_toxicity.py",
    "momentum_quality.py",
    "kalman_pairs_trading.py",
    "correlation_divergence.py",
    "breakout_volume_confirmation.py"
)

foreach ($strategy in $strategies) {
    Copy-Item "C:\TradingSystem\src\strategies\$strategy" "$backupDir\$strategy"
}

Write-Host "OK Backups creados" -ForegroundColor Green

# OPTIMIZACIONES
Write-Host "`nAplicando optimizaciones..." -ForegroundColor Yellow

# 1. LIQUIDITY SWEEP
$content = Get-Content "C:\TradingSystem\src\strategies\liquidity_sweep.py" -Raw
$content = $content -replace "config\.get\('lookback_periods', \[1440, 2880, 4320\]\)", "config.get('lookback_periods', [720, 1440, 2160])"
$content = $content -replace "config\.get\('volume_threshold_multiplier', 2\.0\)", "config.get('volume_threshold_multiplier', 1.5)"
$content = $content -replace "config\.get\('reversal_velocity_min', 5\.0\)", "config.get('reversal_velocity_min', 3.5)"
$content = $content -replace "config\.get\('vpin_threshold', 0\.65\)", "config.get('vpin_threshold', 0.55)"
$content = $content -replace "config\.get\('min_confirmation_score', 4\)", "config.get('min_confirmation_score', 3)"
Set-Content -Path "C:\TradingSystem\src\strategies\liquidity_sweep.py" -Value $content -Encoding UTF8
Write-Host "  [1/8] liquidity_sweep.py" -ForegroundColor Green

# 2. MEAN REVERSION - CRITICO
$content = Get-Content "C:\TradingSystem\src\strategies\mean_reversion_statistical.py" -Raw
$content = $content -replace "config\.get\('entry_sigma_threshold', 3\.0\)", "config.get('entry_sigma_threshold', 2.0)"
$content = $content -replace "config\.get\('exit_sigma_threshold', 0\.8\)", "config.get('exit_sigma_threshold', 0.6)"
$content = $content -replace "config\.get\('vpin_exhaustion_threshold', 0\.70\)", "config.get('vpin_exhaustion_threshold', 0.60)"
$content = $content -replace "config\.get\('imbalance_reversal_threshold', 0\.40\)", "config.get('imbalance_reversal_threshold', 0.30)"
$content = $content -replace "config\.get\('volume_spike_multiplier', 2\.5\)", "config.get('volume_spike_multiplier', 1.8)"
$content = $content -replace "config\.get\('reversal_velocity_min', 8\.0\)", "config.get('reversal_velocity_min', 5.0)"
$content = $content -replace "factors_met >= 3", "factors_met >= 2"
Set-Content -Path "C:\TradingSystem\src\strategies\mean_reversion_statistical.py" -Value $content -Encoding UTF8
Write-Host "  [2/8] mean_reversion_statistical.py (CRITICO)" -ForegroundColor Green

# 3. VOLATILITY REGIME
$content = Get-Content "C:\TradingSystem\src\strategies\volatility_regime_adaptation.py" -Raw
$content = $content -replace "config\.get\('regime_lookback', 50\)", "config.get('regime_lookback', 40)"
$content = $content -replace "config\.get\('low_vol_entry_threshold', 1\.5\)", "config.get('low_vol_entry_threshold', 1.2)"
$content = $content -replace "config\.get\('high_vol_entry_threshold', 2\.5\)", "config.get('high_vol_entry_threshold', 2.0)"
$content = $content -replace "config\.get\('min_regime_confidence', 0\.7\)", "config.get('min_regime_confidence', 0.6)"
Set-Content -Path "C:\TradingSystem\src\strategies\volatility_regime_adaptation.py" -Value $content -Encoding UTF8
Write-Host "  [3/8] volatility_regime_adaptation.py" -ForegroundColor Green

# 4. ORDER FLOW TOXICITY
$content = Get-Content "C:\TradingSystem\src\strategies\order_flow_toxicity.py" -Raw
$content = $content -replace "config\.get\('vpin_threshold', 0\.65\)", "config.get('vpin_threshold', 0.55)"
$content = $content -replace "config\.get\('min_consecutive_buckets', 3\)", "config.get('min_consecutive_buckets', 2)"
Set-Content -Path "C:\TradingSystem\src\strategies\order_flow_toxicity.py" -Value $content -Encoding UTF8
Write-Host "  [4/8] order_flow_toxicity.py" -ForegroundColor Green

# 5. MOMENTUM QUALITY
$content = Get-Content "C:\TradingSystem\src\strategies\momentum_quality.py" -Raw
$content = $content -replace "config\.get\('price_threshold', 0\.5\)", "config.get('price_threshold', 0.35)"
$content = $content -replace "config\.get\('min_quality_score', 0\.70\)", "config.get('min_quality_score', 0.60)"
$content = $content -replace "quality_score'\] < 0\.85", "quality_score'] < 0.75"
Set-Content -Path "C:\TradingSystem\src\strategies\momentum_quality.py" -Value $content -Encoding UTF8
Write-Host "  [5/8] momentum_quality.py" -ForegroundColor Green

# 6. KALMAN PAIRS
$content = Get-Content "C:\TradingSystem\src\strategies\kalman_pairs_trading.py" -Raw
$content = $content -replace "config\.get\('z_score_entry_threshold', 2\.0\)", "config.get('z_score_entry_threshold', 1.5)"
$content = $content -replace "config\.get\('min_correlation', 0\.75\)", "config.get('min_correlation', 0.70)"
$content = $content -replace "config\.get\('lookback_period', 200\)", "config.get('lookback_period', 150)"
Set-Content -Path "C:\TradingSystem\src\strategies\kalman_pairs_trading.py" -Value $content -Encoding UTF8
Write-Host "  [6/8] kalman_pairs_trading.py" -ForegroundColor Green

# 7. CORRELATION DIVERGENCE
$content = Get-Content "C:\TradingSystem\src\strategies\correlation_divergence.py" -Raw
$content = $content -replace "config\.get\('correlation_lookback', 100\)", "config.get('correlation_lookback', 75)"
$content = $content -replace "config\.get\('historical_correlation_min', 0\.80\)", "config.get('historical_correlation_min', 0.70)"
$content = $content -replace "config\.get\('divergence_correlation_threshold', 0\.50\)", "config.get('divergence_correlation_threshold', 0.60)"
$content = $content -replace "config\.get\('min_divergence_magnitude', 1\.5\)", "config.get('min_divergence_magnitude', 1.0)"
Set-Content -Path "C:\TradingSystem\src\strategies\correlation_divergence.py" -Value $content -Encoding UTF8
Write-Host "  [7/8] correlation_divergence.py" -ForegroundColor Green

# 8. BREAKOUT VOLUME
$content = Get-Content "C:\TradingSystem\src\strategies\breakout_volume_confirmation.py" -Raw
$content = $content -replace "config\.get\('atr_contraction_threshold', 0\.60\)", "config.get('atr_contraction_threshold', 0.70)"
$content = $content -replace "config\.get\('volume_breakout_multiplier', 3\.0\)", "config.get('volume_breakout_multiplier', 2.0)"
$content = $content -replace "config\.get\('imbalance_confirmation_threshold', 0\.35\)", "config.get('imbalance_confirmation_threshold', 0.25)"
$content = $content -replace "confirmation\['imbalance_aligned'\] and confirmation\['vpin_appropriate'\]", "confirmation['imbalance_aligned'] or confirmation['vpin_appropriate']"
Set-Content -Path "C:\TradingSystem\src\strategies\breakout_volume_confirmation.py" -Value $content -Encoding UTF8
Write-Host "  [8/8] breakout_volume_confirmation.py (CRITICO)" -ForegroundColor Green

Write-Host "`nVerificando sintaxis..." -ForegroundColor Yellow
$errors = 0
foreach ($strategy in $strategies) {
    python -m py_compile "C:\TradingSystem\src\strategies\$strategy" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { $errors++ }
}

if ($errors -gt 0) {
    Write-Host "X $errors errores - REVERTIENDO" -ForegroundColor Red
    foreach ($strategy in $strategies) {
        Copy-Item "$backupDir\$strategy" "C:\TradingSystem\src\strategies\$strategy" -Force
    }
    exit 1
}

Write-Host "OK Sintaxis valida" -ForegroundColor Green
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "OPTIMIZACION COMPLETADA" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Backup: $backupDir" -ForegroundColor Cyan
Write-Host "31 parametros optimizados en 8 estrategias" -ForegroundColor White
Write-Host "Impacto esperado: 10-20 ops/dia" -ForegroundColor White
Write-Host "`nPresione cualquier tecla para continuar..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
