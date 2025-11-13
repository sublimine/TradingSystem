================================================================================
VOLUME 06 - ENGINE EXECUTION
================================================================================

CICLO DE ESCANEO
----------------
Intervalo: 60 segundos
Orden: Secuencial (símbolo por símbolo, estrategia por estrategia)
Timeout: No aplica (sin límite hard)

LISTA BLANCA ACTIVA (9 módulos)
--------------------------------
1. breakout_volume_confirmation
2. correlation_divergence
3. kalman_pairs_trading
4. liquidity_sweep
5. mean_reversion_statistical
6. momentum_quality
7. news_event_positioning
8. order_flow_toxicity
9. volatility_regime_adaptation

POLÍTICAS ANTI-SPAM
-------------------
- Cooldown: 300 segundos por símbolo/dirección
- Max simultáneas por símbolo: 2
- Min intervalo misma estrategia/símbolo: 300s
- Bloqueo por DUPLICATE_IDEA si ya existe posición

MANEJO DE ERRORES
-----------------
Principio: NO ABORTAR EN IMPORT

- Si un módulo falla al cargar → logger.error() + continuar con los demás
- Si una estrategia falla en evaluate() → stats['errors']++ + continuar
- Motor nunca se detiene por fallo individual de estrategia

LOGGING DE CARGA:
  "CARGADA <modulo>" → OK
  "ERROR_IMPORT <modulo>" → Falló pero motor continúa
  "IGNORADA <modulo>" → No está en lista blanca

EJECUCIÓN DE ÓRDENES
--------------------
1. Validar signal.validate()
2. Verificar can_open_position() (anti-spam)
3. Obtener precio actual (tick)
4. Calcular lotaje (symbol_info.volume_min)
5. Enviar orden MT5
6. Registrar en open_positions
7. Log resultado

FLUJO COMPLETO:
  scan_markets() →
    for symbol in SYMBOLS:
      get_market_data()
      calculate_features()
      for strategy in strategies:
        evaluate()
        if signal:
          if can_open_position():
            execute_order()
            record_position_opened()
