# 🚀 GUÍA COMPLETA DE DEPLOYMENT A VPS

## ✅ RESPUESTA DIRECTA: ¿Necesito copiar/pegar archivos manualmente?

**NO.** Hay 3 opciones (ordenadas por facilidad):

1. **GIT CLONE** (MEJOR) - 1 comando, todo automático ⭐
2. **SCRIPT AUTOMÁTICO** - Descarga y ejecuta script de deployment
3. **TRANSFER PACKAGE** - ZIP con todo incluido (si no tienes git)

---

## 🎯 OPCIÓN 1: GIT CLONE (RECOMENDADA)

### **Ventajas:**
- ✅ 1 solo comando
- ✅ Futuras actualizaciones con `git pull`
- ✅ NO necesitas copiar archivos manualmente
- ✅ Historial completo de commits

### **Pasos:**

#### **En tu VPS (via SSH):**

```bash
# 1. Conectar a VPS
ssh user@your-vps-ip

# 2. Clonar repositorio
git clone https://github.com/YOUR_USERNAME/TradingSystem.git
cd TradingSystem

# 3. Instalar dependencias
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Crear directorios necesarios
mkdir -p logs reports backtest_reports ml_data trade_history

# 5. Configurar credenciales MT5
nano config/mt5_credentials.yaml
# (copiar tus credenciales)

# 6. LISTO - Ejecutar
python main.py --mode backtest --days 90
```

**Tiempo total: 5-10 minutos**

---

## 🎯 OPCIÓN 2: SCRIPT AUTOMÁTICO DE DEPLOYMENT

### **Ventajas:**
- ✅ Instala TODO automáticamente (Python, dependencias, MT5, etc.)
- ✅ Configura servicio systemd (auto-inicio)
- ✅ Verifica instalación completa
- ✅ UN SOLO COMANDO

### **Paso único:**

```bash
# En tu VPS, ejecuta:
bash <(curl -s https://raw.githubusercontent.com/YOUR_REPO/TradingSystem/main/deploy_to_vps.sh)
```

**O si prefieres descargarlo primero:**

```bash
wget https://raw.githubusercontent.com/YOUR_REPO/TradingSystem/main/deploy_to_vps.sh
chmod +x deploy_to_vps.sh
./deploy_to_vps.sh
```

**El script automáticamente:**
1. ✓ Verifica/instala Python 3
2. ✓ Verifica/instala Git
3. ✓ Clona el repositorio
4. ✓ Crea virtual environment
5. ✓ Instala todas las dependencias
6. ✓ Crea directorios necesarios
7. ✓ Instala Wine (para MT5 en Linux)
8. ✓ Opcionalmente configura systemd service
9. ✓ Verifica que todo funcione

**Tiempo total: 10-15 minutos (todo automático)**

---

## 🎯 OPCIÓN 3: TRANSFER PACKAGE (Sin Git)

### **Cuándo usar:**
- ❌ Tu VPS no tiene acceso a internet
- ❌ No puedes usar git por restricciones
- ✅ Quieres tener control total del deployment

### **Pasos:**

#### **En tu máquina local:**

```bash
cd TradingSystem

# Crear package con todo incluido
python generate_transfer_package.py
# Genera: trading_system_transfer_YYYYMMDD.tar.gz
```

#### **Transferir a VPS:**

```bash
# Opción 1: SCP
scp trading_system_transfer_20250111.tar.gz user@vps-ip:/home/user/

# Opción 2: SFTP
sftp user@vps-ip
put trading_system_transfer_20250111.tar.gz
```

#### **En VPS:**

```bash
# Extraer
tar -xzf trading_system_transfer_20250111.tar.gz
cd TradingSystem

# Instalar dependencias
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Ejecutar
python main.py --mode backtest --days 90
```

**Tiempo total: 15-20 minutos**

---

## 📋 PREREQUISITOS DEL VPS

### **Mínimo requerido:**

| Componente | Mínimo | Recomendado |
|------------|--------|-------------|
| **OS** | Ubuntu 20.04+ | Ubuntu 22.04 LTS |
| **CPU** | 2 cores | 4 cores |
| **RAM** | 4 GB | 8 GB |
| **Disco** | 20 GB | 50 GB SSD |
| **Python** | 3.8+ | 3.10+ |
| **Internet** | 10 Mbps | 50+ Mbps |

### **Software necesario:**

```bash
# Verificar instalado
python3 --version  # >= 3.8
git --version      # cualquier versión
pip3 --version     # cualquier versión

# Si falta algo:
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git
```

---

## 🔧 CONFIGURACIÓN POST-DEPLOYMENT

### **1. Credenciales MT5**

```bash
cd TradingSystem
nano config/mt5_credentials.yaml
```

**Contenido:**
```yaml
mt5:
  login: 12345678        # Tu login MT5
  password: "tu_pass"    # Tu contraseña
  server: "Broker-Server"  # Servidor del broker
  path: "/home/user/.wine/drive_c/Program Files/MetaTrader 5/terminal64.exe"
```

### **2. Configuración del Sistema**

```bash
nano config/system_config.yaml
```

**Verificar:**
- `risk.max_risk_per_trade: 0.01` (1% riesgo)
- `ml.enabled: true` ✓
- `ml_supervisor.enabled: true` ✓
- Symbols a operar

### **3. Configuración de Estrategias**

```bash
nano config/strategies_institutional.yaml
```

**IMPORTANTE:** Deshabilita estrategias que no quieras usar:

```yaml
spoofing_detection_l2:
  enabled: false  # Si no tienes L2 data

nfp_news_event_handler:
  enabled: true   # Mantén activas las que quieras
```

---

## 🎬 STARTUP AUTOMÁTICO (Systemd)

### **Crear servicio:**

```bash
sudo nano /etc/systemd/system/elite-trading.service
```

**Contenido:**
```ini
[Unit]
Description=Elite Trading System
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/home/your_user/TradingSystem
ExecStart=/home/your_user/TradingSystem/venv/bin/python /home/your_user/TradingSystem/main.py --mode paper
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### **Activar servicio:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable elite-trading
sudo systemctl start elite-trading

# Verificar status
sudo systemctl status elite-trading

# Ver logs en tiempo real
sudo journalctl -u elite-trading -f
```

### **Comandos útiles:**

```bash
# Iniciar
sudo systemctl start elite-trading

# Detener
sudo systemctl stop elite-trading

# Reiniciar
sudo systemctl restart elite-trading

# Ver logs
sudo journalctl -u elite-trading -n 100  # Últimas 100 líneas
sudo journalctl -u elite-trading -f      # Seguir en tiempo real
```

---

## 📊 VALIDACIÓN POST-DEPLOYMENT

### **1. Verificar instalación:**

```bash
cd TradingSystem
source venv/bin/activate
python -c "
import pandas
import numpy
import yaml
from src.core.brain import InstitutionalBrain
from src.core.ml_supervisor import MLSupervisor
print('✓ All imports successful')
"
```

Si imprime "✓ All imports successful" → BIEN

### **2. Ejecutar backtest de prueba:**

```bash
python main.py --mode backtest --days 30
```

**Verificar output:**
```
================================================================================
ELITE INSTITUTIONAL TRADING SYSTEM V2.0 - INITIALIZING
================================================================================
✓ Configuration loaded from config/system_config.yaml
✓ Risk Manager initialized
✓ Position Manager initialized
✓ Regime Detector initialized
✓ Multi-Timeframe Manager initialized
✓✓ ML Adaptive Engine ENABLED (auto-learning active)
✓ Institutional Brain initialized
✓ Strategy Orchestrator initialized (24 strategies)
✓ Institutional Reporting System initialized
✓✓ ML Supervisor ENABLED (autonomous decision-making active)
================================================================================
SYSTEM INITIALIZATION COMPLETE - FULLY AUTONOMOUS
================================================================================
```

Si ves este output → **TODO CORRECTO** ✅

### **3. Verificar directorios creados:**

```bash
ls -la
```

Debes ver:
```
drwxr-xr-x  logs/
drwxr-xr-x  reports/
drwxr-xr-x  backtest_reports/
drwxr-xr-x  ml_data/
drwxr-xr-x  trade_history/
drwxr-xr-x  config/
```

---

## 🔍 TROUBLESHOOTING

### **Error: "ModuleNotFoundError: No module named 'MetaTrader5'"**

```bash
source venv/bin/activate
pip install MetaTrader5
```

### **Error: "MT5 initialization failed"**

**Causa:** MT5 no instalado o credenciales incorrectas

**Solución:**
```bash
# Verificar credenciales
cat config/mt5_credentials.yaml

# Instalar MT5 en Linux (via Wine)
sudo dpkg --add-architecture i386
sudo apt-get update
sudo apt-get install wine wine32 wine64

# Descargar MT5
wget https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe
wine mt5setup.exe
```

### **Error: "Permission denied" en logs/**

```bash
chmod -R 755 logs/ reports/ backtest_reports/ ml_data/ trade_history/
```

### **Sistema se detiene después de unos minutos**

**Causa:** No está configurado como servicio systemd

**Solución:** Ver sección "STARTUP AUTOMÁTICO" arriba

### **Los reportes no se generan**

**Verificar:**
```bash
# ¿Hay trades cerrados?
ls -la trade_history/

# ¿Está configurado reporting?
grep "generate_daily" config/system_config.yaml
```

---

## 📈 MONITOREO POST-DEPLOYMENT

### **1. Logs en tiempo real:**

```bash
# Sistema completo
tail -f logs/trading_system.log

# Solo trades
grep "Position opened\|Position closed" logs/trading_system.log | tail -20

# Solo ML Supervisor
grep "ML SUPERVISOR\|AUTO-DISABLING" logs/trading_system.log | tail -20
```

### **2. Revisar reportes:**

```bash
# Último reporte diario
cat reports/daily_$(date +%Y%m%d).json | jq .

# Último reporte semanal
ls -t reports/weekly_*.json | head -1 | xargs cat | jq .

# Último backtest
ls -t backtest_reports/analysis_*.json | head -1 | xargs cat | jq .
```

### **3. Monitorear ML Supervisor:**

```bash
# Ver estrategias deshabilitadas
grep "AUTO-DISABLING" logs/trading_system.log

# Ver circuit breakers
grep "CIRCUIT BREAKER" logs/trading_system.log

# Ver optimizaciones ML aplicadas
grep "APPLYING ML PARAMETER" logs/trading_system.log
```

---

## 🔄 ACTUALIZACIONES FUTURAS

### **Con Git (recomendado):**

```bash
cd TradingSystem
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Reiniciar servicio
sudo systemctl restart elite-trading
```

### **Sin Git:**

1. Generar nuevo transfer package localmente
2. Transferir a VPS
3. Backup directorios importantes:
```bash
cp -r ml_data ml_data_backup
cp -r trade_history trade_history_backup
```
4. Extraer nuevo package
5. Restaurar datos:
```bash
cp -r ml_data_backup/* ml_data/
cp -r trade_history_backup/* trade_history/
```

---

## 🎯 CHECKLIST COMPLETO DE DEPLOYMENT

Marca cada paso cuando lo completes:

### **Pre-Deployment**
- [ ] VPS contratado (mínimo 4GB RAM, 2 cores)
- [ ] Ubuntu 20.04+ instalado
- [ ] SSH access configurado
- [ ] Python 3.8+ instalado
- [ ] Git instalado (si usas Opción 1 o 2)

### **Deployment**
- [ ] Código transferido a VPS (git clone / script / package)
- [ ] Virtual environment creado
- [ ] Dependencias instaladas (`pip install -r requirements.txt`)
- [ ] Directorios creados (logs/, reports/, etc.)
- [ ] MT5 instalado y configurado
- [ ] Credenciales MT5 configuradas
- [ ] system_config.yaml revisado
- [ ] strategies_institutional.yaml revisado

### **Validación**
- [ ] Test de imports exitoso
- [ ] Backtest de prueba ejecutado (30-90 días)
- [ ] Logs sin errores críticos
- [ ] Reportes generándose correctamente

### **Production Setup**
- [ ] Systemd service configurado (opcional)
- [ ] Auto-start habilitado
- [ ] Monitoreo configurado (logs, reportes)
- [ ] Backup automático configurado

### **Post-Deployment**
- [ ] Paper trading corriendo 3-6 meses
- [ ] Reportes mensuales revisados
- [ ] ML Supervisor funcionando (auto-disable, optimizaciones)
- [ ] Performance matches backtest (±20%)

---

## 📞 SOPORTE

### **Logs importantes para debugging:**

```bash
# Inicialización
grep "INITIALIZING\|COMPLETE" logs/trading_system.log

# Errores
grep "ERROR\|CRITICAL" logs/trading_system.log | tail -50

# ML Supervisor actions
grep "AUTO-DISABLING\|CIRCUIT BREAKER\|APPLYING ML" logs/trading_system.log

# Trades
grep "Position opened\|Position closed" logs/trading_system.log | tail -20
```

---

## ✅ RESUMEN EJECUTIVO

### **Opción 1 (GIT - MEJOR):**
```bash
git clone https://github.com/YOUR_REPO/TradingSystem.git
cd TradingSystem
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
mkdir -p logs reports backtest_reports ml_data trade_history
# Configurar credenciales
python main.py --mode backtest --days 90
```
**Tiempo: 5-10 minutos**

### **Opción 2 (SCRIPT AUTOMÁTICO):**
```bash
bash <(curl -s https://raw.githubusercontent.com/YOUR_REPO/TradingSystem/main/deploy_to_vps.sh)
```
**Tiempo: 10-15 minutos (automático)**

### **Opción 3 (TRANSFER PACKAGE):**
1. Generar ZIP localmente
2. Transferir a VPS
3. Extraer y setup
**Tiempo: 15-20 minutos**

---

**TODO el sistema se activa automáticamente al ejecutar `python main.py`**

**NO necesitas intervención manual después del deployment.** 🎯
