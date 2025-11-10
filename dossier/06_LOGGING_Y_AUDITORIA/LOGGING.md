
================================================================================
LOGGING Y AUDITORÍA
================================================================================

ESQUEMA DE EVENTOS
------------------

Formato: texto con timestamp
Encoding: UTF-8
Handler: FileHandler + StreamHandler

Niveles:
- INFO: Eventos normales
- ERROR: Excepciones y fallos

Eventos clave:

1. INICIALIZACIÓN
   "Conectado a <server>"
   "Cuenta: <login>"
   "Balance: $<amount>"
   "Cargando estrategias..."
   "CARGADA <strategy>" | "ERROR_IMPORT <strategy>"
   "Estrategias activas: <n>"

2. SCAN
   "SCAN #<n> - <timestamp>"
   Por cada símbolo evaluado

3. SEÑAL
   "SEÑAL GENERADA:"
   "  Estrategia: <name>"
   "  Simbolo: <symbol>"
   "  Direccion: <direction>"
   "  Entry: <price>"

4. EJECUCIÓN
   "OK ORDEN EJECUTADA: <direction> <symbol> @ <price>"
   "   SL: <sl> | TP: <tp>"
   "   Ticket: <ticket>"

5. ERRORES
   "ERROR evaluando <strategy>: <message>"
   "ERROR: order_send devolvio None"
   "ERROR: Orden rechazada - <comment>"

6. ANTI-SPAM
   "THROTTLE_COOLDOWN: Ya existe <direction> en <symbol>"
   "DUPLICATE_IDEA: <symbol> <direction> en cooldown"

7. ESTADÍSTICAS (cada 10 scans)
   "ESTADISTICAS (Scan #<n>)"
   Por estrategia: evaluaciones, señales, errores, trades

CORRELATION IDs
---------------
Actualmente: No implementados
Futuro: UUID por señal para trazar señal → orden → posición

TRAZAS
------
Señal generada → Validación → can_open_position → execute_order → MT5 result

Location: logs/live_trading.log
Rotación: Manual (no automática aún)
Retención: Indefinida (hasta limpieza manual)

FORMATO ESTRUCTURADO (Futuro)
------------------------------
JSON Lines para parsing automatizado:
{"timestamp": "...", "level": "INFO", "event": "signal", "strategy": "...", ...}
