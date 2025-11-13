
================================================================================
LOGGING AND AUDIT
Esquema de Eventos y Auditoría
================================================================================

ESQUEMA DE LOGS
---------------

Formato: Texto plano con timestamp
Encoding: UTF-8
Handler: logging.FileHandler + StreamHandler
Destino: logs/live_trading.log

Estructura por evento:
  YYYY-MM-DD HH:MM:SS,mmm - LEVEL - MESSAGE

Campos mínimos:
  - timestamp (automático)
  - level (INFO/ERROR)
  - message (texto descriptivo)

EVENTOS PRINCIPALES
-------------------

1. STARTUP
   "Conectado a <server>"
   "Cuenta: <account_id>"
   "Balance: $<amount>"
   "Estrategias activas: <n>"

2. STRATEGY LOADING
   "CARGADA <strategy_name>"
   "ERROR_IMPORT <strategy_name>: <error>"

3. SCAN
   "SCAN #<n> - YYYY-MM-DD HH:MM:SS"
   "Resultados del scan: Señales generadas: <count>"

4. SIGNAL
   "SEÑAL GENERADA:"
   "  Estrategia: <name>"
   "  Simbolo: <symbol>"
   "  Direccion: <direction>"
   "  Entry: <price>"

5. EXECUTION
   "OK ORDEN EJECUTADA: <direction> <symbol> @ <price>"
   "   SL: <sl> | TP: <tp>"
   "   Ticket: <ticket>"

6. ERROR
   "ERROR evaluando <strategy>: <exception>"
   "ERROR: No tick para <symbol>"
   "ERROR: Orden rechazada - <reason>"

7. ANTI-SPAM
   "THROTTLE_COOLDOWN: Ya existe <direction> en <symbol>"
   "DUPLICATE_IDEA: <symbol> <direction> en cooldown"

CORRELACIÓN
-----------

Actual: No hay correlation IDs

Target:
  - Signal UUID en señal generada
  - Mismo UUID en orden enviada
  - Mismo UUID en confirmación de ejecución
  - Trazabilidad: signal → order → position

RECONSTRUCCIÓN DE INCIDENTES
-----------------------------

Para investigar un incidente:
  1. Obtener timestamp del evento
  2. grep logs/live_trading.log para ±5 minutos
  3. Buscar SCAN # más cercano
  4. Revisar evaluaciones de estrategias
  5. Verificar señales generadas
  6. Confirmar órdenes ejecutadas
  7. Correlacionar con posiciones MT5

Campos clave para buscar:
  - "ERROR"
  - Symbol específico
  - Strategy específica
  - Timestamp range

RETENCIÓN
---------

Actual: Indefinida (manual cleanup)
Target: 90 días, luego archivar
