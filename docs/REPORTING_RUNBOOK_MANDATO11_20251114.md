# RUNBOOK OPERATIVO - SISTEMA DE REPORTING INSTITUCIONAL

**Proyecto**: SUBLIMINE TradingSystem
**Mandato**: MANDATO 11
**Fecha**: 2025-11-14
**Responsable**: Jefe de Mesa / Risk Manager

---

## PROCEDIMIENTOS OPERATIVOS

### DIARIO (EOD - End of Day)

**Timing**: 23:00 UTC (después de cierre NY)

**Pasos**:

1. **Generar informe diario**:
   ```bash
   python scripts/generate_reports.py --frequency daily --date $(date +%Y-%m-%d)
   ```

2. **Revisar archivo**:
   - Ubicación: `reports/daily/report_YYYYMMDD.md`
   - Abrir y revisar secciones:
     - ✅ PnL del día (positivo/negativo)
     - ✅ Top/worst trades (identificar outliers)
     - ✅ Riesgo usado vs disponible (< 30% ok, > 40% alerta)
     - ✅ Eventos críticos (slippage, stops en cascada, circuit breakers)

3. **Acciones inmediatas**:
   - **Si PnL < -2%**: Revisar todas las estrategias activas, considerar pausar las perdedoras
   - **Si riesgo > 40%**: Reducir exposición en símbolos con mayor riesgo
   - **Si slippage > 10bps promedio**: Revisar liquidez de símbolos afectados
   - **Si correlation_divergence u otra estrategia pierde 2+ veces consecutivas**: Marcar para revisión semanal

4. **Notificar**:
   - Si eventos críticos: Email a jefe de mesa + risk manager
   - Si todo normal: No acción

**Checklist**:
- [ ] Informe generado
- [ ] PnL revisado
- [ ] Riesgo dentro de límites
- [ ] Eventos críticos documentados
- [ ] Acciones tomadas (si aplica)

---

### SEMANAL (EOW - End of Week)

**Timing**: Domingo 12:00 UTC

**Pasos**:

1. **Generar informe semanal**:
   ```bash
   START=$(date -d "7 days ago" +%Y-%m-%d)
   END=$(date +%Y-%m-%d)
   python scripts/generate_reports.py --frequency weekly --start $START --end $END
   ```

2. **Revisar archivo**:
   - Ubicación: `reports/weekly/report_YYYYMMDD_to_YYYYMMDD.md`
   - Secciones clave:
     - ✅ KPIs semanales (Sharpe, hit rate, trades)
     - ✅ Calibración de QualityScore (correlación Quality-Return)
     - ✅ Distribución de quality en wins vs losses
     - ✅ Señales de decay preliminares

3. **Acciones si necesario**:
   - **Si Sharpe < 1.0**: Revisar estrategias principales, considerar ajustar parámetros
   - **Si correlación Quality-Return < 0.3**: Recalibrar QualityScorer (ver `config/quality_thresholds.yaml`)
   - **Si estrategia con señales de decay**: Cambiar a estado DEGRADED, reducir exposure

4. **Actualizar parámetros**:
   - Ajustar thresholds de estrategias si performance cae
   - Actualizar risk limits si clusters sobrecargados

**Checklist**:
- [ ] Informe generado
- [ ] Sharpe > 1.5 (target)
- [ ] Quality correlation > 0.5 (target)
- [ ] Estrategias DEGRADED marcadas
- [ ] Parámetros ajustados (si aplica)

---

### MENSUAL (EOM - End of Month)

**Timing**: Primer día del mes siguiente, 10:00 UTC

**Pasos**:

1. **Generar informe mensual**:
   ```bash
   MONTH=$(date -d "1 month ago" +%Y-%m)
   python scripts/generate_reports.py --frequency monthly --month $MONTH
   ```

2. **Revisar archivo**:
   - Ubicación: `reports/monthly/report_YYYYMM.md`
   - Secciones clave:
     - ✅ KPIs completos (Sharpe, Sortino, Calmar, MAR)
     - ✅ Max drawdown (profundidad, duración)
     - ✅ Breakdown por clase de activo, estrategia, región
     - ✅ Matriz de correlación entre estrategias (factor crowding)
     - ✅ Anexo de riesgo (límites, rechazos, cumplimiento)

3. **Presentar a comité de riesgo**:
   - Preparar resumen ejecutivo (1 página)
   - Destacar:
     - Performance vs target (Sharpe > 1.5, Calmar > 2.0)
     - Estrategias top performers
     - Estrategias en DEGRADED (candidatas a RETIRED)
     - Uso de límites de riesgo
     - Correlación entre estrategias (> 0.60 = crowding risk)

4. **Decisiones**:
   - **Estrategias DEGRADED**: Decidir si continuar monitoreando o pasar a RETIRED
   - **Estrategias PILOT**: Si performance >target, promover a PRODUCTION
   - **Ajustes de riesgo**: Aumentar/reducir max_exposure_pct por clase/símbolo según performance

**Checklist**:
- [ ] Informe generado
- [ ] Presentación a comité preparada
- [ ] Decisiones sobre lifecycle de estrategias tomadas
- [ ] Ajustes de riesgo aplicados

---

### TRIMESTRAL

**Timing**: Primer lunes del nuevo trimestre

Similar a mensual pero con análisis más profundo:
- Segmentación por regímenes de volatilidad
- Comparación con benchmarks (S&P500, VAMI, etc.)
- Evolución de estrategias (lifecycle transitions)
- Plan de acción para próximo trimestre

---

### ANUAL

**Timing**: Enero (primera semana)

Informe completo para inversores:
- Performance anual completa
- Comparación multi-año (si disponible)
- Análisis de ciclos de mercado
- Estrategias añadidas/retiradas durante el año
- Plan estratégico para próximo año

---

## ALERTAS Y TRIGGERS AUTOMÁTICOS

### Alerta Nivel 1 (Informativa)

**Triggers**:
- PnL diario < -1%
- Slippage promedio > 5bps
- Estrategia con 3+ pérdidas consecutivas

**Acción**: Revisar informes, documentar, no requiere intervención inmediata.

### Alerta Nivel 2 (Warning)

**Triggers**:
- PnL diario < -2%
- Riesgo usado > 40%
- Sharpe semanal < 1.0
- Quality correlation < 0.3
- Estrategia con 5+ pérdidas consecutivas o hit rate < 40%

**Acción**: Intervención requerida en <24h. Ajustar parámetros, reducir exposure, marcar estrategias DEGRADED.

### Alerta Nivel 3 (Critical)

**Triggers**:
- PnL diario < -5%
- Riesgo usado > 50%
- Circuit breaker activado
- Max drawdown > 15%

**Acción**: Intervención inmediata. Pausar trading, revisar sistema completo, notificar a jefe de mesa + CTO + risk committee.

---

## MANTENIMIENTO DEL SISTEMA DE REPORTING

### Semanal

- **Backup de DB**: `pg_dump reporting_db > backups/reporting_YYYYMMDD.sql`
- **Limpiar eventos antiguos**: Archivar eventos >90 días a Parquet/cold storage
- **Verificar espacio en disco**: reports/ debe tener <10GB activos

### Mensual

- **Reindexar DB**: `REINDEX DATABASE reporting_db;`
- **Analizar queries lentas**: Revisar logs de Postgres, optimizar índices si necesario
- **Actualizar documentación**: Si se añaden estrategias/símbolos, actualizar diseño

---

## TROUBLESHOOTING

### "Error: No trades found for date YYYY-MM-DD"

**Causa**: Sin trades ese día (mercados cerrados, sistema pausado)
**Solución**: Normal si es fin de semana o holiday. Verificar logs de trading si día laboral.

### "Error: Database connection failed"

**Causa**: Postgres no disponible
**Solución**:
1. Verificar servicio: `systemctl status postgresql`
2. Reiniciar si necesario: `systemctl restart postgresql`
3. Si persiste, revisar logs: `/var/log/postgresql/`

### "Quality correlation < 0.1 (muy bajo)"

**Causa**: QualityScorer mal calibrado o estrategias no funcionando como esperado
**Solución**:
1. Revisar thresholds de QualityScorer en `config/quality_thresholds.yaml`
2. Comparar quality medio de wins vs losses (gap debe ser >0.10)
3. Si gap <0.05, recalibrar pesos de QualityScorer

### "Slippage > 20bps en múltiples símbolos"

**Causa**: Problemas de liquidez o broker
**Solución**:
1. Verificar estado de símbolos en broker
2. Revisar horarios de trading (evitar rollover, news events)
3. Considerar reducir tamaño de posiciones en símbolos afectados

---

## CONTACTOS

- **Jefe de Mesa**: [email]
- **Risk Manager**: [email]
- **CTO**: [email]
- **Soporte Técnico**: [email]

---

**VERSIÓN**: 1.0
**ÚLTIMA ACTUALIZACIÓN**: 2025-11-14
**PRÓXIMA REVISIÓN**: 2025-12-14
