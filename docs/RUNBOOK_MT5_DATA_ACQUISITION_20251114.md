# RUNBOOK - MT5 DATA ACQUISITION

**MANDATO 20 - Data Pipeline Institucional**

**Propósito**: Guía operativa paso-a-paso para configurar y ejecutar descarga de datos REALES desde MetaTrader 5 en Windows VPS.

**Audiencia**: DevOps, Quant Team, cualquier persona que necesite obtener datos históricos REALES.

**Tiempo estimado**: 30-60 minutos (setup inicial)

---

## PRE-REQUISITOS

### Hardware

- ✅ **Windows machine** (VPS, VM, o local)
  - Windows Server 2016+ (recomendado)
  - O Windows 10/11 (para desarrollo)
- ✅ **CPU**: 2+ cores
- ✅ **RAM**: 4+ GB
- ✅ **Disk**: 10+ GB libre (datos históricos ~100 MB, MT5 terminal ~500 MB)
- ✅ **Network**: Stable internet connection

### Software

- ✅ **MetaTrader 5 Terminal** (descarga gratis desde broker)
- ✅ **Python 3.8+** (recomendado 3.10+)
- ✅ **Git** (para clonar repositorio)

### Accounts & Credentials

- ✅ **MT5 Account** (demo OK para testing, real para producción)
  - Login number
  - Password
  - Server name (ej: "ICMarkets-Demo", "Pepperstone-Live")
- ✅ **Git access** al repositorio TradingSystem

---

## FASE 0: PREPARACIÓN DE ENTORNO

### Paso 0.1: Conectar a Windows VPS

**Opción A - RDP** (Remote Desktop Protocol):

```bash
# Desde Linux/Mac
rdesktop -u Administrator -p PASSWORD VPS_IP:3389

# Desde Windows
mstsc.exe  # Abrir Remote Desktop Connection
# Ingresar: VPS_IP, username, password
```

**Opción B - VPS Provider Dashboard**:
- AWS EC2: Session Manager o RDP
- Azure: Bastion o RDP
- DigitalOcean: Console Access o RDP

### Paso 0.2: Verificar Windows Version

```cmd
# Abrir PowerShell o CMD
winver
```

**Expected**: Windows Server 2016+, Windows 10 Build 1803+, o Windows 11

### Paso 0.3: Instalar Python

**Si Python NO está instalado**:

1. Descargar: https://www.python.org/downloads/
2. Ejecutar instalador
3. ✅ **IMPORTANTE**: Check "Add Python to PATH"
4. Completar instalación

**Verificar**:

```cmd
python --version
# Expected: Python 3.8.x or higher
```

### Paso 0.4: Instalar Git

**Si Git NO está instalado**:

1. Descargar: https://git-scm.com/download/win
2. Ejecutar instalador (default options OK)
3. Completar instalación

**Verificar**:

```cmd
git --version
# Expected: git version 2.x.x
```

---

## FASE 1: INSTALAR Y CONFIGURAR MT5 TERMINAL

### Paso 1.1: Descargar MT5 Terminal

**Desde broker**:
- ICMarkets: https://www.icmarkets.com/global/en/trading-platforms/metatrader-5
- Pepperstone: https://pepperstone.com/en/trading-platforms/metatrader-5
- XM: https://www.xm.com/metatrader-5
- (O tu broker preferido)

**Alternativa - Download directo**:
- https://www.metatrader5.com/en/download

### Paso 1.2: Instalar MT5 Terminal

1. Ejecutar instalador `mt5setup.exe`
2. Aceptar Terms & Conditions
3. Completar instalación (default directory OK)
4. Launch MT5 terminal

### Paso 1.3: Crear/Configurar Cuenta MT5

**Opción A - Nueva cuenta demo** (recomendado para testing):

1. En MT5 terminal: File → Open an Account
2. Seleccionar broker server (ej: "ICMarkets-Demo")
3. Fill form: Name, Email, Phone
4. Seleccionar: **"Demo Account"**
5. Configurar: Balance (ej: $100,000), Leverage (ej: 1:500)
6. Submit
7. **ANOTAR**: Login, Password, Server

**Opción B - Cuenta real existente**:

1. En MT5 terminal: File → Login to Trade Account
2. Ingresar: Login, Password
3. Seleccionar: Server
4. Connect

### Paso 1.4: Verificar Conexión

**En MT5 terminal**:
- Bottom-right corner: Debería decir **"Connected"** con ping (ej: "254ms")
- Si dice "No connection", troubleshoot:
  - Check internet connection
  - Check firewall (allow `terminal64.exe`)
  - Verify server name, credentials

### Paso 1.5: Habilitar Auto-Trading

**CRÍTICO para que Python pueda conectar**:

1. En MT5 terminal: Tools → Options
2. Tab: Expert Advisors
3. ✅ Check: **"Allow automated trading"**
4. ✅ Check: **"Allow DLL imports"** (optional, pero recomendado)
5. Click OK

### Paso 1.6: Agregar Símbolos a Market Watch

**Símbolos mínimos (MANDATO 19)**:
- EURUSD
- XAUUSD (Gold)
- US500 (S&P 500)

**Cómo agregar**:
1. En MT5 terminal: View → Market Watch (o Ctrl+M)
2. Right-click en Market Watch → Symbols
3. Search: "EURUSD" → Select → Show
4. Repeat para XAUUSD, US500
5. Close Symbols window

**Verificar**:
- Market Watch debería mostrar precios live para EURUSD, XAUUSD, US500

---

## FASE 2: CLONAR Y CONFIGURAR REPOSITORIO

### Paso 2.1: Clonar Repositorio

**Abrir PowerShell o Git Bash**:

```bash
# Navegar a directorio de proyectos (ej: C:\Projects\)
cd C:\Projects

# Clonar repositorio
git clone https://github.com/sublimine/TradingSystem.git
cd TradingSystem

# Checkout branch MANDATO 20 (si todavía no mergeado a main)
git checkout claude/mandato20-data-pipeline-01AqipubodvYuyNtfLsBZpsx
```

**Verificar**:

```bash
ls
# Should see: src/, scripts/, config/, data/, docs/, etc.
```

### Paso 2.2: Crear Virtual Environment (Recomendado)

```bash
# Crear venv
python -m venv venv

# Activar venv
# PowerShell:
.\venv\Scripts\Activate.ps1

# CMD:
.\venv\Scripts\activate.bat

# Verificar
which python  # Should point to venv\Scripts\python.exe
```

### Paso 2.3: Instalar Dependencies

```bash
# Actualizar pip
python -m pip install --upgrade pip

# Instalar dependencies
pip install -r requirements.txt

# CRÍTICO: Instalar MetaTrader5
pip install MetaTrader5

# Opcional: python-dotenv para .env management
pip install python-dotenv
```

**Verificar instalación MT5**:

```bash
python -c "import MetaTrader5 as mt5; print(f'MT5 version: {mt5.__version__}')"
# Expected: MT5 version: 5.0.xxxx
```

### Paso 2.4: Configurar Credenciales (.env)

**Crear archivo `.env`** en root del repositorio:

```bash
# PowerShell
notepad .env
```

**Contenido de `.env`**:

```bash
# MT5 Credentials (NEVER commit to Git)
MT5_LOGIN=12345678
MT5_PASSWORD=YourSecurePassword123!
MT5_SERVER=ICMarkets-Demo

# Optional: Logging
LOG_LEVEL=INFO
```

**IMPORTANTE**:
- Reemplazar `12345678` con tu login real
- Reemplazar `YourSecurePassword123!` con tu password real
- Reemplazar `ICMarkets-Demo` con tu server real

**Verificar que `.env` está gitignored**:

```bash
cat .gitignore | grep ".env"
# Should output: .env (o *.env)
```

### Paso 2.5: Verificar Estructura de Directorios

```bash
# Verificar que REAL/ directory existe
ls data/historical/REAL/
# Should be empty (ready for downloads)
```

---

## FASE 3: PROBAR CONEXIÓN MT5

### Paso 3.1: Smoke Test - Connection Check

```bash
python scripts/download_mt5_history.py --check-connection
```

**Expected output (SUCCESS)**:

```
================================================================================
MANDATO 20 - MT5 CONNECTION CHECK
================================================================================
INFO: Checking MT5 connection...
INFO: ✅ MT5 connected: ICMarkets-Demo | Login: 12345678
INFO:    Balance: 100000.0 USD
INFO:    Leverage: 1:500
================================================================================
✅ MT5 CONNECTION OK
================================================================================
```

**Si falla, troubleshoot**:

1. **MT5 terminal NO está corriendo**:
   - Lanzar MT5 terminal
   - Verificar que está logged in (bottom-right: "Connected")

2. **Auto-trading disabled**:
   - MT5: Tools → Options → Expert Advisors
   - ✅ Check "Allow automated trading"

3. **Credenciales incorrectas en `.env`**:
   - Verificar login, password, server
   - Re-ingresar credenciales en MT5 terminal

4. **Firewall blocking**:
   - Windows Defender Firewall: Allow `terminal64.exe`
   - Allow Python connections

5. **MT5 module not installed**:
   ```bash
   pip install MetaTrader5
   ```

---

## FASE 4: DESCARGA INICIAL DE DATOS

### Paso 4.1: Download Mínimo Scope (MANDATO 19)

**Símbolos**: EURUSD, XAUUSD, US500
**Timeframe**: M15 (15 minutos)
**Period**: 2023-01-01 → 2024-12-31 (24 meses)

```bash
python scripts/download_mt5_history.py \
  --symbols EURUSD,XAUUSD,US500 \
  --timeframe M15 \
  --start 2023-01-01 \
  --end 2024-12-31 \
  --dest data/historical/REAL
```

**Expected output**:

```
================================================================================
MANDATO 20 - MT5 HISTORICAL DATA DOWNLOAD (REAL)
================================================================================
Symbols: ['EURUSD', 'XAUUSD', 'US500']
Timeframe: M15
Period: 2023-01-01 to 2024-12-31
Destination: data/historical/REAL
================================================================================

[EURUSD] Downloading M15 data...
Validating data quality for EURUSD M15...
  ✅ Data quality OK - no issues found
✅ [EURUSD] Downloaded 35040 bars → data/historical/REAL/REAL_EURUSD_M15.csv

[XAUUSD] Downloading M15 data...
Validating data quality for XAUUSD M15...
  ✅ Data quality OK - no issues found
✅ [XAUUSD] Downloaded 35040 bars → data/historical/REAL/REAL_XAUUSD_M15.csv

[US500] Downloading M15 data...
Validating data quality for US500 M15...
  ✅ Data quality OK - no issues found
✅ [US500] Downloaded 35040 bars → data/historical/REAL/REAL_US500_M15.csv

================================================================================
DOWNLOAD SUMMARY
================================================================================
✅ SUCCESS: 3 symbols
   EURUSD: 35040 bars → data/historical/REAL/REAL_EURUSD_M15.csv
   XAUUSD: 35040 bars → data/historical/REAL/REAL_XAUUSD_M15.csv
   US500: 35040 bars → data/historical/REAL/REAL_US500_M15.csv
================================================================================
All downloads completed successfully
```

**Tiempo estimado**: 30-90 segundos (depende de broker server)

### Paso 4.2: Verificar Archivos CSV

```bash
# Listar archivos
ls -lh data/historical/REAL/

# Expected output:
# REAL_EURUSD_M15.csv  (~3 MB)
# REAL_XAUUSD_M15.csv  (~3 MB)
# REAL_US500_M15.csv   (~3 MB)
```

### Paso 4.3: Spot-Check Data Quality

**Abrir CSV en Excel/Notepad** (verificación manual):

```bash
# Windows
notepad data/historical/REAL/REAL_EURUSD_M15.csv
```

**Verificar**:
- ✅ Header row: `timestamp,open,high,low,close,volume`
- ✅ First data row: `2023-01-02 00:00:00+00:00,1.06720,...`
- ✅ No NaN values
- ✅ High >= Low
- ✅ Dates sorted ascending

**Programmatic check** (Python):

```python
import pandas as pd

df = pd.read_csv('data/historical/REAL/REAL_EURUSD_M15.csv', index_col=0, parse_dates=True)

print(f"Shape: {df.shape}")  # Expected: (~35000, 5)
print(f"Date range: {df.index[0]} to {df.index[-1]}")
print(f"NaNs: {df.isnull().sum().sum()}")  # Expected: 0
print(f"High >= Low: {(df['high'] >= df['low']).all()}")  # Expected: True
```

---

## FASE 5: DESCARGA COMPLETA (OPCIONAL)

### Paso 5.1: Download Full Universe (15 símbolos)

**Si quieres ejecutar calibración completa (MANDATO 19 full)**:

```bash
python scripts/download_mt5_history.py \
  --symbols EURUSD,GBPUSD,USDJPY,AUDUSD,NZDUSD,USDCHF,USDCAD,EURJPY,GBPJPY,US500,NAS100,DE40,XAUUSD,XTIUSD,BTCUSD \
  --timeframe M15 \
  --start 2023-01-01 \
  --end 2024-12-31 \
  --dest data/historical/REAL
```

**Tiempo estimado**: 5-10 minutos (15 símbolos)

**Output**: 15 CSV files (~45 MB total)

### Paso 5.2: Extender Historia (5 años - Opcional)

**Si quieres más datos históricos**:

```bash
python scripts/download_mt5_history.py \
  --symbols EURUSD,XAUUSD,US500 \
  --timeframe M15 \
  --start 2020-01-01 \
  --end 2024-12-31 \
  --dest data/historical/REAL
```

**Nota**: Broker puede no tener datos tan antiguos (depende del broker).

---

## FASE 6: INTEGRACIÓN CON CALIBRACIÓN (MANDATO 19)

### Paso 6.1: Verificar Calibration Config

**Editar** `config/backtest_calibration_20251114.yaml`:

```yaml
data_settings:
  data_dir: "data/historical/REAL"  # <-- Usar REAL data (no synthetic)
  timeframe: "M15"
```

**Verificar que apunta a `REAL/`**, no a `data/historical/`.

### Paso 6.2: Run Calibration Sweep (Smoke Test)

**Ejecutar calibración de 1 estrategia (rápido)**:

```bash
python scripts/run_calibration_sweep.py --strategy liquidity_sweep
```

**Si todo está bien**:
- Debería cargar datos desde `data/historical/REAL/`
- Ejecutar backtest con datos REALES
- Generar reportes en `reports/calibration/`

**Si falla**:
- Check logs para errores
- Verificar que CSV files existen en `data/historical/REAL/`
- Verificar que BacktestDataLoader encuentra los archivos

### Paso 6.3: Run Full Calibration (MANDATO 19)

**Cuando esté listo para calibración completa**:

```bash
# Calibrar todas las estrategias
python scripts/run_calibration_sweep.py

# Calibrar brain-layer
python scripts/train_brain_policies_calibrated.py

# Hold-out validation
python scripts/run_calibration_holdout.py
```

**Output**: Reportes en `reports/` con métricas REALES.

---

## FASE 7: MANTENIMIENTO Y ACTUALIZACIONES

### Paso 7.1: Actualizar Datos (Incremental)

**Scenario**: Ya tienes datos 2023-2024, ahora quieres agregar 2025.

**Opción A - Re-download completo** (sobrescribe):

```bash
python scripts/download_mt5_history.py \
  --symbols EURUSD,XAUUSD,US500 \
  --timeframe M15 \
  --start 2023-01-01 \
  --end 2025-12-31 \
  --dest data/historical/REAL
```

**Opción B - Download solo 2025** (manual merge):

```bash
# Download 2025
python scripts/download_mt5_history.py \
  --symbols EURUSD \
  --timeframe M15 \
  --start 2025-01-01 \
  --end 2025-12-31 \
  --dest data/historical/REAL_2025

# Merge CSV files (Python script)
python scripts/merge_market_data.py \
  data/historical/REAL/REAL_EURUSD_M15.csv \
  data/historical/REAL_2025/REAL_EURUSD_M15.csv \
  --output data/historical/REAL/REAL_EURUSD_M15.csv
```

**Future enhancement**: Auto-incremental update script (MANDATO futuro).

### Paso 7.2: Backup de Datos

**Antes de re-download o updates importantes**:

```bash
# PowerShell
$date = Get-Date -Format "yyyyMMdd"
Copy-Item -Recurse data/historical/REAL data/historical/REAL_backup_$date
```

**Verificar backup**:

```bash
ls data/historical/
# Should see: REAL/, REAL_backup_20251114/, etc.
```

### Paso 7.3: Monitoreo de Calidad

**Periódicamente verificar calidad de datos**:

```python
# Script de monitoreo (crear si no existe)
python scripts/validate_market_data.py data/historical/REAL/

# Output esperado:
# ✅ REAL_EURUSD_M15.csv: OK (35040 bars, 0 issues)
# ✅ REAL_XAUUSD_M15.csv: OK (35040 bars, 0 issues)
# ⚠️  REAL_US500_M15.csv: WARNING (3 outliers detected)
```

---

## TROUBLESHOOTING

### Error: "MT5 NOT AVAILABLE"

**Mensaje**:
```
CRITICAL: MT5 NOT AVAILABLE: MetaTrader5 module not installed
```

**Solución**:
```bash
pip install MetaTrader5
```

**Si persiste**:
- Verificar que estás en Windows (MT5 module solo Windows)
- Verificar Python version (3.8+)
- Re-instalar: `pip uninstall MetaTrader5 && pip install MetaTrader5`

---

### Error: "MT5 CONNECTION FAILED"

**Mensaje**:
```
ERROR: MT5 connection failed
```

**Checklist**:
1. ✅ MT5 terminal está **corriendo** (Task Manager: `terminal64.exe` presente)
2. ✅ MT5 terminal está **logged in** (bottom-right: "Connected")
3. ✅ Auto-trading **habilitado** (Tools → Options → Expert Advisors)
4. ✅ Credenciales **correctas** en `.env`
5. ✅ Firewall **permite** MT5 connections

**Debugging**:

```python
import MetaTrader5 as mt5

# Test manual
if not mt5.initialize():
    print(f"Error: {mt5.last_error()}")
else:
    print("✅ Connected")
    account = mt5.account_info()
    print(f"Server: {account.server}, Login: {account.login}")
    mt5.shutdown()
```

**Common errors**:
- `(1, 'Terminal: no IPC')`: MT5 terminal no está corriendo
- `(2, 'Terminal: wrong account')`: Credenciales incorrectas
- `(10004, 'Terminal: invalid account')`: Account no existe

---

### Error: "Symbol '...' does not exist"

**Mensaje**:
```
ValueError: Symbol 'EURUSD' does not exist on MT5 server
```

**Root cause**: Symbol name incorrecto (broker-specific).

**Solución**:

1. **Check symbol names en MT5 terminal**:
   - Market Watch → Right-click → Symbols
   - Search for EUR
   - Note exact name (could be "EURUSD", "EURUSDm", "EURUSD.pro", etc.)

2. **List all symbols via Python**:

```python
import MetaTrader5 as mt5

mt5.initialize()
symbols = mt5.symbols_get()
print([s.name for s in symbols if 'EUR' in s.name])
mt5.shutdown()
```

3. **Use correct name en download script**:

```bash
python scripts/download_mt5_history.py --symbols EURUSD.pro,XAUUSD,US500 ...
```

---

### Error: "No data returned"

**Mensaje**:
```
RuntimeError: No data returned from MT5 for EURUSD M15
```

**Possible causes**:

1. **Date range invalid**:
   - Start date in future
   - End date before start date
   - Only weekends in range (no trading)

2. **Broker no tiene historia**:
   - Algunos brokers tienen historia limitada (ej: solo 1 año)

3. **Symbol no tiene datos para ese período**:
   - Symbol nuevo (ej: crypto recién listado)

**Solución**:

1. **Verificar date range**:
   ```bash
   --start 2023-01-01 --end 2024-12-31  # OK
   --start 2024-12-31 --end 2023-01-01  # WRONG (inverted)
   --start 2030-01-01 --end 2030-12-31  # WRONG (future)
   ```

2. **Try shorter range**:
   ```bash
   --start 2024-01-01 --end 2024-01-31  # 1 month only
   ```

3. **Check in MT5 terminal**:
   - Open chart para symbol (ej: EURUSD M15)
   - Verify que hay historia visible
   - Scroll back para verificar cuánto historial existe

---

### Warning: "Found X potential outlier bars"

**Mensaje**:
```
WARNING: Found 5 potential outlier bars (>50% price change)
WARNING: Review manually - NOT auto-removing (could be real flash crash)
```

**Root cause**: Price change >50% en una barra (podría ser real o error de datos).

**Acción**:

1. **Review logs**: Identificar qué barras son outliers
2. **Check chart en MT5**: Verificar si outlier es visible en chart
3. **Decidir**:
   - Si es **flash crash real** (visible en chart): Keep data
   - Si es **error de datos** (spike invisible en chart): Contact broker or re-download

**Note**: Data es usable (outliers NO se eliminan automáticamente).

---

### Warning: "Missing ~X% of data"

**Mensaje**:
```
WARNING: Data appears incomplete: expected ~40000 bars, got 35000
WARNING: Missing ~12.5% of data (weekends/holidays may account for some)
```

**Root cause**: Gaps en datos (normal para weekends/holidays).

**Expected missing %**:
- **FX**: ~30% missing (weekends, holidays)
- **Indices**: ~35% missing (16h/day, 5 days/week)
- **Crypto**: ~5% missing (24/7 trading, pocas pausas)

**Acción**:
- **<15% missing**: Normal, acceptable
- **>15% missing**: Investigate (broker issue? connection drops?)

**Note**: Data es usable (gaps NO son error fatal).

---

## SECURITY CHECKLIST

### Pre-Production Deployment

- [ ] **Credentials NOT hardcoded** (use `.env`)
- [ ] **`.env` in `.gitignore`** (verify: `cat .gitignore | grep .env`)
- [ ] **Demo account** para testing (NO real money)
- [ ] **Firewall rules** configured (allow MT5, Python)
- [ ] **VPS access** restricted (SSH keys, no password auth)
- [ ] **Backups** configured (data, code)

### Post-Deployment

- [ ] **Rotate credentials** después de setup inicial (best practice)
- [ ] **Monitor logs** para failed connections
- [ ] **Alert on failures** (email, Slack, etc.)
- [ ] **Regular audits** de data quality

---

## OPERATIONAL CHECKLIST

### Daily Operations

- [ ] Verificar MT5 terminal está **logged in**
- [ ] Verificar **connection status** (green, low ping)
- [ ] Run **incremental data update** (cuando esté automatizado)

### Weekly Operations

- [ ] **Backup** data directory
- [ ] **Review** data quality logs
- [ ] **Monitor** disk space (data directory)

### Monthly Operations

- [ ] **Update** dependencies (`pip install --upgrade -r requirements.txt`)
- [ ] **Review** MT5 terminal version (update si disponible)
- [ ] **Audit** credentials (rotate si necesario)

---

## AUTOMATION (FUTURE)

### Scheduled Downloads (Task Scheduler)

**Create task** para download diario automático:

1. Open **Task Scheduler** (Windows)
2. Create Basic Task
3. Trigger: Daily, 02:00 AM
4. Action: Start a program
   - Program: `C:\Projects\TradingSystem\venv\Scripts\python.exe`
   - Arguments: `scripts/update_market_data.py`
   - Start in: `C:\Projects\TradingSystem`
5. Save

**Script**: `scripts/update_market_data.py` (crear en MANDATO futuro)

### Email Alerts

**Configurar alertas** para failures:

```python
# scripts/update_market_data.py (pseudo-code)
try:
    download_data()
except Exception as e:
    send_email(
        to="team@sublimine.com",
        subject="MT5 Download FAILED",
        body=str(e)
    )
```

---

## REFERENCIAS

**Documentación Técnica**:
- `docs/DATA_PIPELINE_MANDATO20_*.md` - Arquitectura del pipeline
- `docs/MANDATO20_STATUS_*.md` - Status de implementación
- `data/historical/REAL/README.md` - Data conventions

**Scripts**:
- `scripts/download_mt5_history.py` - Download script principal
- `src/data_providers/mt5_data_client.py` - MT5 client class

**Configs**:
- `config/mt5_data_config.yaml` - MT5 configuration
- `.env` - Credentials (gitignored)

**External**:
- MetaTrader 5 Docs: https://www.mql5.com/en/docs/python_metatrader5
- MT5 Python Examples: https://www.mql5.com/en/docs/python_metatrader5/examples

---

## CONTACTO Y SOPORTE

**Issues con MT5 connection**:
- Check MT5 terminal logs: `File → Open Data Folder → Logs`
- Contact broker support
- Check MQL5 community forums

**Issues con Python script**:
- Review logs: Console output
- Check GitHub issues: https://github.com/sublimine/TradingSystem/issues
- Contact quant team

**Issues con datos (quality, gaps, etc.)**:
- Review validation logs
- Compare con broker charts
- Contact broker si data es claramente incorrecta

---

**RUNBOOK VERSION**: 1.0
**Last Updated**: 2025-11-14
**Mandato**: MANDATO 20
**Autor**: SUBLIMINE Institutional Trading System
