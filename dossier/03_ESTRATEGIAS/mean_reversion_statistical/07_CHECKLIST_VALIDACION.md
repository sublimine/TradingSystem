
CHECKLIST DE VALIDACIÓN - mean_reversion_statistical
================================================================================

POST-DESPLIEGUE
---------------
[ ] Motor carga la estrategia sin ERROR_IMPORT
[ ] Aparece en log: "CARGADA mean_reversion_statistical"
[ ] Estrategias activas: incluye esta estrategia
[ ] Sin excepciones en evaluations después de 10 scans
[ ] stats['mean_reversion_statistical']['errors'] == 0
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
