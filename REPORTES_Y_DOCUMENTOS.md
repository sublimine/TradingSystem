# 📊 SISTEMA DE REPORTES Y DOCUMENTOS - GUÍA COMPLETA

## 🎯 ESTRUCTURA DE DIRECTORIOS

Cuando ejecutes el sistema, se crearán automáticamente estos directorios:

```
TradingSystem/
│
├── reports/                          # 📊 REPORTES DE TRADING EN VIVO
│   ├── daily_20250111.json          # Reporte diario (generado cada día)
│   ├── daily_20250112.json
│   ├── weekly_20250115.json         # Reporte semanal (generado cada domingo)
│   ├── monthly_202501.json          # Reporte mensual (fin de mes)
│   ├── quarterly_2025_Q1.json       # Reporte trimestral (fin de trimestre)
│   └── annual_2025.json             # Reporte anual (fin de año)
│
├── backtest_reports/                 # 📈 REPORTES DE BACKTESTING
│   ├── analysis_20250111_143022.json    # Análisis completo de backtest
│   ├── analysis_20250111_150534.json
│   └── walk_forward_20250111.json       # Resultados de walk-forward
│
├── logs/                             # 📝 LOGS DEL SISTEMA
│   ├── trading_system.log           # Log principal (todas las operaciones)
│   ├── trading_system_20250111.log  # Logs diarios archivados
│   └── errors.log                   # Solo errores críticos
│
├── ml_data/                          # 🧠 DATOS DEL MACHINE LEARNING
│   ├── trade_memory.db              # Base de datos de trades históricos
│   ├── model_checkpoint_latest.pkl  # Modelo ML más reciente
│   ├── model_checkpoint_20250111.pkl # Checkpoints históricos
│   └── feature_importance.json      # Importancia de features
│
└── trade_history/                    # 💼 HISTORIAL DE TRADES
    ├── trades_2025_01.csv           # Trades del mes (CSV exportable)
    ├── trades_2025_01.json          # Trades del mes (JSON detallado)
    └── positions_history.db         # Base de datos SQLite con todo el historial
```

---

## 📊 REPORTES DE TRADING EN VIVO

### **1. REPORTE DIARIO** (`reports/daily_YYYYMMDD.json`)

**Generado:** Todos los días a las 00:00 (medianoche)

**Contenido:**
```json
{
  "date": "2025-01-11",
  "total_trades": 12,
  "winning_trades": 8,
  "losing_trades": 4,
  "win_rate": 0.667,
  "total_pnl_r": 4.5,
  "avg_win_r": 1.2,
  "avg_loss_r": -0.8,
  "largest_win_r": 3.2,
  "largest_loss_r": -1.5,
  "expectancy_r": 0.375,
  "strategy_breakdown": {
    "order_block_strategy": {
      "count": 3,
      "sum": 2.8,
      "mean": 0.93
    },
    "stop_hunt_reversal": {
      "count": 4,
      "sum": 1.2,
      "mean": 0.3
    }
  }
}
```

**Cómo leerlo:**
- `total_pnl_r`: Ganancia/pérdida total del día en R (risk units)
- `win_rate`: Porcentaje de trades ganadores
- `expectancy_r`: Ganancia promedio esperada por trade
- `strategy_breakdown`: Performance de cada estrategia

### **2. REPORTE SEMANAL** (`reports/weekly_YYYYMMDD.json`)

**Generado:** Todos los domingos a medianoche

**Contenido:**
```json
{
  "week_ending": "2025-01-12",
  "total_trades": 45,
  "win_rate": 0.622,
  "total_pnl_r": 18.5,
  "expectancy_r": 0.41,
  "sharpe_ratio": 1.85,
  "sortino_ratio": 2.12,
  "max_drawdown_r": -3.2,
  "profit_factor": 2.34,
  "strategy_attribution": {
    "order_block_strategy": {
      "count": 12,
      "sum": 7.8,
      "mean": 0.65
    }
  },
  "best_trade": {
    "strategy": "crisis_mode_volatility_spike",
    "symbol": "EURUSD",
    "pnl_r": 5.2
  },
  "worst_trade": {
    "strategy": "spoofing_detection_l2",
    "symbol": "GBPUSD",
    "pnl_r": -2.1
  }
}
```

**Métricas importantes:**
- `sharpe_ratio`: Retorno ajustado por riesgo (>1.0 = bueno, >2.0 = excelente)
- `sortino_ratio`: Como Sharpe pero solo penaliza volatilidad negativa
- `max_drawdown_r`: Peor racha de pérdidas consecutivas
- `profit_factor`: Ganancias brutas / pérdidas brutas (>1.5 = bueno)

### **3. REPORTE MENSUAL** (`reports/monthly_YYYYMM.json`)

**Generado:** Último día de cada mes

**Contenido:**
```json
{
  "month_ending": "2025-01",
  "total_trades": 187,
  "win_rate": 0.615,
  "total_pnl_r": 76.5,
  "expectancy_r": 0.409,
  "sharpe_ratio": 1.92,
  "sortino_ratio": 2.28,
  "calmar_ratio": 5.85,
  "max_drawdown_r": -13.1,
  "profit_factor": 2.41,
  "top_strategies": {
    "order_block_strategy": {
      "count": 45,
      "sum": 28.5,
      "mean": 0.63,
      "win_rate": 0.71
    },
    "stop_hunt_reversal": {
      "count": 38,
      "sum": 22.1,
      "mean": 0.58,
      "win_rate": 0.65
    }
  },
  "worst_strategies": {
    "spoofing_detection_l2": {
      "count": 12,
      "sum": -4.2,
      "mean": -0.35,
      "win_rate": 0.42
    }
  },
  "recommendations": [
    "✅ Performance within acceptable parameters. Continue monitoring.",
    "🔴 Strategy 'spoofing_detection_l2' lost -4.2R. Consider: 1) Disable, 2) Optimize"
  ]
}
```

**CRÍTICO:** Lee las `recommendations` - te dice exactamente qué hacer.

### **4. REPORTE TRIMESTRAL** (`reports/quarterly_YYYY_QX.json`)

**Generado:** Fin de trimestre (31 Mar, 30 Jun, 30 Sep, 31 Dic)

**Contenido:**
```json
{
  "quarter_ending": "2025-Q1",
  "total_trades": 562,
  "total_pnl_r": 234.8,
  "sharpe_ratio": 2.05,
  "max_drawdown_r": -18.3,
  "strategic_insights": {
    "most_profitable_month": "2025-03",
    "most_active_strategy": "order_block_strategy",
    "avg_trade_duration_minutes": 127.5
  }
}
```

### **5. REPORTE ANUAL** (`reports/annual_YYYY.json`)

**Generado:** 31 de diciembre

**Contenido completo del año:**
```json
{
  "year": 2025,
  "total_trades": 2234,
  "total_pnl_r": 987.5,
  "win_rate": 0.628,
  "sharpe_ratio": 2.18,
  "sortino_ratio": 2.56,
  "calmar_ratio": 7.32,
  "max_drawdown_r": -21.5,
  "profit_factor": 2.63,
  "monthly_pnl": {
    "2025-01": 76.5,
    "2025-02": 82.3,
    "2025-03": 91.2,
    ...
  }
}
```

---

## 📈 REPORTES DE BACKTESTING

### **ANÁLISIS COMPLETO** (`backtest_reports/analysis_TIMESTAMP.json`)

**Generado:** Cada vez que ejecutas un backtest

**Contenido:**
```json
{
  "summary": {
    "initial_capital": 10000.0,
    "final_equity": 12850.5,
    "total_return_pct": 28.5,
    "total_return_r": 145.2,
    "total_trades": 287,
    "win_rate": 0.615
  },
  "risk_metrics": {
    "sharpe_ratio": 1.85,
    "sortino_ratio": 2.12,
    "calmar_ratio": 6.34,
    "omega_ratio": 1.92,
    "kappa_3_ratio": 1.78,
    "profit_factor": 2.34,
    "payoff_ratio": 1.52,
    "recovery_factor": 7.89,
    "ulcer_index": 4.23
  },
  "strategy_attribution": {
    "order_block_strategy": {
      "total_trades": 68,
      "win_rate": 0.69,
      "total_pnl_r": 45.2,
      "avg_pnl_r": 0.66,
      "sharpe": 2.12,
      "profit_factor": 2.85
    },
    "stop_hunt_reversal": {
      "total_trades": 54,
      "win_rate": 0.63,
      "total_pnl_r": 32.8,
      "avg_pnl_r": 0.61,
      "sharpe": 1.89,
      "profit_factor": 2.41
    }
  },
  "drawdown_analysis": {
    "max_drawdown_r": -18.5,
    "current_drawdown_r": -2.3,
    "num_drawdown_periods": 23,
    "avg_drawdown_depth_r": -5.2,
    "avg_recovery_trades": 12.5,
    "top_5_drawdowns": [
      {
        "depth_r": -18.5,
        "length_trades": 34,
        "start_idx": 145,
        "end_idx": 179
      },
      {
        "depth_r": -14.2,
        "length_trades": 28,
        "start_idx": 56,
        "end_idx": 84
      }
    ]
  },
  "trade_distribution": {
    "avg_win_r": 1.85,
    "avg_loss_r": -1.22,
    "median_win_r": 1.52,
    "median_loss_r": -0.98,
    "largest_win_r": 5.8,
    "largest_loss_r": -3.2,
    "skewness": 0.52,
    "kurtosis": 2.34
  },
  "monthly_returns": {
    "2024-01": {
      "trades": 23,
      "total_r": 12.5,
      "avg_r": 0.54,
      "win_rate": 0.65
    }
  },
  "time_analysis": {
    "best_hour": 8,
    "worst_hour": 22,
    "best_day": 2,
    "worst_day": 4
  }
}
```

**Cómo interpretarlo:**
1. **summary**: Resultados generales
2. **risk_metrics**: Métricas de calidad del sistema
3. **strategy_attribution**: ¿Qué estrategias funcionan?
4. **drawdown_analysis**: ¿Cuánto puedes perder?
5. **monthly_returns**: ¿Consistencia mensual?

---

## 📝 LOGS DEL SISTEMA

### **LOG PRINCIPAL** (`logs/trading_system.log`)

**Contenido en tiempo real:**
```
2025-01-11 14:30:22 - EliteTradingSystem - INFO - SYSTEM INITIALIZATION COMPLETE
2025-01-11 14:30:22 - EliteTradingSystem - INFO - ML Engine: ENABLED ✓
2025-01-11 14:30:22 - EliteTradingSystem - INFO - Strategies Loaded: 24
2025-01-11 14:31:15 - OrderBlockStrategy - INFO - ✓ LONG signal: EURUSD @ 1.08500
2025-01-11 14:31:15 - strategic_stops - INFO - ✓✓ WICK SWEEP stop: 1.08320 (significance: 2.3)
2025-01-11 14:31:16 - RiskManager - INFO - Position size: 0.05 lots (1% risk)
2025-01-11 14:31:16 - PositionManager - INFO - Position opened: EURUSD LONG @ 1.08500
2025-01-11 14:45:30 - PositionManager - INFO - Position closed: EURUSD @ 1.08780 (+2.8R)
2025-01-11 14:45:30 - MLAdaptiveEngine - INFO - Learning from trade: +2.8R (win)
```

**Útil para:**
- Debugging (si algo falla)
- Ver qué está haciendo el sistema en tiempo real
- Auditoría de trades

---

## 🧠 DATOS DEL MACHINE LEARNING

### **TRADE MEMORY** (`ml_data/trade_memory.db`)

Base de datos SQLite con TODOS los trades históricos para que el ML aprenda.

**Estructura:**
```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,
    symbol TEXT,
    strategy TEXT,
    direction TEXT,
    entry_price REAL,
    exit_price REAL,
    pnl_r REAL,
    regime TEXT,
    features TEXT  -- JSON con todas las features del trade
);
```

### **MODELO ML** (`ml_data/model_checkpoint_latest.pkl`)

Modelo de ML entrenado (Random Forest/Gradient Boosting).

**Se actualiza:**
- Cada 20 trades nuevos
- Cada día a medianoche
- Cuando detecta mejora significativa

### **FEATURE IMPORTANCE** (`ml_data/feature_importance.json`)

Qué features son más importantes para predecir trades ganadores:

```json
{
  "feature_importance": {
    "order_flow_imbalance": 0.245,
    "regime_volatility": 0.189,
    "order_block_strength": 0.156,
    "volume_profile": 0.134,
    "correlation_divergence": 0.098,
    "time_of_day": 0.067,
    ...
  },
  "last_updated": "2025-01-11T14:30:00Z"
}
```

---

## 💼 HISTORIAL DE TRADES

### **TRADES MENSUALES CSV** (`trade_history/trades_2025_01.csv`)

Exportable a Excel para análisis manual:

```csv
timestamp,symbol,strategy,direction,entry_price,exit_price,pnl_r,duration_min,regime
2025-01-11 14:31:16,EURUSD,order_block_strategy,LONG,1.08500,1.08780,2.8,14.2,trending
2025-01-11 15:12:45,GBPUSD,stop_hunt_reversal,SHORT,1.27850,1.27620,1.9,23.5,ranging
...
```

### **TRADES MENSUALES JSON** (`trade_history/trades_2025_01.json`)

Versión detallada con TODAS las features:

```json
[
  {
    "timestamp": "2025-01-11T14:31:16Z",
    "symbol": "EURUSD",
    "strategy": "order_block_strategy",
    "direction": "LONG",
    "entry_price": 1.08500,
    "entry_time": "2025-01-11T14:31:16Z",
    "exit_price": 1.08780,
    "exit_time": "2025-01-11T14:45:30Z",
    "pnl_r": 2.8,
    "pnl_dollars": 224.50,
    "stop_loss": 1.08320,
    "stop_type": "WICK_SWEEP",
    "take_profit": 1.09040,
    "target_type": "ORDER_BLOCK",
    "position_size": 0.05,
    "commission": 3.50,
    "duration_minutes": 14.2,
    "regime": "trending",
    "features": {
      "order_flow_imbalance": 0.73,
      "volume_profile": "bullish",
      "order_block_strength": 0.85,
      ...
    }
  }
]
```

---

## 🚀 CÓMO ACCEDER A LOS REPORTES

### **Opción 1: Leer archivos JSON directamente**

```python
import json

# Leer reporte diario
with open('reports/daily_20250111.json', 'r') as f:
    report = json.load(f)

print(f"Ganancia del día: {report['total_pnl_r']:.2f}R")
print(f"Win rate: {report['win_rate']:.2%}")
```

### **Opción 2: Usar el sistema de reporting**

```python
from src.reporting.institutional_reports import InstitutionalReportingSystem

reporting = InstitutionalReportingSystem(output_dir='reports/')

# Generar y leer reporte semanal
report = reporting.generate_weekly_report(trades, week_end_date)
print(report)
```

### **Opción 3: Dashboard web** (TODO - futuro)

```bash
# Iniciar dashboard interactivo
python dashboard/app.py
# Abre http://localhost:5000
```

---

## ⏰ CALENDARIO DE GENERACIÓN AUTOMÁTICA

| Reporte | Frecuencia | Cuándo se genera | Ubicación |
|---------|------------|------------------|-----------|
| **Diario** | Todos los días | 00:00 medianoche | `reports/daily_*.json` |
| **Semanal** | Cada semana | Domingo 00:00 | `reports/weekly_*.json` |
| **Mensual** | Cada mes | Último día 00:00 | `reports/monthly_*.json` |
| **Trimestral** | Cada trimestre | 31 Mar, 30 Jun, 30 Sep, 31 Dic | `reports/quarterly_*.json` |
| **Anual** | Cada año | 31 Dic 23:59 | `reports/annual_*.json` |
| **Backtest** | Cuando ejecutas backtest | Inmediatamente | `backtest_reports/analysis_*.json` |

---

## 📊 EJEMPLO: WORKFLOW COMPLETO

### **Día 1: Inicias el sistema**

```bash
python main.py --mode paper
```

**Se generan automáticamente:**
```
logs/
└── trading_system.log          # Log en tiempo real

reports/
└── (vacío hasta fin de día)

ml_data/
├── trade_memory.db             # Base de datos vacía
└── model_checkpoint_latest.pkl # Modelo inicial
```

### **Día 1 - 23:59:59: Primer día completo**

**Se genera automáticamente:**
```
reports/
└── daily_20250111.json         # Reporte del día 1

trade_history/
├── trades_2025_01.csv          # 12 trades del día
└── trades_2025_01.json         # Detallado
```

### **Día 7: Primera semana completa**

**Se genera automáticamente:**
```
reports/
├── daily_20250111.json
├── daily_20250112.json
├── ...
├── daily_20250117.json
└── weekly_20250117.json        # ✨ NUEVO: Reporte semanal
```

### **Día 31: Primer mes completo**

**Se genera automáticamente:**
```
reports/
├── daily_*.json (31 archivos)
├── weekly_*.json (4 archivos)
└── monthly_202501.json         # ✨ NUEVO: Reporte mensual con recommendations
```

### **Ejecutas backtest:**

```bash
python examples/backtest_example.py
```

**Se genera:**
```
backtest_reports/
├── analysis_20250111_143022.json    # Análisis completo
└── (más archivos cada vez que backtest)
```

---

## 🔍 INTERPRETAR RECOMENDACIONES

El sistema genera **recomendaciones automáticas** en reportes mensuales:

### **Ejemplo 1: Sistema saludable**
```json
"recommendations": [
  "✅ Excellent Sharpe 2.35. Consider: 1) Increase position sizing, 2) Deploy to live",
  "✅ Strong profit factor 2.63. System is robust.",
  "✅ Performance within acceptable parameters. Continue monitoring."
]
```
**Acción:** ✅ Sigue así, considera aumentar position sizing

### **Ejemplo 2: Win rate bajo**
```json
"recommendations": [
  "⚠️  Win rate 48% below 50%. Actions: 1) Tighten entry criteria, 2) Review stop placement, 3) Trail profits sooner"
]
```
**Acción:** ⚠️ Ajusta filtros de entrada, revisa stops

### **Ejemplo 3: Estrategia perdedora**
```json
"recommendations": [
  "🔴 Strategy 'spoofing_detection_l2' lost -8.2R. Consider: 1) Disable, 2) Review parameters, 3) Analyze regime fit"
]
```
**Acción:** 🔴 Deshabilita la estrategia inmediatamente

---

## 📌 RESUMEN RÁPIDO

**¿Dónde están los reportes?**
- **Trading en vivo:** `reports/`
- **Backtesting:** `backtest_reports/`
- **Logs:** `logs/`
- **ML data:** `ml_data/`
- **Historial trades:** `trade_history/`

**¿Cuándo se generan?**
- **Diario:** Automático a medianoche
- **Semanal:** Automático cada domingo
- **Mensual:** Automático fin de mes
- **Backtest:** Cuando ejecutas backtest

**¿Cómo leerlos?**
- **JSON:** Abre con cualquier editor de texto / Python
- **CSV:** Abre con Excel
- **Logs:** Tail -f en tiempo real

---

**Todo está configurado para generarse AUTOMÁTICAMENTE. No tienes que hacer nada manualmente.** 🎯
