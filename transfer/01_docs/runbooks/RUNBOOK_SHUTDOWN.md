
================================================================================
RUNBOOK - SHUTDOWN
Procedimiento de Parada Segura
================================================================================

PARADA NORMAL
-------------

1. Presionar Ctrl+C en ventana del motor

2. Esperar mensaje:
   "Deteniendo sistema..."
   "OK Sistema detenido"

3. Verificar posiciones abiertas en MT5
   - Si hay posiciones: decisión manual (mantener/cerrar)

4. Verificar logs finales
   - Último SCAN completado
   - Sin errores pendientes

5. Cerrar ventana PowerShell

PARADA DE EMERGENCIA
---------------------

Si motor no responde a Ctrl+C:

1. Cerrar ventana PowerShell (X)
2. Verificar proceso:
   tasklist | findstr python
3. Si persiste:
   taskkill /F /IM python.exe
4. Verificar MT5:
   - Cerrar posiciones manualmente si necesario
   - Revisar órdenes pendientes

POST-SHUTDOWN
-------------

1. Revisar último scan en logs
2. Documentar razón de parada (si no planeada)
3. Verificar estado de cuenta MT5
4. Backup de logs si necesario:
   copy logs\live_trading.log logs\backup_<timestamp>.log

REINICIO TRAS SHUTDOWN
----------------------

1. Esperar 30 segundos
2. Seguir RUNBOOK_STARTUP.md
3. Verificar que nuevo inicio es limpio (sin estado previo)
