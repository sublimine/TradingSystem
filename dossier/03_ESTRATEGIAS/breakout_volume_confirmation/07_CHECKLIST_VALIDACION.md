
CHECKLIST DE VALIDACIÓN - breakout_volume_confirmation
================================================================================

POST-DESPLIEGUE
---------------
[ ] Motor carga la estrategia sin ERROR_IMPORT
[ ] Aparece en log: "CARGADA breakout_volume_confirmation"
[ ] Estrategias activas: incluye esta estrategia
[ ] Sin excepciones en evaluations después de 10 scans
[ ] stats['breakout_volume_confirmation']['errors'] == 0
[ ] Si hay señales: validate() retorna True

MONITOREO CONTINUO
------------------
[ ] errors no aumenta constantemente
[ ] signals > 0 cuando condiciones apropiadas
[ ] Señales tienen SL/TP válidos
[ ] No spam (respeta cooldown)

CONFIRMACIÓN FINAL
------------------
Si todos los checks pasan: OPERATIVA ✓
