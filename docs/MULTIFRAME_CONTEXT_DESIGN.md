# MULTIFRAME CONTEXT ENGINE – DISEÑO INSTITUCIONAL

**Proyecto**: SUBLIMINE TradingSystem
**Mandato**: 5 – Síntesis Temporal HTF/MTF/LTF
**Fecha**: 2025-11-13
**Autor**: Sistema SUBLIMINE
**Status**: Design Phase – Institutional Grade

---

## RESUMEN EJECUTIVO

El **MultiFrameContextEngine** es el componente encargado de **orquestar el análisis multi-temporal** del mercado, sintetizando información de marcos temporales altos (HTF: H4, D1), medios (MTF: M15, M5) y bajos (LTF: M1) para:

1. **Identificar régimen estructural** en HTF (tendencia, rango, transición)
2. **Validar contexto táctico** en MTF (swing structure, zonas de liquidez)
3. **Ejecutar timing preciso** en LTF (entry triggers, confirmación microestructural)

**Objetivo**: Asegurar que cada señal de trading esté **alineada temporalmente** desde la estructura macro (HTF) hasta la ejecución micro (LTF), eliminando trades contra tendencia principal o en contextos estructuralmente débiles.

**Principios**:
1. **HTF Governs**: La estructura de marco temporal alto es ley, NO se opera contra ella
2. **MTF Validates**: Marco medio valida zonas de interés y swings operables
3. **LTF Executes**: Marco bajo confirma entry preciso con microestructura favorable
4. **No Contradictions**: Si HTF dice LONG, MTF no puede generar SHORT signals (filtro estricto)
5. **Dynamic Weighting**: Peso de cada timeframe ajustado por régimen (trending vs ranging)

**Restricciones**:
- NO operar señales que contradigan HTF bias
- NO usar timeframes demasiado bajos (<M1) por ruido excesivo
- Manejar latencia: sincronización de múltiples timeframes debe ser <50ms
- Gestionar conflictos: resolución clara cuando MTF y LTF divergen

---

## TABLA DE CONTENIDOS

1. [Arquitectura General](#arquitectura-general)
2. [Componente 1: HTF Structure Analyzer](#componente-1-htf-structure-analyzer)
3. [Componente 2: MTF Context Validator](#componente-2-mtf-context-validator)
4. [Componente 3: LTF Timing Executor](#componente-3-ltf-timing-executor)
5. [Componente 4: TimeFrame Synchronizer](#componente-4-timeframe-synchronizer)
6. [Componente 5: MultiFrame Orchestrator](#componente-5-multiframe-orchestrator)
7. [Reglas de Alineación Temporal](#reglas-de-alineación-temporal)
8. [Integración con Risk Engine](#integración-con-risk-engine)
9. [Manejo de Conflictos](#manejo-de-conflictos)
10. [Implementación y Testing](#implementación-y-testing)

---

## ARQUITECTURA GENERAL

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────────┐
│                MULTIFRAME CONTEXT ENGINE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────┐      ┌────────────┐      ┌────────────┐        │
│  │    HTF     │      │    MTF     │      │    LTF     │        │
│  │  H4, D1    │      │  M15, M5   │      │    M1      │        │
│  │            │      │            │      │            │        │
│  │ Structure  │      │  Context   │      │   Timing   │        │
│  │ Analyzer   │      │ Validator  │      │  Executor  │        │
│  └─────┬──────┘      └──────┬─────┘      └──────┬─────┘        │
│        │                    │                   │               │
│        │ Trend Direction    │ Swing Structure   │ Entry Trigger │
│        │ Key Levels         │ Supply/Demand     │ Confirmation  │
│        │ Market Structure   │ POIs              │ Microstructure│
│        │                    │                   │               │
│        └────────────────────┼───────────────────┘               │
│                             │                                   │
│                             ▼                                   │
│                ┌────────────────────────┐                       │
│                │  TimeFrame Synchronizer│                       │
│                │  (Alignment Check)     │                       │
│                └────────────┬───────────┘                       │
│                             │                                   │
│                             ▼                                   │
│                ┌────────────────────────┐                       │
│                │  MultiFrame            │                       │
│                │  Orchestrator          │                       │
│                │  (Final Decision)      │                       │
│                └────────────┬───────────┘                       │
│                             │                                   │
└─────────────────────────────┼───────────────────────────────────┘
                              │
                              ▼
                   ┌──────────────────────┐
                   │   Signal to          │
                   │   QualityScorer      │
                   │   + Risk Engine      │
                   └──────────────────────┘
```

### Jerarquía de Timeframes

| Categoría | Timeframes | Rol | Datos Clave |
|-----------|-----------|-----|-------------|
| **HTF** (High) | H4, D1 | Identificar tendencia principal, estructura macro, key levels | Trend direction, swing highs/lows, order blocks, FVGs grandes |
| **MTF** (Medium) | M15, M5 | Validar zonas de entrada, refinar swings, identificar POIs | Swing structure, supply/demand zones, mitigation blocks |
| **LTF** (Low) | M1 | Timing de entrada, confirmación microestructural, trigger | BOS/CHoCH, FVGs pequeños, order flow, entry patterns |

**Regla Fundamental**:
```
HTF = Dirección estratégica (¿Hacia dónde vamos?)
MTF = Zona táctica (¿Desde dónde entramos?)
LTF = Timing de ejecución (¿Cuándo exactamente?)
```

---

## COMPONENTE 1: HTF Structure Analyzer

### Definición

El **HTF Structure Analyzer** identifica la **estructura macro** del mercado en marcos temporales altos (H4, D1):

1. **Trend Direction**: Alcista, bajista, o rango
2. **Key Levels**: Swing highs/lows críticos, order blocks institucionales
3. **Market Structure**: Secuencia de HH/HL (alcista) o LH/LL (bajista)
4. **Invalidation Levels**: Niveles que invalidan la estructura actual

**Timeframes Monitorizados**: H4, D1 (primario), H1 (secundario para transiciones)

### Identificación de Trend Direction

**Algoritmo**:

```python
class HTFStructureAnalyzer:
    """
    Analiza estructura macro en timeframes altos (H4, D1).
    """
    def __init__(self, config: Dict[str, Any]):
        self.htf_timeframes = config.get('htf_timeframes', ['H4', 'D1'])
        self.lookback_swings = config.get('lookback_swings', 10)
        self.structure_cache = {}

    def analyze_structure(self, symbol: str, timeframe: str,
                          ohlcv: pd.DataFrame) -> HTFStructure:
        """
        Analiza estructura completa en un timeframe HTF.

        Args:
            symbol: Símbolo (e.g., 'EURUSD')
            timeframe: Timeframe HTF (e.g., 'H4', 'D1')
            ohlcv: DataFrame con datos OHLCV

        Returns:
            HTFStructure con trend, key levels, invalidation
        """
        # 1. Identificar swing points
        swings = self._identify_swing_points(ohlcv)

        # 2. Determinar trend direction
        trend = self._determine_trend(swings)

        # 3. Extraer key levels
        key_levels = self._extract_key_levels(swings, ohlcv)

        # 4. Identificar invalidation levels
        invalidation = self._identify_invalidation_levels(swings, trend)

        # 5. Detectar order blocks institucionales
        order_blocks = self._detect_institutional_order_blocks(ohlcv, trend)

        return HTFStructure(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=ohlcv.index[-1],
            trend_direction=trend,
            key_levels=key_levels,
            invalidation_level=invalidation,
            order_blocks=order_blocks,
            swings=swings,
        )

    def _identify_swing_points(self, ohlcv: pd.DataFrame,
                               window: int = 5) -> List[SwingPoint]:
        """
        Identifica swing highs y lows usando ventana deslizante.

        Swing High: high[i] > high[i-window:i] AND high[i] > high[i+1:i+window+1]
        Swing Low: low[i] < low[i-window:i] AND low[i] < low[i+1:i+window+1]
        """
        swings = []

        for i in range(window, len(ohlcv) - window):
            # Swing High
            if (ohlcv.iloc[i]['high'] == ohlcv.iloc[i-window:i+window+1]['high'].max()):
                swings.append(SwingPoint(
                    index=i,
                    timestamp=ohlcv.index[i],
                    type='HIGH',
                    price=ohlcv.iloc[i]['high'],
                ))

            # Swing Low
            if (ohlcv.iloc[i]['low'] == ohlcv.iloc[i-window:i+window+1]['low'].min()):
                swings.append(SwingPoint(
                    index=i,
                    timestamp=ohlcv.index[i],
                    type='LOW',
                    price=ohlcv.iloc[i]['low'],
                ))

        return sorted(swings, key=lambda x: x.index)

    def _determine_trend(self, swings: List[SwingPoint]) -> str:
        """
        Determina trend direction basado en secuencia de swings.

        Alcista: Secuencia de Higher Highs (HH) y Higher Lows (HL)
        Bajista: Secuencia de Lower Highs (LH) y Lower Lows (LL)
        Rango: No hay secuencia clara
        """
        if len(swings) < 4:
            return 'RANGE'

        # Separar highs y lows
        highs = [s for s in swings if s.type == 'HIGH']
        lows = [s for s in swings if s.type == 'LOW']

        if len(highs) < 2 or len(lows) < 2:
            return 'RANGE'

        # Últimos 3 highs y lows
        recent_highs = highs[-3:]
        recent_lows = lows[-3:]

        # Verificar HH (Higher Highs)
        hh_count = sum(
            1 for i in range(1, len(recent_highs))
            if recent_highs[i].price > recent_highs[i-1].price
        )

        # Verificar HL (Higher Lows)
        hl_count = sum(
            1 for i in range(1, len(recent_lows))
            if recent_lows[i].price > recent_lows[i-1].price
        )

        # Verificar LH (Lower Highs)
        lh_count = sum(
            1 for i in range(1, len(recent_highs))
            if recent_highs[i].price < recent_highs[i-1].price
        )

        # Verificar LL (Lower Lows)
        ll_count = sum(
            1 for i in range(1, len(recent_lows))
            if recent_lows[i].price < recent_lows[i-1].price
        )

        # Decisión
        bullish_score = hh_count + hl_count
        bearish_score = lh_count + ll_count

        if bullish_score >= 3:
            return 'BULLISH'
        elif bearish_score >= 3:
            return 'BEARISH'
        else:
            return 'RANGE'

    def _extract_key_levels(self, swings: List[SwingPoint],
                            ohlcv: pd.DataFrame) -> List[KeyLevel]:
        """
        Extrae key levels (swing highs/lows) que actúan como soporte/resistencia.
        """
        key_levels = []

        # Últimos N swings son key levels
        for swing in swings[-self.lookback_swings:]:
            key_levels.append(KeyLevel(
                price=swing.price,
                type='RESISTANCE' if swing.type == 'HIGH' else 'SUPPORT',
                timestamp=swing.timestamp,
                strength=self._calculate_level_strength(swing, ohlcv),
                timeframe='HTF',
            ))

        return key_levels

    def _calculate_level_strength(self, swing: SwingPoint,
                                   ohlcv: pd.DataFrame) -> float:
        """
        Calcula fuerza del nivel basado en:
        - Número de toques (price revisits)
        - Volumen en el swing
        - Distancia desde precio actual

        Returns:
            Strength [0.0, 1.0]
        """
        # Contar toques: cuántas veces precio ha estado cerca de este nivel
        touches = 0
        threshold = swing.price * 0.001  # 0.1% threshold

        for i in range(len(ohlcv)):
            if abs(ohlcv.iloc[i]['high'] - swing.price) < threshold:
                touches += 1
            if abs(ohlcv.iloc[i]['low'] - swing.price) < threshold:
                touches += 1

        # Normalizar: 1 toque = 0.2, 5+ toques = 1.0
        touch_score = min(touches * 0.2, 1.0)

        # Volumen en el swing (normalizado vs promedio)
        swing_volume = ohlcv.iloc[swing.index]['volume']
        avg_volume = ohlcv['volume'].mean()
        volume_score = min(swing_volume / avg_volume, 2.0) / 2.0

        # Combinar
        strength = 0.6 * touch_score + 0.4 * volume_score

        return np.clip(strength, 0.0, 1.0)

    def _identify_invalidation_levels(self, swings: List[SwingPoint],
                                      trend: str) -> float:
        """
        Identifica nivel de invalidación de estructura actual.

        Alcista: Último swing low
        Bajista: Último swing high
        Rango: No hay invalidación clara
        """
        if trend == 'BULLISH':
            lows = [s for s in swings if s.type == 'LOW']
            return lows[-1].price if lows else None

        elif trend == 'BEARISH':
            highs = [s for s in swings if s.type == 'HIGH']
            return highs[-1].price if highs else None

        else:  # RANGE
            return None

    def _detect_institutional_order_blocks(self, ohlcv: pd.DataFrame,
                                           trend: str) -> List[OrderBlock]:
        """
        Detecta order blocks institucionales en HTF.

        Order Block: Última vela antes de movimiento impulsivo.
        """
        order_blocks = []

        # Identificar movimientos impulsivos (>2% en H4 o >3% en D1)
        threshold = 0.02  # 2%

        for i in range(1, len(ohlcv) - 1):
            move = abs(ohlcv.iloc[i+1]['close'] - ohlcv.iloc[i]['close']) / ohlcv.iloc[i]['close']

            if move >= threshold:
                # Order block es la vela ANTES del impulso
                ob_candle = ohlcv.iloc[i-1]

                order_blocks.append(OrderBlock(
                    high=ob_candle['high'],
                    low=ob_candle['low'],
                    timestamp=ohlcv.index[i-1],
                    direction='BULLISH' if ohlcv.iloc[i+1]['close'] > ohlcv.iloc[i]['close'] else 'BEARISH',
                    timeframe='HTF',
                    strength=move,  # Magnitud del impulso = strength
                ))

        return order_blocks
```

### Output de HTF Structure

```python
@dataclass
class HTFStructure:
    """Estructura macro de HTF para orchestrator."""
    symbol: str
    timeframe: str
    timestamp: datetime
    trend_direction: str           # 'BULLISH', 'BEARISH', 'RANGE'
    key_levels: List[KeyLevel]     # Soporte/resistencia críticos
    invalidation_level: float      # Nivel que invalida estructura
    order_blocks: List[OrderBlock] # Order blocks institucionales
    swings: List[SwingPoint]       # Swing points identificados

    def get_bias(self) -> str:
        """
        Retorna bias direccional para filtro de señales.

        Returns:
            'LONG_ONLY', 'SHORT_ONLY', 'BOTH'
        """
        if self.trend_direction == 'BULLISH':
            return 'LONG_ONLY'
        elif self.trend_direction == 'BEARISH':
            return 'SHORT_ONLY'
        else:  # RANGE
            return 'BOTH'

    def is_signal_aligned(self, signal_direction: str) -> bool:
        """
        Verifica si una señal está alineada con HTF bias.

        Args:
            signal_direction: 'LONG' o 'SHORT'

        Returns:
            True si alineada, False si contraindica
        """
        bias = self.get_bias()

        if bias == 'BOTH':
            return True
        elif bias == 'LONG_ONLY' and signal_direction == 'LONG':
            return True
        elif bias == 'SHORT_ONLY' and signal_direction == 'SHORT':
            return True
        else:
            return False
```

---

## COMPONENTE 2: MTF Context Validator

### Definición

El **MTF Context Validator** analiza **marcos temporales medios** (M15, M5) para:

1. **Validar zonas de entrada**: Identificar supply/demand zones, mitigation blocks, POIs
2. **Refinar swing structure**: Swings intermedios que refinan estructura HTF
3. **Detectar CHoCH/BOS**: Cambios de carácter y breaks de estructura
4. **Confirmar setup táctico**: Validar que precio esté en zona operarable

**Timeframes Monitorizados**: M15, M5

### Identificación de Supply/Demand Zones

**Algoritmo**:

```python
class MTFContextValidator:
    """
    Valida contexto táctico en timeframes medios (M15, M5).
    """
    def __init__(self, config: Dict[str, Any]):
        self.mtf_timeframes = config.get('mtf_timeframes', ['M15', 'M5'])
        self.zone_lookback = config.get('zone_lookback', 50)

    def validate_context(self, symbol: str, timeframe: str,
                         ohlcv: pd.DataFrame, htf_structure: HTFStructure) -> MTFContext:
        """
        Valida contexto MTF considerando estructura HTF.

        Args:
            symbol: Símbolo
            timeframe: Timeframe MTF (e.g., 'M15', 'M5')
            ohlcv: DataFrame con datos OHLCV
            htf_structure: Estructura HTF para alineación

        Returns:
            MTFContext con zonas, swings, CHoCH/BOS
        """
        # 1. Identificar supply/demand zones
        zones = self._identify_supply_demand_zones(ohlcv, htf_structure.trend_direction)

        # 2. Detectar swings intermedios
        swings = self._identify_mtf_swings(ohlcv)

        # 3. Detectar CHoCH y BOS
        structure_breaks = self._detect_structure_breaks(ohlcv, swings)

        # 4. Identificar POIs (Points of Interest)
        pois = self._identify_points_of_interest(ohlcv, zones, htf_structure)

        # 5. Evaluar si precio está en zona operable
        in_tradeable_zone = self._is_price_in_tradeable_zone(
            ohlcv.iloc[-1]['close'],
            zones,
            htf_structure
        )

        return MTFContext(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=ohlcv.index[-1],
            supply_demand_zones=zones,
            swings=swings,
            structure_breaks=structure_breaks,
            points_of_interest=pois,
            in_tradeable_zone=in_tradeable_zone,
            htf_alignment=htf_structure.trend_direction,
        )

    def _identify_supply_demand_zones(self, ohlcv: pd.DataFrame,
                                      htf_trend: str) -> List[Zone]:
        """
        Identifica zonas de supply (resistencia) y demand (soporte) en MTF.

        Demand Zone: Base de movimiento alcista fuerte
        Supply Zone: Tope de movimiento bajista fuerte
        """
        zones = []

        # Buscar movimientos impulsivos (>1% en M15)
        threshold = 0.01

        for i in range(10, len(ohlcv) - 1):
            move_pct = (ohlcv.iloc[i+1]['close'] - ohlcv.iloc[i]['close']) / ohlcv.iloc[i]['close']

            # Movimiento alcista fuerte → Demand zone en base
            if move_pct >= threshold:
                # Base = últimas 2-3 velas antes del impulso
                base_high = ohlcv.iloc[i-2:i+1]['high'].max()
                base_low = ohlcv.iloc[i-2:i+1]['low'].min()

                zones.append(Zone(
                    high=base_high,
                    low=base_low,
                    type='DEMAND',
                    timestamp=ohlcv.index[i],
                    strength=abs(move_pct),
                    timeframe='MTF',
                ))

            # Movimiento bajista fuerte → Supply zone en tope
            elif move_pct <= -threshold:
                top_high = ohlcv.iloc[i-2:i+1]['high'].max()
                top_low = ohlcv.iloc[i-2:i+1]['low'].min()

                zones.append(Zone(
                    high=top_high,
                    low=top_low,
                    type='SUPPLY',
                    timestamp=ohlcv.index[i],
                    strength=abs(move_pct),
                    timeframe='MTF',
                ))

        # Filtrar zonas: mantener solo últimas N y más fuertes
        zones = sorted(zones, key=lambda z: z.strength, reverse=True)[:self.zone_lookback]

        return zones

    def _identify_mtf_swings(self, ohlcv: pd.DataFrame,
                             window: int = 3) -> List[SwingPoint]:
        """
        Identifica swings intermedios en MTF (ventana más corta que HTF).
        """
        swings = []

        for i in range(window, len(ohlcv) - window):
            # Swing High
            if (ohlcv.iloc[i]['high'] == ohlcv.iloc[i-window:i+window+1]['high'].max()):
                swings.append(SwingPoint(
                    index=i,
                    timestamp=ohlcv.index[i],
                    type='HIGH',
                    price=ohlcv.iloc[i]['high'],
                ))

            # Swing Low
            if (ohlcv.iloc[i]['low'] == ohlcv.iloc[i-window:i+window+1]['low'].min()):
                swings.append(SwingPoint(
                    index=i,
                    timestamp=ohlcv.index[i],
                    type='LOW',
                    price=ohlcv.iloc[i]['low'],
                ))

        return sorted(swings, key=lambda x: x.index)

    def _detect_structure_breaks(self, ohlcv: pd.DataFrame,
                                 swings: List[SwingPoint]) -> List[StructureBreak]:
        """
        Detecta CHoCH (Change of Character) y BOS (Break of Structure).

        CHoCH: Rotura del último swing interno (posible reversión)
        BOS: Rotura de swing externo (continuación de tendencia)
        """
        breaks = []

        if len(swings) < 3:
            return breaks

        # Separar highs y lows
        highs = [s for s in swings if s.type == 'HIGH']
        lows = [s for s in swings if s.type == 'LOW']

        # Detectar BOS alcista: precio rompe último swing high
        if len(highs) >= 2:
            last_high = highs[-1]
            current_price = ohlcv.iloc[-1]['close']

            if current_price > last_high.price:
                breaks.append(StructureBreak(
                    type='BOS',
                    direction='BULLISH',
                    level=last_high.price,
                    timestamp=ohlcv.index[-1],
                    timeframe='MTF',
                ))

        # Detectar BOS bajista: precio rompe último swing low
        if len(lows) >= 2:
            last_low = lows[-1]
            current_price = ohlcv.iloc[-1]['close']

            if current_price < last_low.price:
                breaks.append(StructureBreak(
                    type='BOS',
                    direction='BEARISH',
                    level=last_low.price,
                    timestamp=ohlcv.index[-1],
                    timeframe='MTF',
                ))

        # CHoCH: detectar cambios de carácter (lógica más compleja, simplificado aquí)
        # ...

        return breaks

    def _identify_points_of_interest(self, ohlcv: pd.DataFrame,
                                     zones: List[Zone],
                                     htf_structure: HTFStructure) -> List[POI]:
        """
        Identifica Points of Interest (POIs) para posible entrada.

        POI: Intersección de zonas MTF con key levels HTF.
        """
        pois = []
        current_price = ohlcv.iloc[-1]['close']

        # POIs son zonas MTF que coinciden con key levels HTF
        for zone in zones:
            for level in htf_structure.key_levels:
                # Verificar si level HTF está dentro de zona MTF
                if zone.low <= level.price <= zone.high:
                    # Calcular distancia desde precio actual
                    distance = abs(current_price - level.price) / current_price

                    pois.append(POI(
                        price=level.price,
                        zone=zone,
                        level=level,
                        type='CONFLUENCE',
                        distance_from_price=distance,
                        quality=zone.strength * level.strength,  # Product de strengths
                    ))

        return sorted(pois, key=lambda p: p.quality, reverse=True)

    def _is_price_in_tradeable_zone(self, current_price: float,
                                    zones: List[Zone],
                                    htf_structure: HTFStructure) -> bool:
        """
        Verifica si precio actual está en una zona operable (demand o supply).

        Returns:
            True si precio está en zona operable alineada con HTF
        """
        htf_bias = htf_structure.get_bias()

        for zone in zones:
            # Verificar si precio está dentro de zona
            if zone.low <= current_price <= zone.high:
                # Verificar alineación con HTF
                if htf_bias == 'LONG_ONLY' and zone.type == 'DEMAND':
                    return True
                elif htf_bias == 'SHORT_ONLY' and zone.type == 'SUPPLY':
                    return True
                elif htf_bias == 'BOTH':
                    return True

        return False
```

### Output de MTF Context

```python
@dataclass
class MTFContext:
    """Contexto táctico de MTF para orchestrator."""
    symbol: str
    timeframe: str
    timestamp: datetime
    supply_demand_zones: List[Zone]
    swings: List[SwingPoint]
    structure_breaks: List[StructureBreak]
    points_of_interest: List[POI]
    in_tradeable_zone: bool
    htf_alignment: str             # Trend HTF para referencia

    def get_active_zones(self, current_price: float,
                        distance_threshold: float = 0.005) -> List[Zone]:
        """
        Retorna zonas activas (cerca del precio actual).

        Args:
            current_price: Precio actual
            distance_threshold: Distancia máxima (0.5% por defecto)

        Returns:
            Lista de zonas cercanas
        """
        active_zones = []

        for zone in self.supply_demand_zones:
            zone_mid = (zone.high + zone.low) / 2.0
            distance = abs(current_price - zone_mid) / current_price

            if distance <= distance_threshold:
                active_zones.append(zone)

        return active_zones

    def has_recent_structure_break(self, direction: str,
                                   lookback_minutes: int = 60) -> bool:
        """
        Verifica si ha habido BOS/CHoCH reciente en la dirección dada.
        """
        cutoff_time = datetime.now() - timedelta(minutes=lookback_minutes)

        for break_event in self.structure_breaks:
            if break_event.timestamp >= cutoff_time and break_event.direction == direction:
                return True

        return False
```

---

## COMPONENTE 3: LTF Timing Executor

### Definición

El **LTF Timing Executor** opera en **marco temporal bajo** (M1) para:

1. **Confirmar entry trigger**: Patrón específico que activa entrada (BOS, FVG fill, etc.)
2. **Validar microestructura**: Order flow y VPIN favorables
3. **Ejecutar timing preciso**: Entry al pip óptimo

**Timeframe Monitorizado**: M1 (principal), M5 (validación cruzada)

### Detección de Entry Triggers

**Triggers válidos**:
- **BOS (Break of Structure)**: Rotura de último swing low (LONG) o high (SHORT)
- **FVG Fill**: Precio llena Fair Value Gap y rechaza
- **Mitigation**: Precio visita order block y rechaza
- **Liquidity Sweep**: Sweep de liquidez + reversión

```python
class LTFTimingExecutor:
    """
    Ejecuta timing preciso en LTF (M1) con confirmación microestructural.
    """
    def __init__(self, config: Dict[str, Any],
                 microstructure_engine: MicrostructureEngine):
        self.ltf_timeframe = config.get('ltf_timeframe', 'M1')
        self.microstructure_engine = microstructure_engine
        self.trigger_patterns = config.get('trigger_patterns', ['BOS', 'FVG', 'MITIGATION'])

    def evaluate_entry_timing(self, symbol: str, ohlcv: pd.DataFrame,
                              mtf_context: MTFContext,
                              htf_structure: HTFStructure) -> Optional[LTFTiming]:
        """
        Evalúa si hay trigger de entrada válido en LTF.

        Args:
            symbol: Símbolo
            ohlcv: DataFrame M1 con datos OHLCV
            mtf_context: Contexto MTF para alineación
            htf_structure: Estructura HTF para alineación

        Returns:
            LTFTiming si hay trigger válido, None en caso contrario
        """
        # 1. Verificar que precio esté en zona operable (MTF)
        if not mtf_context.in_tradeable_zone:
            return None

        # 2. Detectar triggers en LTF
        triggers = self._detect_entry_triggers(ohlcv, htf_structure.get_bias())

        if not triggers:
            return None

        # 3. Validar microestructura
        microstructure_score = self.microstructure_engine.get_current_score(
            symbol=symbol,
            direction=triggers[0].direction  # Usar primer trigger
        )

        if microstructure_score < 0.50:
            # Microestructura desfavorable, no entrar
            return None

        # 4. Confirmar alineación temporal completa
        aligned = self._verify_temporal_alignment(
            triggers[0],
            mtf_context,
            htf_structure
        )

        if not aligned:
            return None

        # 5. Retornar timing válido
        return LTFTiming(
            symbol=symbol,
            timestamp=ohlcv.index[-1],
            trigger=triggers[0],
            entry_price=ohlcv.iloc[-1]['close'],
            microstructure_score=microstructure_score,
            mtf_aligned=True,
            htf_aligned=True,
            confidence=self._calculate_timing_confidence(
                triggers[0],
                microstructure_score,
                mtf_context
            ),
        )

    def _detect_entry_triggers(self, ohlcv: pd.DataFrame,
                               htf_bias: str) -> List[EntryTrigger]:
        """
        Detecta entry triggers válidos en LTF.

        Returns:
            Lista de triggers detectados (ordenados por calidad)
        """
        triggers = []

        # Trigger 1: BOS (Break of Structure)
        if 'BOS' in self.trigger_patterns:
            bos_trigger = self._detect_bos_trigger(ohlcv, htf_bias)
            if bos_trigger:
                triggers.append(bos_trigger)

        # Trigger 2: FVG Fill
        if 'FVG' in self.trigger_patterns:
            fvg_trigger = self._detect_fvg_fill_trigger(ohlcv, htf_bias)
            if fvg_trigger:
                triggers.append(fvg_trigger)

        # Trigger 3: Mitigation
        if 'MITIGATION' in self.trigger_patterns:
            mitigation_trigger = self._detect_mitigation_trigger(ohlcv, htf_bias)
            if mitigation_trigger:
                triggers.append(mitigation_trigger)

        # Ordenar por calidad
        return sorted(triggers, key=lambda t: t.quality, reverse=True)

    def _detect_bos_trigger(self, ohlcv: pd.DataFrame, htf_bias: str) -> Optional[EntryTrigger]:
        """
        Detecta BOS (Break of Structure) en LTF.

        BOS LONG: Precio rompe último swing high interno
        BOS SHORT: Precio rompe último swing low interno
        """
        # Identificar swings en LTF (ventana muy corta: 2-3 velas)
        swings = self._identify_ltf_swings(ohlcv, window=2)

        if len(swings) < 2:
            return None

        current_price = ohlcv.iloc[-1]['close']
        current_high = ohlcv.iloc[-1]['high']
        current_low = ohlcv.iloc[-1]['low']

        # BOS LONG
        if htf_bias in ['LONG_ONLY', 'BOTH']:
            highs = [s for s in swings if s.type == 'HIGH']
            if highs:
                last_high = highs[-1]
                if current_high > last_high.price:
                    return EntryTrigger(
                        type='BOS',
                        direction='LONG',
                        level=last_high.price,
                        timestamp=ohlcv.index[-1],
                        quality=0.85,  # BOS es trigger de alta calidad
                    )

        # BOS SHORT
        if htf_bias in ['SHORT_ONLY', 'BOTH']:
            lows = [s for s in swings if s.type == 'LOW']
            if lows:
                last_low = lows[-1]
                if current_low < last_low.price:
                    return EntryTrigger(
                        type='BOS',
                        direction='SHORT',
                        level=last_low.price,
                        timestamp=ohlcv.index[-1],
                        quality=0.85,
                    )

        return None

    def _detect_fvg_fill_trigger(self, ohlcv: pd.DataFrame, htf_bias: str) -> Optional[EntryTrigger]:
        """
        Detecta FVG (Fair Value Gap) fill + rejection.

        FVG: Gap entre vela[i-2].low y vela[i].high (alcista) o viceversa (bajista)
        Trigger: Precio llena FVG y rechaza (vela de reversión)
        """
        if len(ohlcv) < 5:
            return None

        # Buscar FVGs recientes (últimas 10 velas)
        for i in range(len(ohlcv) - 3, max(len(ohlcv) - 13, 2), -1):
            # FVG Alcista (bullish)
            if htf_bias in ['LONG_ONLY', 'BOTH']:
                gap_high = ohlcv.iloc[i-2]['low']
                gap_low = ohlcv.iloc[i]['high']

                if gap_high > gap_low:
                    # Hay FVG alcista
                    current_low = ohlcv.iloc[-1]['low']
                    current_close = ohlcv.iloc[-1]['close']

                    # Verificar fill + rejection
                    if current_low <= gap_low and current_close > (gap_high + gap_low) / 2:
                        return EntryTrigger(
                            type='FVG_FILL',
                            direction='LONG',
                            level=(gap_high + gap_low) / 2,
                            timestamp=ohlcv.index[-1],
                            quality=0.75,
                        )

            # FVG Bajista (bearish)
            if htf_bias in ['SHORT_ONLY', 'BOTH']:
                gap_low = ohlcv.iloc[i-2]['high']
                gap_high = ohlcv.iloc[i]['low']

                if gap_low < gap_high:
                    # Hay FVG bajista
                    current_high = ohlcv.iloc[-1]['high']
                    current_close = ohlcv.iloc[-1]['close']

                    # Verificar fill + rejection
                    if current_high >= gap_high and current_close < (gap_high + gap_low) / 2:
                        return EntryTrigger(
                            type='FVG_FILL',
                            direction='SHORT',
                            level=(gap_high + gap_low) / 2,
                            timestamp=ohlcv.index[-1],
                            quality=0.75,
                        )

        return None

    def _detect_mitigation_trigger(self, ohlcv: pd.DataFrame, htf_bias: str) -> Optional[EntryTrigger]:
        """
        Detecta mitigation: precio visita order block y rechaza.
        """
        # Simplificado: buscar últimas 2-3 velas de reversión
        if len(ohlcv) < 5:
            return None

        # Mitigation LONG: precio baja a OB alcista y rechaza
        if htf_bias in ['LONG_ONLY', 'BOTH']:
            # Buscar vela alcista fuerte (posible OB)
            for i in range(len(ohlcv) - 10, len(ohlcv) - 3):
                candle = ohlcv.iloc[i]
                body = candle['close'] - candle['open']

                if body > 0 and body / candle['open'] > 0.005:  # >0.5% body alcista
                    # OB identificado
                    ob_high = candle['high']
                    ob_low = candle['low']

                    # Verificar si precio actual ha visitado y rechazado
                    current = ohlcv.iloc[-1]
                    if current['low'] <= ob_high and current['close'] > ob_high:
                        return EntryTrigger(
                            type='MITIGATION',
                            direction='LONG',
                            level=(ob_high + ob_low) / 2,
                            timestamp=ohlcv.index[-1],
                            quality=0.70,
                        )

        # Mitigation SHORT: precio sube a OB bajista y rechaza
        if htf_bias in ['SHORT_ONLY', 'BOTH']:
            for i in range(len(ohlcv) - 10, len(ohlcv) - 3):
                candle = ohlcv.iloc[i]
                body = candle['open'] - candle['close']

                if body > 0 and body / candle['open'] > 0.005:  # >0.5% body bajista
                    ob_high = candle['high']
                    ob_low = candle['low']

                    current = ohlcv.iloc[-1]
                    if current['high'] >= ob_low and current['close'] < ob_low:
                        return EntryTrigger(
                            type='MITIGATION',
                            direction='SHORT',
                            level=(ob_high + ob_low) / 2,
                            timestamp=ohlcv.index[-1],
                            quality=0.70,
                        )

        return None

    def _identify_ltf_swings(self, ohlcv: pd.DataFrame, window: int = 2) -> List[SwingPoint]:
        """
        Identifica swings en LTF (ventana muy corta para timing preciso).
        """
        swings = []

        for i in range(window, len(ohlcv) - window):
            if (ohlcv.iloc[i]['high'] == ohlcv.iloc[i-window:i+window+1]['high'].max()):
                swings.append(SwingPoint(
                    index=i,
                    timestamp=ohlcv.index[i],
                    type='HIGH',
                    price=ohlcv.iloc[i]['high'],
                ))

            if (ohlcv.iloc[i]['low'] == ohlcv.iloc[i-window:i+window+1]['low'].min()):
                swings.append(SwingPoint(
                    index=i,
                    timestamp=ohlcv.index[i],
                    type='LOW',
                    price=ohlcv.iloc[i]['low'],
                ))

        return sorted(swings, key=lambda x: x.index)

    def _verify_temporal_alignment(self, trigger: EntryTrigger,
                                   mtf_context: MTFContext,
                                   htf_structure: HTFStructure) -> bool:
        """
        Verifica alineación temporal completa: LTF → MTF → HTF.

        Returns:
            True si hay alineación completa
        """
        # Verificar HTF
        if not htf_structure.is_signal_aligned(trigger.direction):
            return False

        # Verificar MTF: debe haber zona activa en dirección correcta
        htf_bias = htf_structure.get_bias()

        if htf_bias == 'LONG_ONLY' and trigger.direction == 'LONG':
            # Verificar que haya demand zone cercana
            demand_zones = [z for z in mtf_context.supply_demand_zones if z.type == 'DEMAND']
            if not demand_zones:
                return False

        elif htf_bias == 'SHORT_ONLY' and trigger.direction == 'SHORT':
            # Verificar que haya supply zone cercana
            supply_zones = [z for z in mtf_context.supply_demand_zones if z.type == 'SUPPLY']
            if not supply_zones:
                return False

        return True

    def _calculate_timing_confidence(self, trigger: EntryTrigger,
                                     microstructure_score: float,
                                     mtf_context: MTFContext) -> float:
        """
        Calcula confianza del timing [0.0, 1.0].

        Combina:
        - Calidad del trigger (0.70-0.85)
        - Microstructure score (0.0-1.0)
        - Presencia de POIs en MTF
        """
        # Componente 1: Trigger quality (40%)
        trigger_component = 0.40 * trigger.quality

        # Componente 2: Microstructure (40%)
        microstructure_component = 0.40 * microstructure_score

        # Componente 3: POI proximity (20%)
        poi_score = 1.0 if mtf_context.points_of_interest else 0.5
        poi_component = 0.20 * poi_score

        confidence = trigger_component + microstructure_component + poi_component

        return np.clip(confidence, 0.0, 1.0)
```

### Output de LTF Timing

```python
@dataclass
class LTFTiming:
    """Timing de ejecución en LTF para orchestrator."""
    symbol: str
    timestamp: datetime
    trigger: EntryTrigger           # BOS, FVG, MITIGATION, etc.
    entry_price: float
    microstructure_score: float     # Score de microestructura [0-1]
    mtf_aligned: bool               # Alineación con MTF
    htf_aligned: bool               # Alineación con HTF
    confidence: float               # [0.0, 1.0]

    def is_valid_entry(self, min_confidence: float = 0.65) -> bool:
        """
        Verifica si timing es válido para entrada.

        Requiere:
        - Confidence >= min_confidence
        - MTF aligned
        - HTF aligned
        - Microstructure score >= 0.50
        """
        return (
            self.confidence >= min_confidence and
            self.mtf_aligned and
            self.htf_aligned and
            self.microstructure_score >= 0.50
        )
```

---

## COMPONENTE 4: TimeFrame Synchronizer

### Definición

El **TimeFrame Synchronizer** asegura que los datos de HTF, MTF y LTF estén **sincronizados temporalmente** y que las actualizaciones se propaguen correctamente.

**Desafíos**:
- HTF (H4, D1) actualiza cada 4 horas / 1 día
- MTF (M15, M5) actualiza cada 15 / 5 minutos
- LTF (M1) actualiza cada 1 minuto

**Solución**: Cache con timestamps y triggers de actualización solo cuando cambia la vela correspondiente.

```python
class TimeFrameSynchronizer:
    """
    Sincroniza análisis de múltiples timeframes con mínima latencia.
    """
    def __init__(self, config: Dict[str, Any]):
        self.htf_analyzer = HTFStructureAnalyzer(config['htf'])
        self.mtf_validator = MTFContextValidator(config['mtf'])
        self.ltf_executor = LTFTimingExecutor(config['ltf'], config['microstructure_engine'])

        # Cache de análisis con timestamps
        self.htf_cache = {}  # {symbol: (HTFStructure, last_update_time)}
        self.mtf_cache = {}  # {symbol: (MTFContext, last_update_time)}

        # Intervalos de actualización
        self.htf_update_interval = timedelta(hours=4)  # H4
        self.mtf_update_interval = timedelta(minutes=15)  # M15

    def get_synchronized_context(self, symbol: str,
                                 market_data: Dict[str, pd.DataFrame]) -> SynchronizedContext:
        """
        Obtiene contexto sincronizado de HTF, MTF, LTF.

        Args:
            symbol: Símbolo
            market_data: Dict con DataFrames para cada timeframe
                         {'H4': df_h4, 'M15': df_m15, 'M1': df_m1, ...}

        Returns:
            SynchronizedContext con análisis de todos los timeframes
        """
        current_time = datetime.now()

        # HTF: actualizar solo si pasó intervalo o no existe cache
        if self._should_update_htf(symbol, current_time):
            htf_structure = self.htf_analyzer.analyze_structure(
                symbol=symbol,
                timeframe='H4',
                ohlcv=market_data['H4']
            )
            self.htf_cache[symbol] = (htf_structure, current_time)
        else:
            htf_structure = self.htf_cache[symbol][0]

        # MTF: actualizar si pasó intervalo
        if self._should_update_mtf(symbol, current_time):
            mtf_context = self.mtf_validator.validate_context(
                symbol=symbol,
                timeframe='M15',
                ohlcv=market_data['M15'],
                htf_structure=htf_structure
            )
            self.mtf_cache[symbol] = (mtf_context, current_time)
        else:
            mtf_context = self.mtf_cache[symbol][0]

        # LTF: siempre actualizar (M1 es rápido)
        ltf_timing = self.ltf_executor.evaluate_entry_timing(
            symbol=symbol,
            ohlcv=market_data['M1'],
            mtf_context=mtf_context,
            htf_structure=htf_structure
        )

        return SynchronizedContext(
            symbol=symbol,
            timestamp=current_time,
            htf_structure=htf_structure,
            mtf_context=mtf_context,
            ltf_timing=ltf_timing,
        )

    def _should_update_htf(self, symbol: str, current_time: datetime) -> bool:
        """
        Verifica si debe actualizarse análisis HTF.
        """
        if symbol not in self.htf_cache:
            return True

        last_update = self.htf_cache[symbol][1]
        return (current_time - last_update) >= self.htf_update_interval

    def _should_update_mtf(self, symbol: str, current_time: datetime) -> bool:
        """
        Verifica si debe actualizarse análisis MTF.
        """
        if symbol not in self.mtf_cache:
            return True

        last_update = self.mtf_cache[symbol][1]
        return (current_time - last_update) >= self.mtf_update_interval
```

---

## COMPONENTE 5: MultiFrame Orchestrator

### Definición

El **MultiFrame Orchestrator** es el componente principal que **orquesta la decisión final** de trading considerando HTF, MTF y LTF de forma integrada.

**Responsabilidades**:
1. Verificar alineación temporal completa
2. Asignar pesos dinámicos según régimen de mercado
3. Generar señal final con calidad ajustada por multi-timeframe
4. Integrar con QualityScorer y Risk Engine

```python
class MultiFrameOrchestrator:
    """
    Orquesta análisis multi-temporal y genera señales integradas.
    """
    def __init__(self, config: Dict[str, Any]):
        self.synchronizer = TimeFrameSynchronizer(config)
        self.config = config

        # Pesos por defecto (ajustables dinámicamente)
        self.weights = {
            'htf': 0.50,  # HTF tiene mayor peso (estructura macro)
            'mtf': 0.30,  # MTF valida táctica
            'ltf': 0.20,  # LTF confirma timing
        }

    def evaluate_multiframe_signal(self, signal: Signal,
                                   market_data: Dict[str, pd.DataFrame]) -> MultiFrameScore:
        """
        Evalúa señal considerando contexto multi-temporal.

        Args:
            signal: Señal generada por estrategia
            market_data: Datos OHLCV de todos los timeframes

        Returns:
            MultiFrameScore con alineación, pesos, score final
        """
        # 1. Obtener contexto sincronizado
        context = self.synchronizer.get_synchronized_context(
            symbol=signal.symbol,
            market_data=market_data
        )

        # 2. Verificar alineación temporal estricta
        alignment_check = self._check_temporal_alignment(signal, context)

        if not alignment_check['aligned']:
            # RECHAZO: señal no alineada temporalmente
            return MultiFrameScore(
                symbol=signal.symbol,
                signal_id=signal.id,
                aligned=False,
                rejection_reason=alignment_check['reason'],
                htf_score=0.0,
                mtf_score=0.0,
                ltf_score=0.0,
                final_score=0.0,
            )

        # 3. Calcular scores individuales
        htf_score = self._calculate_htf_score(signal, context.htf_structure)
        mtf_score = self._calculate_mtf_score(signal, context.mtf_context)
        ltf_score = self._calculate_ltf_score(signal, context.ltf_timing)

        # 4. Ajustar pesos dinámicamente según régimen
        adjusted_weights = self._adjust_weights_by_regime(context.htf_structure.trend_direction)

        # 5. Calcular score final
        final_score = (
            adjusted_weights['htf'] * htf_score +
            adjusted_weights['mtf'] * mtf_score +
            adjusted_weights['ltf'] * ltf_score
        )

        return MultiFrameScore(
            symbol=signal.symbol,
            signal_id=signal.id,
            aligned=True,
            rejection_reason=None,
            htf_score=htf_score,
            mtf_score=mtf_score,
            ltf_score=ltf_score,
            final_score=final_score,
            weights=adjusted_weights,
            context=context,
        )

    def _check_temporal_alignment(self, signal: Signal,
                                  context: SynchronizedContext) -> Dict[str, Any]:
        """
        Verifica alineación temporal estricta.

        Returns:
            {'aligned': bool, 'reason': str}
        """
        # Check 1: HTF alignment
        if not context.htf_structure.is_signal_aligned(signal.direction):
            return {
                'aligned': False,
                'reason': f'HTF {context.htf_structure.trend_direction} contradice señal {signal.direction}'
            }

        # Check 2: MTF tradeable zone
        if not context.mtf_context.in_tradeable_zone:
            return {
                'aligned': False,
                'reason': 'Precio fuera de zona operable en MTF'
            }

        # Check 3: LTF timing (si existe)
        if context.ltf_timing is not None:
            if not context.ltf_timing.htf_aligned or not context.ltf_timing.mtf_aligned:
                return {
                    'aligned': False,
                    'reason': 'LTF timing no alineado con HTF/MTF'
                }

        return {'aligned': True, 'reason': None}

    def _calculate_htf_score(self, signal: Signal, htf_structure: HTFStructure) -> float:
        """
        Calcula score HTF [0.0, 1.0].

        Considera:
        - Alineación con trend
        - Distancia a invalidation level
        - Presencia de order blocks en dirección
        """
        score = 0.0

        # Componente 1: Trend alignment (50%)
        if htf_structure.trend_direction == 'BULLISH' and signal.direction == 'LONG':
            score += 0.50
        elif htf_structure.trend_direction == 'BEARISH' and signal.direction == 'SHORT':
            score += 0.50
        elif htf_structure.trend_direction == 'RANGE':
            score += 0.25  # Neutral

        # Componente 2: Distancia a invalidation (30%)
        if htf_structure.invalidation_level:
            distance = abs(signal.entry_price - htf_structure.invalidation_level) / signal.entry_price

            # Penalizar si muy cerca de invalidación (<1%)
            if distance < 0.01:
                distance_score = 0.0
            elif distance < 0.02:
                distance_score = 0.5
            else:
                distance_score = 1.0

            score += 0.30 * distance_score

        # Componente 3: Order blocks alineados (20%)
        aligned_obs = [
            ob for ob in htf_structure.order_blocks
            if (signal.direction == 'LONG' and ob.direction == 'BULLISH') or
               (signal.direction == 'SHORT' and ob.direction == 'BEARISH')
        ]

        ob_score = min(len(aligned_obs) * 0.33, 1.0)  # 3+ OBs = 1.0
        score += 0.20 * ob_score

        return np.clip(score, 0.0, 1.0)

    def _calculate_mtf_score(self, signal: Signal, mtf_context: MTFContext) -> float:
        """
        Calcula score MTF [0.0, 1.0].

        Considera:
        - Presencia de POIs de calidad
        - Structure breaks recientes en dirección
        - Zonas activas alineadas
        """
        score = 0.0

        # Componente 1: POIs (40%)
        if mtf_context.points_of_interest:
            # Usar calidad del mejor POI
            best_poi_quality = max(poi.quality for poi in mtf_context.points_of_interest)
            score += 0.40 * best_poi_quality

        # Componente 2: Structure breaks (30%)
        if mtf_context.has_recent_structure_break(signal.direction.upper(), lookback_minutes=60):
            score += 0.30

        # Componente 3: Zonas activas (30%)
        active_zones = mtf_context.get_active_zones(signal.entry_price, distance_threshold=0.005)

        if active_zones:
            # Verificar alineación de zona con señal
            aligned_zones = [
                z for z in active_zones
                if (signal.direction == 'LONG' and z.type == 'DEMAND') or
                   (signal.direction == 'SHORT' and z.type == 'SUPPLY')
            ]

            if aligned_zones:
                zone_score = max(z.strength for z in aligned_zones)
                score += 0.30 * zone_score

        return np.clip(score, 0.0, 1.0)

    def _calculate_ltf_score(self, signal: Signal, ltf_timing: Optional[LTFTiming]) -> float:
        """
        Calcula score LTF [0.0, 1.0].

        Considera:
        - Presencia de timing válido
        - Confidence del timing
        - Microstructure score
        """
        if ltf_timing is None:
            return 0.50  # Neutral si no hay timing LTF

        if not ltf_timing.is_valid_entry():
            return 0.30  # Penalizar timing inválido

        # Score = promedio de confidence y microstructure
        score = 0.5 * ltf_timing.confidence + 0.5 * ltf_timing.microstructure_score

        return np.clip(score, 0.0, 1.0)

    def _adjust_weights_by_regime(self, trend: str) -> Dict[str, float]:
        """
        Ajusta pesos según régimen de mercado.

        Trending: Mayor peso a HTF (estructura macro domina)
        Ranging: Mayor peso a MTF/LTF (timing más importante)
        """
        if trend in ['BULLISH', 'BEARISH']:
            # Trending: HTF domina
            return {
                'htf': 0.55,
                'mtf': 0.25,
                'ltf': 0.20,
            }
        else:  # RANGE
            # Ranging: MTF/LTF más relevantes
            return {
                'htf': 0.35,
                'mtf': 0.35,
                'ltf': 0.30,
            }
```

### Output de MultiFrame Orchestrator

```python
@dataclass
class MultiFrameScore:
    """Score final multi-temporal para QualityScorer."""
    symbol: str
    signal_id: str
    aligned: bool                   # True si pasa alignment check
    rejection_reason: Optional[str] # Razón de rechazo si aligned=False
    htf_score: float                # [0.0, 1.0]
    mtf_score: float                # [0.0, 1.0]
    ltf_score: float                # [0.0, 1.0]
    final_score: float              # [0.0, 1.0] ponderado
    weights: Dict[str, float]       # Pesos aplicados
    context: SynchronizedContext    # Contexto completo para auditoría

    def get_enriched_quality_score_inputs(self) -> Dict[str, Any]:
        """
        Genera inputs para enriquecer QualityScorer.

        El final_score puede usarse como:
        - Boost al signal_score del QualityScorer
        - Ajuste al microstructure_score
        - Factor de multiplicación del Quality Score total
        """
        return {
            'multiframe_aligned': self.aligned,
            'multiframe_score': self.final_score,
            'htf_trend': self.context.htf_structure.trend_direction,
            'mtf_in_zone': self.context.mtf_context.in_tradeable_zone,
            'ltf_timing_valid': self.context.ltf_timing.is_valid_entry() if self.context.ltf_timing else False,
        }
```

---

## REGLAS DE ALINEACIÓN TEMPORAL

### Regla 1: HTF Governs (HTF manda)

```
SI HTF = BULLISH → SOLO señales LONG permitidas
SI HTF = BEARISH → SOLO señales SHORT permitidas
SI HTF = RANGE → Ambas direcciones permitidas (con cautela)
```

**Implementación**:
```python
def filter_signal_by_htf(signal: Signal, htf_structure: HTFStructure) -> bool:
    """Filtro estricto por HTF."""
    return htf_structure.is_signal_aligned(signal.direction)
```

### Regla 2: MTF Validates Zone (MTF valida zona)

```
Señal LONG → Precio debe estar en DEMAND zone (MTF)
Señal SHORT → Precio debe estar en SUPPLY zone (MTF)
```

**Implementación**:
```python
def validate_signal_zone(signal: Signal, mtf_context: MTFContext) -> bool:
    """Valida que precio esté en zona operable."""
    return mtf_context.in_tradeable_zone
```

### Regla 3: LTF Confirms Timing (LTF confirma timing)

```
Entry solo si:
  - Trigger LTF presente (BOS, FVG, Mitigation)
  - Microstructure score >= 0.50
  - Confidence >= 0.65
```

**Implementación**:
```python
def confirm_entry_timing(ltf_timing: Optional[LTFTiming]) -> bool:
    """Confirma timing de entrada."""
    if ltf_timing is None:
        return False
    return ltf_timing.is_valid_entry(min_confidence=0.65)
```

### Regla 4: No Contradictions (Sin contradicciones)

```
SI HTF BULLISH + MTF DEMAND + LTF BOS LONG → ✅ VÁLIDO
SI HTF BULLISH + MTF SUPPLY → ❌ INVÁLIDO (contradicción)
SI HTF RANGE + MTF DEMAND + LTF BOS SHORT → ⚠️ DUDOSO (revisar)
```

---

## INTEGRACIÓN CON RISK ENGINE

### Extensión de QualityScorer

El **MultiFrameOrchestrator** alimenta al **QualityScorer** (MANDATO 4) ajustando el componente `signal_score`:

```python
class QualityScorer:
    """
    QualityScorer extendido con multi-temporal context.
    """
    def __init__(self, config: Dict[str, Any]):
        self.multiframe_orchestrator = MultiFrameOrchestrator(config['multiframe'])
        # ... otros componentes ...

    def evaluate_signal(self, signal: Signal, market_data: Dict[str, pd.DataFrame]) -> QualityScore:
        """
        Evalúa calidad de señal CON análisis multi-temporal.
        """
        # 1. Análisis multi-temporal
        multiframe_score_obj = self.multiframe_orchestrator.evaluate_multiframe_signal(
            signal=signal,
            market_data=market_data
        )

        # 2. Si no está alineada temporalmente, RECHAZAR
        if not multiframe_score_obj.aligned:
            logger.warning(
                f"Señal {signal.id} RECHAZADA: {multiframe_score_obj.rejection_reason}"
            )
            return QualityScore(
                overall=0.0,  # Score 0.0 = NO TRADE
                pedigree=0.0,
                signal=0.0,
                microstructure=0.0,
                data_health=0.0,
                portfolio=0.0,
                rejection_reason=multiframe_score_obj.rejection_reason,
            )

        # 3. Calcular componentes estándar
        pedigree_score = self._calculate_pedigree(signal.strategy_id)

        # 4. Signal score AJUSTADO por multi-temporal
        base_signal_score = self._calculate_signal_strength(signal)
        adjusted_signal_score = 0.60 * base_signal_score + 0.40 * multiframe_score_obj.final_score

        # 5. Microstructure score (ya integrado en MANDATO 5)
        microstructure_score = self.microstructure_engine.get_current_score(
            symbol=signal.symbol,
            direction=signal.direction
        )

        # 6. Data health y portfolio
        data_health_score = self._calculate_data_health(signal.symbol)
        portfolio_score = self._calculate_portfolio_context(signal)

        # 7. Agregación
        quality_score = (
            self.weights['pedigree'] * pedigree_score +
            self.weights['signal'] * adjusted_signal_score +  # ← Ajustado
            self.weights['microstructure'] * microstructure_score +
            self.weights['data_health'] * data_health_score +
            self.weights['portfolio'] * portfolio_score
        )

        return QualityScore(
            overall=quality_score,
            pedigree=pedigree_score,
            signal=adjusted_signal_score,
            microstructure=microstructure_score,
            data_health=data_health_score,
            portfolio=portfolio_score,
            multiframe_context=multiframe_score_obj,  # Para auditoría
        )
```

---

## MANEJO DE CONFLICTOS

### Conflicto 1: HTF vs MTF

**Escenario**: HTF BULLISH pero MTF detecta supply zone fuerte con BOS bajista reciente.

**Resolución**:
- **HTF domina**: Rechazar señales SHORT
- **MTF advierte**: Reducir confidence de señales LONG (ajustar peso MTF a la baja)

```python
def resolve_htf_mtf_conflict(htf_structure: HTFStructure,
                             mtf_context: MTFContext) -> str:
    """
    Resuelve conflicto HTF-MTF.

    Returns:
        'HTF_DOMINATES', 'REDUCE_MTF_WEIGHT', 'RANGE_PIVOT'
    """
    if htf_structure.trend_direction in ['BULLISH', 'BEARISH']:
        # Trending: HTF domina siempre
        return 'HTF_DOMINATES'
    else:
        # Ranging: MTF puede sugerir pivote
        return 'RANGE_PIVOT'
```

### Conflicto 2: MTF vs LTF

**Escenario**: MTF dice LONG (demand zone) pero LTF detecta BOS SHORT.

**Resolución**:
- **Esperar confirmación**: NO entrar hasta que LTF alinee con MTF
- **Timeout**: Si después de N minutos no hay alineación, cancelar señal

```python
def resolve_mtf_ltf_conflict(mtf_context: MTFContext,
                             ltf_timing: LTFTiming,
                             timeout_minutes: int = 15) -> str:
    """
    Resuelve conflicto MTF-LTF.

    Returns:
        'WAIT_FOR_ALIGNMENT', 'CANCEL_SIGNAL', 'PROCEED_WITH_CAUTION'
    """
    # Si LTF contradice MTF, esperar
    if ltf_timing and ltf_timing.trigger.direction != mtf_context.htf_alignment:
        return 'WAIT_FOR_ALIGNMENT'

    # Si no hay timing LTF válido, proceder con cautela
    if not ltf_timing or not ltf_timing.is_valid_entry():
        return 'PROCEED_WITH_CAUTION'

    return 'PROCEED_WITH_CAUTION'
```

### Conflicto 3: Signal Contradicts All Timeframes

**Escenario**: Estrategia genera señal SHORT pero HTF BULLISH, MTF DEMAND, LTF BOS LONG.

**Resolución**:
- **RECHAZO INMEDIATO**: Señal inválida, no procesar

```python
def check_full_contradiction(signal: Signal,
                             multiframe_score: MultiFrameScore) -> bool:
    """
    Detecta contradicción completa.

    Returns:
        True si señal contradice TODOS los timeframes
    """
    if not multiframe_score.aligned:
        return True

    # Verificar scores individuales
    all_low = (
        multiframe_score.htf_score < 0.30 and
        multiframe_score.mtf_score < 0.30 and
        multiframe_score.ltf_score < 0.30
    )

    return all_low
```

---

## IMPLEMENTACIÓN Y TESTING

### Testing Strategy

#### Unit Tests

```python
class TestHTFStructureAnalyzer:
    """Tests para HTF analyzer."""

    def test_trend_identification(self):
        """Verifica identificación de tendencia."""
        # Generar datos con tendencia alcista clara
        ohlcv = generate_bullish_trend_data(bars=100)

        analyzer = HTFStructureAnalyzer({})
        structure = analyzer.analyze_structure('EURUSD', 'H4', ohlcv)

        assert structure.trend_direction == 'BULLISH'

    def test_swing_detection(self):
        """Verifica detección de swing points."""
        ohlcv = generate_test_ohlcv_with_swings()

        analyzer = HTFStructureAnalyzer({})
        swings = analyzer._identify_swing_points(ohlcv)

        assert len(swings) > 0
        assert all(s.type in ['HIGH', 'LOW'] for s in swings)
```

#### Integration Tests

```python
class TestMultiFrameOrchestrator:
    """Tests de integración del orchestrator."""

    def test_full_alignment(self):
        """Verifica alineación temporal completa."""
        # Preparar datos alineados: HTF BULLISH, MTF DEMAND, LTF BOS LONG
        market_data = {
            'H4': generate_bullish_trend('H4'),
            'M15': generate_demand_zone('M15'),
            'M1': generate_bos_long('M1'),
        }

        orchestrator = MultiFrameOrchestrator(test_config)
        signal = Signal(direction='LONG', ...)

        mf_score = orchestrator.evaluate_multiframe_signal(signal, market_data)

        assert mf_score.aligned == True
        assert mf_score.final_score > 0.65

    def test_rejection_on_contradiction(self):
        """Verifica rechazo de señal contradictoria."""
        # HTF BULLISH pero señal SHORT
        market_data = {
            'H4': generate_bullish_trend('H4'),
            'M15': generate_supply_zone('M15'),
            'M1': generate_bos_short('M1'),
        }

        orchestrator = MultiFrameOrchestrator(test_config)
        signal = Signal(direction='SHORT', ...)

        mf_score = orchestrator.evaluate_multiframe_signal(signal, market_data)

        assert mf_score.aligned == False
        assert mf_score.rejection_reason is not None
```

#### Backtesting

```python
def backtest_multiframe_system(
    historical_data: Dict[str, Dict[str, pd.DataFrame]],
    strategy_signals: List[Signal]
) -> pd.DataFrame:
    """
    Backtests sistema multi-temporal completo.

    Args:
        historical_data: {symbol: {'H4': df_h4, 'M15': df_m15, 'M1': df_m1}}
        strategy_signals: Señales generadas por estrategias

    Returns:
        DataFrame con resultados: aligned, scores, PnL, etc.
    """
    orchestrator = MultiFrameOrchestrator(load_config())
    results = []

    for signal in strategy_signals:
        # Obtener datos de mercado en timestamp de señal
        market_data = get_market_data_at_time(
            historical_data[signal.symbol],
            signal.timestamp
        )

        # Evaluar multi-temporal
        mf_score = orchestrator.evaluate_multiframe_signal(signal, market_data)

        # Simular ejecución si aligned
        if mf_score.aligned:
            execution = simulate_trade_execution(signal, historical_data[signal.symbol])
        else:
            execution = None

        results.append({
            'signal_id': signal.id,
            'timestamp': signal.timestamp,
            'symbol': signal.symbol,
            'direction': signal.direction,
            'aligned': mf_score.aligned,
            'rejection_reason': mf_score.rejection_reason,
            'htf_score': mf_score.htf_score,
            'mtf_score': mf_score.mtf_score,
            'ltf_score': mf_score.ltf_score,
            'final_score': mf_score.final_score,
            'executed': execution is not None,
            'pnl': execution.pnl if execution else 0.0,
        })

    return pd.DataFrame(results)
```

### Validación de Calidad

**Métricas**:

1. **Alignment Accuracy**: % de señales correctamente filtradas
   - Target: >85% de señales rechazadas deben tener razón válida

2. **Win Rate Improvement**: Win rate con vs sin multi-temporal
   - Target: +15% vs señales sin filtro temporal

3. **Drawdown Reduction**: Reducción de drawdown máximo
   - Target: -25% vs sistema sin filtro temporal

```python
def validate_multiframe_quality(backtest_results: pd.DataFrame):
    """
    Valida calidad del sistema multi-temporal.
    """
    # Métrica 1: Alignment accuracy
    rejected = backtest_results[backtest_results['aligned'] == False]
    executed = backtest_results[backtest_results['aligned'] == True]

    rejected_winrate = rejected['pnl'].apply(lambda x: x > 0).mean() if len(rejected) > 0 else 0
    executed_winrate = executed['pnl'].apply(lambda x: x > 0).mean()

    print(f"Win Rate (Rejected): {rejected_winrate:.1%}")
    print(f"Win Rate (Executed): {executed_winrate:.1%}")

    assert executed_winrate > rejected_winrate, "Sistema debe filtrar señales de menor calidad"

    # Métrica 2: Score correlation con PnL
    correlation = backtest_results['final_score'].corr(backtest_results['pnl'])
    print(f"Score-PnL Correlation: {correlation:.3f}")

    assert correlation > 0.20, "Score debe correlacionar con PnL"
```

---

## CONFIGURACIÓN RECOMENDADA

### Configuración de Producción

```python
MULTIFRAME_CONFIG_PRODUCTION = {
    'htf': {
        'timeframes': ['H4', 'D1'],
        'lookback_swings': 10,
        'swing_window': 5,
        'ob_threshold': 0.02,  # 2% move = institutional OB
    },
    'mtf': {
        'timeframes': ['M15', 'M5'],
        'zone_lookback': 50,
        'swing_window': 3,
        'impulse_threshold': 0.01,  # 1% = strong move
    },
    'ltf': {
        'timeframe': 'M1',
        'trigger_patterns': ['BOS', 'FVG', 'MITIGATION'],
        'swing_window': 2,
        'min_confidence': 0.65,
    },
    'synchronizer': {
        'htf_update_interval_hours': 4,
        'mtf_update_interval_minutes': 15,
    },
    'orchestrator': {
        'weights': {
            'htf': 0.50,
            'mtf': 0.30,
            'ltf': 0.20,
        },
        'min_final_score': 0.50,
    },
}
```

---

## REFERENCIAS Y BIBLIOGRAFÍA

1. **Elder, A. (2014)**
   *"The New Trading for a Living"*
   John Wiley & Sons. (Triple Screen Trading System)

2. **Douglas, M. (2000)**
   *"Trading in the Zone"*
   Prentice Hall. (Timeframe consistency)

3. **Brooks, A. (2009)**
   *"Reading Price Charts Bar by Bar"*
   John Wiley & Sons. (Multi-timeframe price action)

4. **Murphy, J. J. (1999)**
   *"Technical Analysis of the Financial Markets"*
   New York Institute of Finance. (Intermarket analysis, multiple timeframes)

5. **Nison, S. (1991)**
   *"Japanese Candlestick Charting Techniques"*
   (Temporal patterns across timeframes)

---

**FIN DE MULTIFRAME_CONTEXT_DESIGN.md**

*Diseño completo de análisis multi-temporal para SUBLIMINE TradingSystem.*
*Integración con Risk Engine (MANDATO 4) y MicrostructureEngine (MANDATO 5).*
