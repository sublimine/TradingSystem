================================================================================
MIGRATION KIT - Sistema de Trading Institucional
Build: 20251105_FINAL
================================================================================

PASOS PARA IMPORTAR EL CONTEXTO
--------------------------------

1. RESTAURAR CHECKPOINT
   - Copiar checkpoint/STATE_20251105_T0/ al entorno destino
   - Verificar hashes con manifest_hashes.json
   - Instalar dependencias de env_fingerprint.json

2. REVISAR DOSSIER
   - Empezar por dossier/00_RESUMEN_EJECUTIVO.md
   - Seguir con dossier/INDEX.json para navegación
   - Leer estrategias en dossier/03_ESTRATEGIAS/

3. CONFIGURAR ENTORNO
   - Python 3.x
   - MetaTrader5
   - pandas, numpy
   - Cuenta DEMO configurada

4. VALIDAR OPERACIÓN
   - python scripts/live_trading_engine.py
   - Verificar "Estrategias activas: 9"
   - Monitorear primeros 3 scans sin errores

5. CHECKPOINT DE VERIFICACIÓN
   - Generar nuevo checkpoint tras validación
   - Comparar con STATE_20251105_T0

ORDEN DE LECTURA RECOMENDADO
-----------------------------
1. dossier/00_RESUMEN_EJECUTIVO.md
2. dossier/01_ARQUITECTURA_SISTEMA.md
3. dossier/03_ESTRATEGIAS/ (todas)
4. dossier/07_RUNBOOK_OPERATIVO/RUNBOOK.md
5. Resto de volúmenes según necesidad

CONTACTO Y SOPORTE
------------------
Sistema autónomo - sin soporte externo
Logs en: logs/live_trading.log
Checkpoints de estado: disponibles en demanda

Fecha: 2025-11-05
Timezone: Europe/Zurich
