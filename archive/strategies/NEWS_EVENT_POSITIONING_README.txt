# NEWS EVENT POSITIONING - ARCHIVED 2025-11-05

## RAZÓN DE ARCHIVO

Esta estrategia fue archivada porque requiere infraestructura institucional que
actualmente no está disponible en el sistema.

## INFRAESTRUCTURA REQUERIDA PARA REACTIVACIÓN

1. **Calendario Económico con API**
   - Conexión directa a Reuters o Bloomberg Economic Calendar API
   - Latencia < 500ms desde publicación del evento
   - Clasificación automática de impacto esperado (high/medium/low)

2. **Modelos de Natural Language Processing**
   - Clasificador de sentimiento para headlines económicas
   - Comparador actual vs consensus vs previous
   - Detector de "surprise factor" cuantificado

3. **Modelos de Slippage y Spread**
   - Predicción de spread expansion por tipo de evento
   - Modelo de slippage esperado en primeros 30 segundos post-evento
   - Estimación de profundidad del libro durante volatilidad extrema

4. **Halt Rules Automatizadas**
   - Stop trading si spread > 5x normal
   - Stop si latency del feed > 200ms
   - Stop si slippage observado > 2x modelo predicho

## CONDICIONES DE REACTIVACIÓN

Esta estrategia solo debe reactivarse cuando los cuatro componentes de
infraestructura estén completamente implementados y testeados.

## CONTACTO

Para discusión sobre reactivación, contactar al arquitecto del sistema.
