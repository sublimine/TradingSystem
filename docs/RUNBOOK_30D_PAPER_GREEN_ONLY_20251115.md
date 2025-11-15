# RUNBOOK: 30 DÍAS PAPER TRADING - GREEN ONLY PROFILE

**MANDATO**: MANDATO GAMMA - Production Hardening
**PERFIL**: runtime_profile_paper_GREEN_ONLY.yaml
**OBJETIVO**: Validar 5 estrategias GREEN COMPLETE durante 30 días continuos antes de LIVE
**AUTOR**: SUBLIMINE Institutional Trading System
**FECHA**: 2025-11-15

---

## 📋 ÍNDICE

1. [Pre-Launch Checklist](#1-pre-launch-checklist)
2. [Launch Procedure](#2-launch-procedure)
3. [Daily Monitoring](#3-daily-monitoring)
4. [Weekly Metrics Review](#4-weekly-metrics-review)
5. [STOP Criteria](#5-stop-criteria)
6. [Post-30D Evaluation](#6-post-30d-evaluation)
7. [Prerequisites for LIVE Activation](#7-prerequisites-for-live-activation)
8. [Emergency Procedures](#8-emergency-procedures)

---

## 1. PRE-LAUNCH CHECKLIST

**CRITICAL: Completar TODOS los items antes de iniciar 30 días PAPER.**

### 1.1 Validación de Configuración

```bash
# PASO 1: Validar runtime profiles
python scripts/validate_runtime_profiles.py
# EXPECTED: ✅ 3/3 profiles válidos - APROBADO para deployment

# PASO 2: Smoke test GREEN ONLY end-to-end
python scripts/smoke_test_green_only.py
# EXPECTED: ✅ SMOKE TEST PASSED - GREEN ONLY profile READY for 30-day PAPER

# PASO 3: Verificar NO ATR en risk/sizing/SL/TP
python scripts/check_no_atr_in_risk.py
# EXPECTED: ✅ ZERO ATR contamination en risk paths
```

**❌ ABORTAR si algún script retorna EXIT CODE ≠ 0**

### 1.2 Verificación Manual de Perfiles

```bash
# Verificar config activo
cat config/runtime_profile_paper_GREEN_ONLY.yaml | grep "execution_mode"
# EXPECTED: execution_mode: paper

cat config/runtime_profile_paper_GREEN_ONLY.yaml | grep "active_strategies" -A 6
# EXPECTED: Exactamente 5 GREEN COMPLETE strategies
```

**Estrategias PROHIBIDAS durante 30d PAPER:**
- ❌ HYBRID (6): fvg_institutional, idp_inducement_distribution, order_block_institutional, htf_ltf_liquidity, volatility_regime_adaptation, fractal_market_structure
- ❌ BROKEN (8): calendar_arbitrage_flows, correlation_cascade_detection, crisis_mode_volatility_spike, footprint_orderflow_clusters, nfp_news_event_handler, topological_data_analysis_regime, momentum_quality, vwap_reversion_extreme

**Estrategias PERMITIDAS (5 GREEN COMPLETE):**
- ✅ breakout_volume_confirmation
- ✅ liquidity_sweep
- ✅ ofi_refinement
- ✅ order_flow_toxicity
- ✅ vpin_reversal_extreme

### 1.3 Infraestructura

- [ ] **Servidor operativo** (uptime >99.9%)
- [ ] **MT5 Demo account** conectado y funcional
- [ ] **Disco**: >20GB libres para logs/backups
- [ ] **RAM**: >4GB disponibles
- [ ] **Logs directory**: `logs/` existe y tiene permisos escritura
- [ ] **Database**: SQLite operational (if used)

### 1.4 Comunicaciones

- [ ] **Email alerts** configurado (config: `alerts.email`)
- [ ] **Emergency contacts** actualizados (config: `emergency.contacts`)
- [ ] **Slack/Discord** webhook configurado (opcional)

### 1.5 Backup & Recovery

```bash
# Crear backup pre-launch
mkdir -p backups/pre_30d_paper_$(date +%Y%m%d)
cp -r config/ backups/pre_30d_paper_$(date +%Y%m%d)/
cp -r src/ backups/pre_30d_paper_$(date +%Y%m%d)/
```

---

## 2. LAUNCH PROCEDURE

### 2.1 Iniciar 30 Días PAPER

**Comando (ejecutar en screen/tmux para persistencia):**

```bash
# Opción 1: Screen (recomendado para producción)
screen -S sublimine_paper_30d
python main_institutional.py \
  --mode paper \
  --config config/runtime_profile_paper_GREEN_ONLY.yaml

# Opción 2: Tmux
tmux new -s sublimine_paper_30d
python main_institutional.py \
  --mode paper \
  --config config/runtime_profile_paper_GREEN_ONLY.yaml

# Opción 3: Nohup (background process)
nohup python main_institutional.py \
  --mode paper \
  --config config/runtime_profile_paper_GREEN_ONLY.yaml \
  > logs/paper_30d_$(date +%Y%m%d).log 2>&1 &
```

**Detach from screen:** `Ctrl+A D`
**Re-attach to screen:** `screen -r sublimine_paper_30d`

### 2.2 Verificación Post-Launch (primeros 5 minutos)

```bash
# CHECK 1: Proceso corriendo
ps aux | grep main_institutional.py
# EXPECTED: Proceso activo

# CHECK 2: Logs generándose
tail -f logs/trading_$(date +%Y%m%d).log
# EXPECTED: Ver mensajes de inicialización, strategies loaded, execution_mode=PAPER

# CHECK 3: NO crashes en primeros 5 minutos
# EXPECTED: ZERO exceptions, ZERO critical errors

# CHECK 4: Strategies cargadas (buscar en log)
grep "Strategy loaded" logs/trading_$(date +%Y%m%d).log | wc -l
# EXPECTED: 5 (una por cada GREEN COMPLETE)

# CHECK 5: PaperExecutionAdapter activo
grep "PaperExecutionAdapter" logs/trading_$(date +%Y%m%d).log
# EXPECTED: "PaperExecutionAdapter initialized"
```

**❌ ABORTAR si algún CHECK falla en primeros 5 minutos.**

---

## 3. DAILY MONITORING

**EJECUTAR TODOS LOS DÍAS a las 09:00 UTC (antes de apertura London).**

### 3.1 Daily Health Checks (5 min)

```bash
# === LOG ANALYSIS ===
# 1. Buscar CRITICAL/ERROR en logs de ayer
grep -i "CRITICAL\|ERROR" logs/trading_$(date -d yesterday +%Y%m%d).log

# EXPECTED: ZERO CRITICAL, minimal ERROR (transient network issues OK)
# ACTION: Si >10 ERRORs o ANY CRITICAL → investigar antes de continuar

# 2. KillSwitch false triggers
grep "KillSwitch.*BLOCKED" logs/trading_$(date -d yesterday +%Y%m%d).log

# EXPECTED: ZERO false triggers
# ACTION: Si ANY blocked orders → revisar kill_switch logs, determinar causa

# 3. Risk violations
grep "RISK VIOLATION" logs/trading_$(date -d yesterday +%Y%m%d).log

# EXPECTED: ZERO violations
# ACTION: Si ANY violations → investigar strategy, verificar risk_manager config
```

### 3.2 Daily Metrics (10 min)

**Generar daily report:**

```python
# Si sistema tiene daily reporting automático, revisar:
cat reports/daily/daily_report_$(date -d yesterday +%Y%m%d).json
```

**Métricas a verificar:**

| Métrica                  | Rango Aceptable         | Acción si fuera de rango                  |
|--------------------------|-------------------------|-------------------------------------------|
| **Trades ejecutados**    | 1-20 por día            | <1: revisar señales. >20: posible overtrading |
| **Win rate (daily)**     | >45%                    | <40% por 3 días consecutivos → STOP       |
| **Max DD intraday**      | <5%                     | >10% → STOP inmediatamente                |
| **Avg slippage (pips)**  | <1.0                    | >2.0 → revisar venue simulator config     |
| **Execution latency**    | <200ms                  | >500ms → revisar MT5 connection           |
| **Data quality**         | >95%                    | <90% → revisar data feed, posible gaps    |

### 3.3 Daily Checklist

**Copiar y completar daily:**

```
FECHA: ____________________
OPERADOR: __________________

[ ] Logs revisados (ZERO CRITICAL, <10 ERROR)
[ ] KillSwitch checks (ZERO false triggers)
[ ] Risk violations (ZERO)
[ ] Trades count: _____ (1-20 OK)
[ ] Win rate daily: _____% (>45% OK)
[ ] Max DD: _____% (<5% OK)
[ ] Proceso corriendo (ps aux | grep main_institutional)
[ ] Disk space >10GB (df -h)

NOTAS:
_______________________________________________
_______________________________________________
```

---

## 4. WEEKLY METRICS REVIEW

**EJECUTAR CADA DOMINGO a las 18:00 UTC (post-cierre NY Friday).**

### 4.1 Per-Strategy Performance (30 min)

**Comando:**

```python
# Generar weekly report por estrategia
python scripts/generate_strategy_report.py \
  --start-date $(date -d '7 days ago' +%Y-%m-%d) \
  --end-date $(date +%Y-%m-%d) \
  --profile GREEN_ONLY
```

**Tabla de Review (completar semanalmente):**

| Estrategia                      | Trades | Win% | Sharpe | Max DD (R) | Profit Factor | Status |
|---------------------------------|--------|------|--------|------------|---------------|--------|
| breakout_volume_confirmation    |        |      |        |            |               |        |
| liquidity_sweep                 |        |      |        |            |               |        |
| ofi_refinement                  |        |      |        |            |               |        |
| order_flow_toxicity             |        |      |        |            |               |        |
| vpin_reversal_extreme           |        |      |        |            |               |        |
| **PORTFOLIO (aggregate)**       |        |      |        |            |               |        |

**Criterios de Alerta por Estrategia:**

- 🔴 **DESHABILITAR si:** Win% <45% AND Trades >10 en la semana
- 🟡 **VIGILAR si:** Sharpe <0.5 OR Max DD >10R
- 🟢 **SALUDABLE si:** Win% >55% AND Sharpe >1.0 AND Max DD <5R

### 4.2 Portfolio-Level Metrics (15 min)

**Objetivos institucionales (agregado 30 días):**

| Métrica                | Target      | Minimum Acceptable | STOP Threshold |
|------------------------|-------------|--------------------|----------------|
| **Sharpe Ratio**       | >1.5        | >1.0               | <0.5           |
| **Win Rate**           | >60%        | >55%               | <50%           |
| **Profit Factor**      | >2.0        | >1.5               | <1.2           |
| **Max Drawdown (R)**   | <10R        | <15R               | >20R           |
| **Monthly Target (R)** | 15R         | 10R                | <5R            |

**Acción si STOP Threshold alcanzado:**
- PAUSAR 30d PAPER inmediatamente
- Ejecutar post-mortem analysis (ver sección 8.3)
- Reportar a CIO con trazabilidad completa

### 4.3 Weekly Checklist

```
SEMANA: ______ (del _____/_____/_____ al _____/_____/_____)
OPERADOR: __________________

[ ] Per-strategy performance reviewed
[ ] ZERO strategies en zona ROJA (win% <45%)
[ ] Portfolio Sharpe >1.0
[ ] Portfolio Win Rate >55%
[ ] Portfolio Max DD <15R
[ ] Logs archivados (mv logs/old_logs/ archive/)
[ ] Backup semanal creado

DECISIÓN:
[ ] CONTINUAR 30d PAPER (todo normal)
[ ] VIGILAR (métricas en zona amarilla)
[ ] STOP (threshold alcanzado - ver sección 5)

NOTAS:
_______________________________________________
_______________________________________________
```

---

## 5. STOP CRITERIA

**ABORTAR 30 días PAPER inmediatamente si:**

### 5.1 P0 - BLOCKING (Stop inmediato)

- ❌ **Sharpe <0.5** (agregado 7+ días)
- ❌ **Win rate <50%** (agregado 7+ días)
- ❌ **Max DD >20R** (desde inicio)
- ❌ **Daily loss >10%** (cualquier día)
- ❌ **>3 estrategias con win% <45%** simultáneamente
- ❌ **CRITICAL errors** en logs (crash, DB corruption, data loss)
- ❌ **KillSwitch false trigger rate >5%**
- ❌ **Risk violations** (ANY order >2% risk)

### 5.2 P1 - WARNING (Requiere decisión CIO)

- 🟡 **Sharpe 0.5-1.0** (zona gris, vigilar)
- 🟡 **Win rate 50-55%** (por debajo de target pero no crítico)
- 🟡 **Max DD 15-20R** (acercándose a límite)
- 🟡 **2 estrategias** con win% <45% simultáneamente
- 🟡 **Data quality <90%** por 3+ días consecutivos

### 5.3 STOP Procedure

```bash
# PASO 1: Detener sistema
screen -r sublimine_paper_30d
# Ctrl+C (graceful shutdown)

# PASO 2: Backup completo
mkdir -p backups/stop_$(date +%Y%m%d_%H%M%S)
cp -r logs/ backups/stop_$(date +%Y%m%d_%H%M%S)/
cp -r data/ backups/stop_$(date +%Y%m%d_%H%M%S)/ 2>/dev/null || true

# PASO 3: Generar post-mortem report
python scripts/generate_postmortem_report.py \
  --start-date <30d_paper_start_date> \
  --end-date $(date +%Y-%m-%d) \
  --reason "STOP_CRITERIA_TRIGGERED" \
  --output reports/postmortem_30d_paper_$(date +%Y%m%d).md

# PASO 4: Notificar CIO
# Enviar email con:
# - STOP reason (cuál threshold)
# - Post-mortem report (adjunto)
# - Próximos pasos (re-calibración, strategy disable, etc.)
```

---

## 6. POST-30D EVALUATION

**Ejecutar al completar 30 días PAPER (sin STOP):**

### 6.1 Generar Final Report (30 min)

```bash
# Generar reporte institucional 30 días
python scripts/generate_institutional_report.py \
  --start-date <30d_paper_start_date> \
  --end-date $(date +%Y-%m-%d) \
  --profile GREEN_ONLY \
  --output reports/INSTITUTIONAL_30D_PAPER_GREEN_ONLY_$(date +%Y%m%d).pdf

# Incluir:
# - Executive Summary (Sharpe, Win%, DD, PF)
# - Per-Strategy Performance (tablas)
# - Equity Curve (gráfico)
# - Drawdown Analysis (underwater plot)
# - Trade Distribution (win/loss histogram)
# - Risk Metrics (VaR, CVaR, max consecutive losses)
```

### 6.2 Validation Checklist

**Completar para aprobar paso a LIVE:**

```
30D PAPER VALIDATION - GREEN ONLY PROFILE
Fecha inicio: _______________
Fecha fin: _______________
Total días operativos: _____ (REQUIRED: ≥30 días)

=== PERFORMANCE METRICS ===
[ ] Sharpe Ratio: _____ (REQUIRED: ≥1.0, TARGET: ≥1.5)
[ ] Win Rate: _____% (REQUIRED: ≥55%, TARGET: ≥60%)
[ ] Profit Factor: _____ (REQUIRED: ≥1.5, TARGET: ≥2.0)
[ ] Max Drawdown: _____R (REQUIRED: <20R, TARGET: <10R)
[ ] Monthly Return: _____R (REQUIRED: ≥10R, TARGET: ≥15R)

=== OPERATIONAL METRICS ===
[ ] Total trades executed: _____ (REQUIRED: ≥30)
[ ] Avg trades per day: _____ (EXPECTED: 1-5)
[ ] Data quality avg: _____% (REQUIRED: ≥95%)
[ ] Execution errors: _____ (REQUIRED: <1%, TARGET: 0%)
[ ] KillSwitch false triggers: _____ (REQUIRED: 0)
[ ] Risk violations: _____ (REQUIRED: 0)

=== STRATEGY-LEVEL ===
[ ] breakout_volume_confirmation: Win% _____ (REQUIRED: ≥50%)
[ ] liquidity_sweep: Win% _____ (REQUIRED: ≥50%)
[ ] ofi_refinement: Win% _____ (REQUIRED: ≥50%)
[ ] order_flow_toxicity: Win% _____ (REQUIRED: ≥50%)
[ ] vpin_reversal_extreme: Win% _____ (REQUIRED: ≥50%)

DECISIÓN FINAL:
[ ] APROBADO para LIVE - Cumple TODOS los REQUIRED
[ ] RECHAZADO - NO cumple algún REQUIRED (especificar):
    _______________________________________________

FIRMA CIO: ______________________  FECHA: __________
```

---

## 7. PREREQUISITES FOR LIVE ACTIVATION

**CRITICAL: Completar TODOS antes de activar LIVE mode.**

### 7.1 Technical Prerequisites

- [x] ✅ 30 días PAPER completados sin STOP
- [x] ✅ Validation Checklist 100% aprobado (todos los REQUIRED)
- [x] ✅ `scripts/validate_runtime_profiles.py` pasa en LIVE profile
- [x] ✅ `scripts/smoke_test_green_only.py` adaptado para LIVE (opcional)
- [x] ✅ `scripts/check_no_atr_in_risk.py` pasa (ZERO ATR en risk)
- [x] ✅ KillSwitch 4 layers testeado y operacional
- [x] ✅ MT5 REAL account conectado y verificado
- [x] ✅ Backup automático configurado (cada 6h)
- [x] ✅ Alerts email/SMS configurados y testeados

### 7.2 Operational Prerequisites

- [ ] **CIO sign-off** en validation checklist
- [ ] **Risk Officer approval** (si aplica)
- [ ] **Capital allocation** definido (e.g., $10,000 LIVE)
- [ ] **Emergency runbook** revisado (sección 8)
- [ ] **Operador 24/7** disponible (o monitoring automático)
- [ ] **Broker confirmado**: Cuenta REAL, leverage, comisiones
- [ ] **Legal/Compliance**: Disclaimers, risk disclosure firmados

### 7.3 Configuration Changes for LIVE

**PASO 1: Activar LIVE mode en config**

```bash
# Editar config/runtime_profile_live_GREEN_ONLY.yaml
nano config/runtime_profile_live_GREEN_ONLY.yaml

# CAMBIO 1: Activar live_trading
live_trading:
  enabled: true  # CAMBIAR de false → true

# CAMBIO 2: Activar production environment
environments:
  production:
    enabled: true  # CAMBIAR de false → true
```

**PASO 2: Validar config LIVE**

```bash
python scripts/validate_runtime_profiles.py
# EXPECTED: runtime_profile_live_GREEN_ONLY.yaml válido
```

**PASO 3: Launch LIVE (con triple confirmación)**

```bash
# Sistema pedirá 3 confirmaciones antes de enviar órdenes REAL
python main_institutional.py \
  --mode live \
  --config config/runtime_profile_live_GREEN_ONLY.yaml

# EXPECTED prompts:
# 1. "LIVE MODE - REAL MONEY AT RISK. Confirm? (yes/no)"
# 2. "MT5 REAL account detected. Continue? (yes/no)"
# 3. "Final confirmation before KillSwitch disarm. Proceed? (yes/no)"
```

**⚠️ WARNING: Solo CIO puede autorizar paso a LIVE.**

---

## 8. EMERGENCY PROCEDURES

### 8.1 Emergency Stop (Panic Button)

**Si necesitas detener sistema INMEDIATAMENTE:**

```bash
# Opción 1: Graceful shutdown (recomendado)
screen -r sublimine_paper_30d
# Ctrl+C

# Opción 2: Kill process (si Ctrl+C no responde)
pkill -9 -f main_institutional.py

# Opción 3: Activar KillSwitch manual (LIVE mode)
# Crear archivo de emergencia
touch config/KILLSWITCH_MANUAL_OVERRIDE
# Sistema bloqueará TODAS las órdenes nuevas
```

### 8.2 Emergency Contacts

**Orden de escalación:**

1. **Operador Principal**: <operator_email> / <operator_phone>
2. **CIO**: <cio_email> / <cio_phone>
3. **Soporte Técnico**: <support_email> / <support_phone>
4. **Broker (LIVE only)**: <broker_support_phone>

### 8.3 Post-Mortem Template

**Ejecutar después de cualquier STOP o incident:**

```markdown
# POST-MORTEM: 30D PAPER GREEN ONLY INCIDENT

## INCIDENT SUMMARY
- **Fecha**: _______________
- **Operador**: _______________
- **Severidad**: P0 / P1 / P2
- **Duración downtime**: _____ minutos

## ROOT CAUSE
(Qué causó el STOP o incident)

## TIMELINE
- HH:MM - Evento inicial detectado
- HH:MM - Acción tomada
- HH:MM - Sistema estabilizado

## IMPACT
- Trades afectados: _____
- Pérdida estimada: $_____ (PAPER = $0 real)
- Data loss: Yes / No

## CORRECTIVE ACTIONS
1. Acción inmediata:
2. Acción a corto plazo (1 semana):
3. Acción a largo plazo (preventiva):

## LESSONS LEARNED
(Qué aprendimos, cómo prevenir recurrencia)

## APPROVAL
CIO: ______________________  FECHA: __________
```

---

## 9. APÉNDICES

### 9.1 Comandos Útiles

```bash
# Ver logs en tiempo real
tail -f logs/trading_$(date +%Y%m%d).log

# Buscar trades ejecutados hoy
grep "TRADE_EXECUTED" logs/trading_$(date +%Y%m%d).log

# Verificar proceso corriendo
ps aux | grep main_institutional.py | grep -v grep

# Disk space
df -h | grep -E "/$|/home"

# Memory usage
free -h

# Detach from screen
# Ctrl+A D

# Re-attach to screen
screen -r sublimine_paper_30d

# Kill screen session
screen -X -S sublimine_paper_30d quit
```

### 9.2 Logs Locations

```
logs/
├── trading_YYYYMMDD.log       # Main trading log
├── risk_YYYYMMDD.log           # Risk management log (if separate)
├── kill_switch_YYYYMMDD.log    # KillSwitch events
├── execution_YYYYMMDD.log      # Order execution log
└── critical_events.log         # Critical events (all time)
```

### 9.3 Reports Locations

```
reports/
├── daily/
│   └── daily_report_YYYYMMDD.json
├── weekly/
│   └── weekly_report_YYYY_WW.pdf
└── institutional/
    └── INSTITUTIONAL_30D_PAPER_GREEN_ONLY_YYYYMMDD.pdf
```

---

## ✅ FINAL CHECKLIST ANTES DE INICIAR 30D PAPER

```
OPERADOR: __________________
FECHA: __________________

=== PRE-LAUNCH (Sección 1) ===
[ ] validate_runtime_profiles.py ejecutado (EXIT CODE 0)
[ ] smoke_test_green_only.py ejecutado (EXIT CODE 0)
[ ] check_no_atr_in_risk.py ejecutado (EXIT CODE 0)
[ ] Config manual verificado (5 GREEN, execution_mode=paper)
[ ] Infraestructura OK (server, MT5 demo, disk, RAM)
[ ] Alerts configurados (email, emergency contacts)
[ ] Backup pre-launch creado

=== LAUNCH (Sección 2) ===
[ ] Sistema iniciado en screen/tmux
[ ] Post-launch checks completados (5 min)
[ ] ZERO crashes en primeros 5 minutos
[ ] 5 strategies loaded (verificado en logs)
[ ] PaperExecutionAdapter activo (verificado en logs)

=== MONITORING SETUP ===
[ ] Daily checklist template impreso/accesible
[ ] Weekly checklist template impreso/accesible
[ ] Calendar alarms: Daily 09:00 UTC, Weekly Sunday 18:00 UTC
[ ] Emergency procedures revisadas y entendidas

FIRMA OPERADOR: ______________________  FECHA: __________

APROBACIÓN CIO: ______________________  FECHA: __________
```

---

**FIN DEL RUNBOOK**

---

**NOTAS INSTITUCIONALES:**

1. Este runbook es un **documento vivo**. Actualizar si se descubren mejoras durante 30d PAPER.
2. **TODA decisión de STOP** requiere post-mortem (sección 8.3).
3. **NINGÚN paso a LIVE** sin sign-off CIO (sección 7.2).
4. **Mantener trazabilidad completa**: Logs, backups, checklists completados.
5. **Zero tolerance** para risk violations o KillSwitch bypass.

**MANDATO GAMMA - GREEN ONLY 30D PAPER: Operacional y listo para deployment.**
