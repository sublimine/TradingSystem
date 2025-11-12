# 🚀 DEPLOYMENT GUIDE - Institutional Trading System

## REQUISITOS PRE-LANZAMIENTO

### 1. Sistema Operativo
- Linux (Ubuntu 20.04+ recomendado) o Windows 10/11
- 8GB RAM mínimo (16GB recomendado)
- 50GB espacio en disco
- CPU multi-core (4+ cores recomendado)

### 2. Software Requerido

```bash
# Python 3.8+
python3 --version

# PostgreSQL 12+
psql --version

# MetaTrader 5 (Windows) o Wine (Linux)
# Descarga: https://www.metatrader5.com/
```

### 3. Dependencias Python

```bash
pip install -r requirements.txt
```

---

## PASO 1: CONFIGURACIÓN DATABASE

```bash
# Crear database
sudo -u postgres psql

CREATE DATABASE trading_system;
CREATE USER trading_user WITH PASSWORD 'abc';
GRANT ALL PRIVILEGES ON DATABASE trading_system TO trading_user;
\q

# Importar schema
psql -U trading_user -d trading_system -f schema/trading_system_schema.sql
```

---

## PASO 2: CONFIGURACIÓN MT5

1. **Instalar MetaTrader 5**
   - Windows: Descarga e instala desde mql5.com
   - Linux: Usa Wine + PlayOnLinux

2. **Configurar cuenta demo/real**
   - Login a tu broker
   - Habilitar "Algorithmic Trading" en MT5
   - Tools → Options → Expert Advisors → Allow automated trading

3. **Verificar conexión**
```bash
python3 scripts/test_mt5_connection.py
```

---

## PASO 3: PRE-FLIGHT CHECK

**CRÍTICO**: Ejecuta pre-flight check ANTES de lanzar

```bash
chmod +x start_trading.sh
python3 scripts/pre_flight_check.py
```

Debe mostrar:
```
✅ ALL CRITICAL CHECKS PASSED - System ready for launch!
```

---

## PASO 4: LANZAMIENTO

### Modo Automático (Recomendado)

**WINDOWS (PowerShell):**
```powershell
.\start_trading.ps1
```

**LINUX (Bash):**
```bash
chmod +x start_trading.sh
./start_trading.sh
```

Ambos scripts:
1. ✅ Ejecutan pre-flight checks
2. ✅ Configuran environment
3. ✅ Verifican database
4. ✅ Verifican MT5
5. ✅ Lanzan engine con auto-restart

### Modo Manual

**WINDOWS (PowerShell):**
```powershell
$env:PYTHONPATH = "$PSScriptRoot;$PSScriptRoot\src;$env:PYTHONPATH"
cd scripts
python live_trading_engine_institutional.py
```

**LINUX (Bash):**
```bash
export PYTHONPATH="/home/user/TradingSystem:/home/user/TradingSystem/src:$PYTHONPATH"
cd scripts
python3 live_trading_engine_institutional.py
```

---

## PASO 5: MONITOREO

### Terminal 1: Trading Engine

**WINDOWS:**
```powershell
.\start_trading.ps1
```

**LINUX:**
```bash
./start_trading.sh
```

### Terminal 2: Monitor en vivo

**WINDOWS:**
```powershell
.\monitor.ps1
```

**LINUX:**
```bash
chmod +x monitor.sh
./monitor.sh
```

### Logs en tiempo real

**WINDOWS:**
```powershell
Get-Content logs\trading_$(Get-Date -Format "yyyyMMdd").log -Wait -Tail 20
```

**LINUX:**
```bash
tail -f logs/trading_$(date +%Y%m%d).log
```

---

## CONFIGURACIÓN AVANZADA

### 1. Estrategias Activas

Editar `scripts/live_trading_engine_institutional.py`:

```python
STRATEGY_WHITELIST = [
    'breakout_volume_confirmation',  # Activar/desactivar
    'liquidity_sweep',
    # ... resto de estrategias
]
```

### 2. Risk Parameters

Editar configuración de risk manager:

```python
risk_config = {
    'max_total_exposure_pct': 6.0,     # Máximo 6% exposición total
    'max_per_symbol_exposure_pct': 2.0, # Máximo 2% por símbolo
    'min_quality_score': 0.65,          # Mínimo 65% calidad señal
    'base_risk_pct': 0.5,               # Base 0.5% por trade
}
```

### 3. ML Training

Entrenar modelos con histórico:

```bash
python3 scripts/train_ml_models.py
```

---

## TROUBLESHOOTING

### Error: "MT5 initialization failed"
```bash
# Windows: Reiniciar MT5
# Linux: Verificar Wine
wine --version
```

### Error: "Database connection failed"

**WINDOWS:**
```powershell
# Verificar PostgreSQL service
Get-Service -Name "postgresql*"
Start-Service "postgresql-x64-14"  # Ajustar versión

# Test connection
psql -U trading_user -d trading_system -c "SELECT 1;"
```

**LINUX:**
```bash
# Verificar PostgreSQL
sudo systemctl status postgresql
sudo systemctl start postgresql

# Test connection
psql -U trading_user -d trading_system -c "SELECT 1;"
```

### Error: "Module not found"
```bash
# Reinstalar dependencias
pip install -r requirements.txt --force-reinstall

# Verificar PYTHONPATH
echo $PYTHONPATH
```

### Engine crashes repetidamente

**WINDOWS:**
```powershell
# Ver logs
Get-Content logs\trading_$(Get-Date -Format "yyyyMMdd").log | Select-String "ERROR"

# Re-ejecutar pre-flight check
python scripts/pre_flight_check.py
```

**LINUX:**
```bash
# Ver logs
cat logs/trading_$(date +%Y%m%d).log | grep ERROR

# Re-ejecutar pre-flight check
python3 scripts/pre_flight_check.py
```

---

## SAFETY CHECKLIST ANTES DE LIVE TRADING

- [ ] ✅ Pre-flight check passed
- [ ] ✅ Database funcional
- [ ] ✅ MT5 conectado
- [ ] ✅ Cuenta tiene balance suficiente
- [ ] ✅ Risk limits configurados correctamente
- [ ] ✅ Logs monitoreados
- [ ] ✅ Backtests realizados
- [ ] ✅ Paper trading exitoso (demo)

---

## COMANDOS ÚTILES

**WINDOWS (PowerShell):**
```powershell
# Ver estrategias activas
Select-String -Path "scripts\live_trading_engine*.py" -Pattern "STRATEGY_WHITELIST"

# Ver posiciones abiertas
python -c "import MetaTrader5 as mt5; mt5.initialize(); print(mt5.positions_get())"

# Limpiar logs antiguos (>30 días)
Get-ChildItem logs\*.log | Where-Object {$_.LastWriteTime -lt (Get-Date).AddDays(-30)} | Remove-Item

# Backup database
pg_dump -U trading_user trading_system > backup_$(Get-Date -Format "yyyyMMdd").sql

# Stop trading (gracefully)
Get-Process python | Where-Object {$_.CommandLine -like "*live_trading_engine*"} | Stop-Process
```

**LINUX (Bash):**
```bash
# Ver estrategias activas
grep "STRATEGY_WHITELIST" scripts/live_trading_engine*.py

# Ver posiciones abiertas
python3 -c "import MetaTrader5 as mt5; mt5.initialize(); print(mt5.positions_get())"

# Limpiar logs antiguos (>30 días)
find logs -name "*.log" -mtime +30 -delete

# Backup database
pg_dump -U trading_user trading_system > backup_$(date +%Y%m%d).sql

# Stop trading (gracefully)
pkill -SIGINT -f live_trading_engine
```

---

## SOPORTE

**Bugs encontrados**: Reportar en GitHub Issues
**Documentación**: Ver /docs/
**Logs**: /logs/

**Sistema verificado y listo para producción ✅**
