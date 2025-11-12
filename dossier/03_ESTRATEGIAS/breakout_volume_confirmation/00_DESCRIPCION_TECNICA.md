
================================================================================
DESCRIPCIÓN TÉCNICA - breakout_volume_confirmation
================================================================================

IDENTIFICACIÓN
--------------
Módulo: strategies.breakout_volume_confirmation
Clase: BreakoutVolumeConfirmation
Archivo: src/strategies/breakout_volume_confirmation.py

PROPÓSITO
---------
Estrategia institucional basada en microestructura de mercado y análisis
cuantitativo. NO utiliza indicadores retail (RSI/MACD para entrada).

RACIONAL INSTITUCIONAL
----------------------
Busca ineficiencias de precio mediante análisis de flujo de órdenes,
detección de zonas de liquidez y confirmación con volumen institucional.

SUPUESTOS
---------
- Mercados líquidos (11 símbolos major + metales + cripto)
- Data M1 con calidad adecuada
- Latencia < 500ms para ejecución
- Spreads dentro de rangos normales

ESTADO: OPERATIVA
Build: 20251105_FINAL
