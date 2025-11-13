
LÓGICA DE TRIGGERS - correlation_divergence
================================================================================

ENTRADA
-------
Condiciones evaluadas en método evaluate():
- Análisis de data (pd.DataFrame con 500 barras M1)
- Validación de features disponibles
- Evaluación de condiciones específicas de la estrategia
- Generación de Signal si todas las condiciones se cumplen

SALIDA
------
No aplica salidas gestionadas por estrategia.
SL/TP definidos en la señal inicial.

FILTROS
-------
- Validación de datos mínimos (100 barras)
- Features completos
- Precio actual válido
- Anti-spam: cooldown 300s por símbolo/dirección

CONFIRMACIONES
--------------
Múltiples condiciones deben cumplirse simultáneamente para generar señal.
Lógica AND (no OR) para evitar falsos positivos.

ANTI-DUPLICADOS
---------------
Motor maneja anti-spam:
- can_open_position() verifica posiciones existentes
- Cooldown por símbolo/dirección
- THROTTLE_COOLDOWN si ya existe posición

MTF (Multi-Timeframe)
---------------------
Actualmente: Single timeframe M1
Futuro: Confirmación con M5/M15 si aplica
