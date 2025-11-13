# MICROSTRUCTURE ENGINE – DISEÑO INSTITUCIONAL

**Proyecto**: SUBLIMINE TradingSystem
**Mandato**: 5 – Microestructura, VPIN, Level 2, Order Flow
**Fecha**: 2025-11-13
**Autor**: Sistema SUBLIMINE
**Status**: Design Phase – Institutional Grade

---

## RESUMEN EJECUTIVO

El **MicrostructureEngine** es el componente encargado de analizar la microestructura del mercado en tiempo real, detectando desequilibrios de orden flow, estimando probabilidad de trading informado (VPIN), analizando el libro de órdenes (Level 2), e identificando anomalías de manipulación (spoofing, layering, absorption).

**Objetivo**: Enriquecer la dimensión `microstructure_score` del **QualityScorer** (MANDATO 4) con señales cuantitativas de calidad de ejecución, liquidez disponible y riesgo de adverse selection.

**Principios**:
1. **Trade-Level Granularity**: Cada tick clasificado como compra o venta agresiva
2. **Volume-Synchronized**: VPIN calculado en buckets de volumen constante, NO tiempo
3. **Real-Time Level 2**: Análisis continuo del order book hasta N niveles de profundidad
4. **Detección de Manipulación**: Identificación de spoofing, layering, y icebergs
5. **Integración con QualityScorer**: Output directo al componente `microstructure_score [0-1]`

**Restricciones**:
- NO usar spread como única métrica (insuficiente para HFT/institucional)
- NO asumir simetría en liquidez bid/ask
- Manejar latencia: análisis debe completarse en <10ms para M1 execution
- Gestionar datos faltantes: Level 2 puede no estar disponible en todos los símbolos

---

## TABLA DE CONTENIDOS

1. [Arquitectura General](#arquitectura-general)
2. [Componente 1: VPINEstimator](#componente-1-vpinestimator)
3. [Componente 2: OrderFlowAnalyzer](#componente-2-orderflowanalyzer)
4. [Componente 3: Level2DepthMonitor](#componente-3-level2depthmonitor)
5. [Componente 4: SpoofingDetector](#componente-4-spoofingdetector)
6. [Componente 5: MicrostructureScorer](#componente-5-microstructurescorer)
7. [Flujos de Datos](#flujos-de-datos)
8. [Integración con QualityScorer](#integración-con-qualityscorer)
9. [Calibración y Thresholds](#calibración-y-thresholds)
10. [Implementación y Testing](#implementación-y-testing)

---

## ARQUITECTURA GENERAL

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────────┐
│                     MICROSTRUCTURE ENGINE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐      ┌──────────────────────────────┐    │
│  │  Market Data     │      │   Level 2 Feed                │    │
│  │  Tick Stream     │      │   (Order Book Depth)          │    │
│  │  (Price, Volume) │      │   (Bid/Ask, Quantity, Levels) │    │
│  └────────┬─────────┘      └────────┬─────────────────────┘    │
│           │                         │                           │
│           ├─────────────┬───────────┼───────────┐               │
│           │             │           │           │               │
│           ▼             ▼           ▼           ▼               │
│  ┌────────────┐  ┌──────────┐  ┌────────┐  ┌──────────┐        │
│  │   VPIN     │  │  Order   │  │ Level2 │  │ Spoofing │        │
│  │ Estimator  │  │   Flow   │  │ Depth  │  │ Detector │        │
│  │            │  │ Analyzer │  │Monitor │  │          │        │
│  └─────┬──────┘  └────┬─────┘  └───┬────┘  └────┬─────┘        │
│        │              │            │            │               │
│        └──────────────┴────────────┴────────────┘               │
│                       │                                         │
│                       ▼                                         │
│          ┌────────────────────────┐                             │
│          │  Microstructure Scorer │                             │
│          │  (Aggregates Signals)  │                             │
│          └───────────┬────────────┘                             │
│                      │                                          │
└──────────────────────┼──────────────────────────────────────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │   QualityScorer      │
            │ microstructure_score │
            │     [0.0 - 1.0]      │
            └──────────────────────┘
```

### Flujo de Procesamiento

1. **Ingest**: Recepción de tick data (price, volume, timestamp) + Level 2 snapshots
2. **Classification**: Cada trade clasificado como Buy/Sell agresivo (Lee-Ready, BVC)
3. **VPIN Calculation**: Buckets de volumen constante, cálculo de |V_buy - V_sell| / V_total
4. **Order Flow Imbalance**: Ratio de presión compradora vs vendedora en ventana deslizante
5. **Level 2 Analysis**: Profundidad, wall detection, ratio bid/ask quantity
6. **Spoofing Detection**: Análisis de cancelaciones rápidas y órdenes fantasma
7. **Aggregation**: Combinación de señales en `microstructure_score` [0-1]
8. **Output**: Score enviado a QualityScorer para risk allocation

---

## COMPONENTE 1: VPINEstimator

### Definición

**VPIN** (Volume-Synchronized Probability of Informed Trading) estima la probabilidad de que el mercado esté siendo movido por traders informados (institucionales, insiders) vs noise traders (retail).

**Paper de Referencia**: Easley, López de Prado, O'Hara (2012) - *"Flow Toxicity and Liquidity in a High-Frequency World"*

### Fórmula

Para cada bucket de volumen $V$:

$$
VPIN_{\tau} = \frac{\sum_{i=1}^{n} |V_{buy,i} - V_{sell,i}|}{\sum_{i=1}^{n} V_i}
$$

Donde:
- $n$ = número de buckets en ventana deslizante (típicamente 50)
- $V_{buy,i}$ = volumen de trades agresivos de compra en bucket $i$
- $V_{sell,i}$ = volumen de trades agresivos de venta en bucket $i$
- $V_i$ = volumen total en bucket $i$

**Interpretación**:
- $VPIN < 0.30$: Mercado balanceado, bajo riesgo de adverse selection
- $0.30 \leq VPIN < 0.50$: Presencia moderada de informed trading
- $VPIN \geq 0.50$: Alta probabilidad de informed trading, EVITAR ejecución

### Algoritmo de Clasificación de Trades

**Lee-Ready Algorithm** (Lee & Ready, 1991):

```python
def classify_trade(trade_price: float, mid_price: float, prev_mid: float) -> str:
    """
    Clasifica un trade como BUY o SELL agresivo.

    Args:
        trade_price: Precio del trade ejecutado
        mid_price: (best_bid + best_ask) / 2 en el momento del trade
        prev_mid: Mid price del trade anterior

    Returns:
        'BUY' si agresivo de compra, 'SELL' si agresivo de venta
    """
    # Tick test: comparar con mid price
    if trade_price > mid_price:
        return 'BUY'
    elif trade_price < mid_price:
        return 'SELL'
    else:
        # Tick rule: usar dirección del precio anterior
        if trade_price > prev_mid:
            return 'BUY'
        elif trade_price < prev_mid:
            return 'SELL'
        else:
            # Caso ambiguo: usar bid-ask quote (backup)
            return 'BUY'  # Default conservador
```

### Implementación de Buckets

**Volume Bucket Construction**:

```python
class VolumeBucket:
    """
    Bucket de volumen constante para VPIN.
    """
    def __init__(self, target_volume: float):
        self.target_volume = target_volume  # e.g., 100k USD para EURUSD
        self.accumulated_volume = 0.0
        self.buy_volume = 0.0
        self.sell_volume = 0.0
        self.trades = []

    def add_trade(self, volume: float, side: str):
        """
        Añade un trade al bucket.

        Returns True si el bucket está completo.
        """
        if side == 'BUY':
            self.buy_volume += volume
        else:
            self.sell_volume += volume

        self.accumulated_volume += volume

        return self.accumulated_volume >= self.target_volume

    def get_imbalance(self) -> float:
        """
        Retorna |V_buy - V_sell| / V_total
        """
        if self.accumulated_volume == 0:
            return 0.0

        return abs(self.buy_volume - self.sell_volume) / self.accumulated_volume
```

### Cálculo de VPIN

```python
class VPINEstimator:
    """
    Estima VPIN en tiempo real usando buckets de volumen.
    """
    def __init__(self, config: Dict[str, Any]):
        self.bucket_volume = config['bucket_volume']  # e.g., 100k USD
        self.window_size = config['vpin_window']      # e.g., 50 buckets
        self.buckets = deque(maxlen=self.window_size)
        self.current_bucket = VolumeBucket(self.bucket_volume)
        self.vpin_history = []

    def process_trade(self, trade: Trade, mid_price: float, prev_mid: float) -> Optional[float]:
        """
        Procesa un trade y actualiza VPIN si se completa un bucket.

        Returns:
            VPIN actual si se completó un bucket, None en caso contrario
        """
        # Clasificar trade
        side = classify_trade(trade.price, mid_price, prev_mid)

        # Añadir a bucket actual
        bucket_complete = self.current_bucket.add_trade(trade.volume, side)

        if bucket_complete:
            # Almacenar bucket completo
            self.buckets.append(self.current_bucket)

            # Calcular VPIN con ventana actual
            vpin = self._calculate_vpin()
            self.vpin_history.append(vpin)

            # Iniciar nuevo bucket
            self.current_bucket = VolumeBucket(self.bucket_volume)

            return vpin

        return None

    def _calculate_vpin(self) -> float:
        """
        Calcula VPIN como promedio de imbalances en ventana.
        """
        if len(self.buckets) == 0:
            return 0.0

        total_imbalance = sum(bucket.get_imbalance() for bucket in self.buckets)
        return total_imbalance / len(self.buckets)

    def get_current_vpin(self) -> float:
        """
        Retorna el VPIN más reciente calculado.
        """
        return self.vpin_history[-1] if self.vpin_history else 0.0
```

### Configuración por Símbolo

```python
VPIN_CONFIG = {
    'EURUSD': {
        'bucket_volume': 100_000,  # 100k USD por bucket
        'vpin_window': 50,         # 50 buckets = ~5M USD
        'threshold_low': 0.30,
        'threshold_high': 0.50,
    },
    'GBPUSD': {
        'bucket_volume': 80_000,
        'vpin_window': 50,
        'threshold_low': 0.30,
        'threshold_high': 0.50,
    },
    'XAUUSD': {
        'bucket_volume': 50_000,   # Menor liquidez
        'vpin_window': 40,
        'threshold_low': 0.35,
        'threshold_high': 0.55,
    },
    'BTCUSD': {
        'bucket_volume': 200_000,  # Alta volatilidad
        'vpin_window': 30,
        'threshold_low': 0.40,     # Más permisivo
        'threshold_high': 0.60,
    },
    'US50': {
        'bucket_volume': 150_000,
        'vpin_window': 50,
        'threshold_low': 0.30,
        'threshold_high': 0.50,
    },
}
```

### Output de VPIN

```python
@dataclass
class VPINSignal:
    """Señal de VPIN para microstructure scoring."""
    timestamp: datetime
    symbol: str
    vpin: float                    # [0.0, 1.0]
    bucket_count: int              # Número de buckets en ventana
    buy_volume_pct: float          # % de volumen comprador
    sell_volume_pct: float         # % de volumen vendedor
    toxicity_score: float          # [0.0, 1.0] - 0=safe, 1=toxic

    def is_safe_to_trade(self, threshold: float = 0.50) -> bool:
        """Retorna True si VPIN está por debajo del threshold."""
        return self.vpin < threshold
```

---

## COMPONENTE 2: OrderFlowAnalyzer

### Definición

El **OrderFlowAnalyzer** mide la **presión neta** de compra vs venta en ventanas temporales deslizantes, complementando VPIN con análisis de momentum direccional.

**Diferencia con VPIN**:
- VPIN: mide desequilibrio en buckets de volumen (toxic flow)
- Order Flow: mide momentum direccional en tiempo real (pressure)

### Métricas Calculadas

#### 1. Order Flow Imbalance (OFI)

$$
OFI_t = \frac{V_{buy,t} - V_{sell,t}}{V_{buy,t} + V_{sell,t}}
$$

Rango: $[-1.0, +1.0]$
- $OFI > +0.60$: Fuerte presión compradora
- $-0.60 < OFI < +0.60$: Equilibrio
- $OFI < -0.60$: Fuerte presión vendedora

#### 2. Trade Intensity

$$
Intensity_t = \frac{N_{trades,t}}{T_t}
$$

Donde:
- $N_{trades,t}$ = número de trades en ventana $t$
- $T_t$ = duración de ventana en segundos

**Interpretación**: Trades/segundo - detecta aceleración de actividad.

#### 3. Average Trade Size

$$
AvgSize_t = \frac{\sum_{i=1}^{N} Volume_i}{N}
$$

**Interpretación**: Incremento de tamaño promedio indica participación institucional.

### Implementación

```python
class OrderFlowAnalyzer:
    """
    Analiza order flow en tiempo real con ventanas deslizantes.
    """
    def __init__(self, config: Dict[str, Any]):
        self.window_seconds = config['ofi_window']  # e.g., 60 segundos
        self.trade_buffer = deque(maxlen=10000)
        self.ofi_history = []

    def add_trade(self, trade: Trade, side: str):
        """
        Añade un trade clasificado al buffer.

        Args:
            trade: Trade con price, volume, timestamp
            side: 'BUY' o 'SELL' (del Lee-Ready classifier)
        """
        self.trade_buffer.append({
            'timestamp': trade.timestamp,
            'volume': trade.volume,
            'side': side,
            'price': trade.price,
        })

    def calculate_ofi(self, current_time: datetime) -> float:
        """
        Calcula Order Flow Imbalance en ventana actual.

        Returns:
            OFI en rango [-1.0, +1.0]
        """
        # Filtrar trades dentro de ventana
        cutoff_time = current_time - timedelta(seconds=self.window_seconds)
        recent_trades = [t for t in self.trade_buffer if t['timestamp'] >= cutoff_time]

        if not recent_trades:
            return 0.0

        # Calcular volumen por lado
        buy_volume = sum(t['volume'] for t in recent_trades if t['side'] == 'BUY')
        sell_volume = sum(t['volume'] for t in recent_trades if t['side'] == 'SELL')

        total_volume = buy_volume + sell_volume

        if total_volume == 0:
            return 0.0

        ofi = (buy_volume - sell_volume) / total_volume
        self.ofi_history.append(ofi)

        return ofi

    def calculate_intensity(self, current_time: datetime) -> float:
        """
        Calcula trade intensity (trades/second).
        """
        cutoff_time = current_time - timedelta(seconds=self.window_seconds)
        recent_trades = [t for t in self.trade_buffer if t['timestamp'] >= cutoff_time]

        return len(recent_trades) / self.window_seconds

    def calculate_avg_trade_size(self, current_time: datetime) -> float:
        """
        Calcula tamaño promedio de trade en ventana.
        """
        cutoff_time = current_time - timedelta(seconds=self.window_seconds)
        recent_trades = [t for t in self.trade_buffer if t['timestamp'] >= cutoff_time]

        if not recent_trades:
            return 0.0

        total_volume = sum(t['volume'] for t in recent_trades)
        return total_volume / len(recent_trades)

    def get_directional_bias(self, ofi: float) -> str:
        """
        Retorna bias direccional basado en OFI.

        Returns:
            'STRONG_BUY', 'WEAK_BUY', 'NEUTRAL', 'WEAK_SELL', 'STRONG_SELL'
        """
        if ofi > 0.60:
            return 'STRONG_BUY'
        elif ofi > 0.30:
            return 'WEAK_BUY'
        elif ofi > -0.30:
            return 'NEUTRAL'
        elif ofi > -0.60:
            return 'WEAK_SELL'
        else:
            return 'STRONG_SELL'
```

### Detección de Cambios de Régimen

```python
def detect_flow_regime_change(self, lookback: int = 10) -> bool:
    """
    Detecta cambio abrupto en order flow (posible entrada institucional).

    Args:
        lookback: Número de períodos previos para comparar

    Returns:
        True si hay cambio de régimen significativo
    """
    if len(self.ofi_history) < lookback + 1:
        return False

    recent_ofi = self.ofi_history[-1]
    historical_mean = np.mean(self.ofi_history[-lookback-1:-1])
    historical_std = np.std(self.ofi_history[-lookback-1:-1])

    # Cambio > 2 desviaciones estándar
    z_score = abs(recent_ofi - historical_mean) / (historical_std + 1e-6)

    return z_score > 2.0
```

### Output de Order Flow

```python
@dataclass
class OrderFlowSignal:
    """Señal de order flow para microstructure scoring."""
    timestamp: datetime
    symbol: str
    ofi: float                      # [-1.0, +1.0]
    intensity: float                # Trades/second
    avg_trade_size: float           # Volume promedio
    directional_bias: str           # 'STRONG_BUY', 'NEUTRAL', etc.
    regime_change: bool             # True si hay cambio abrupto
    buy_volume_total: float
    sell_volume_total: float
```

---

## COMPONENTE 3: Level2DepthMonitor

### Definición

El **Level2DepthMonitor** analiza el **order book** (libro de órdenes) en tiempo real, monitoreando:
1. Profundidad de liquidez en bid/ask
2. Ratio de cantidad bid/ask
3. Identificación de liquidity walls
4. Detección de cambios abruptos en depth

### Estructura de Level 2 Data

```python
@dataclass
class Level2Quote:
    """Representa un nivel del order book."""
    price: float
    quantity: float
    num_orders: int  # Opcional: número de órdenes agregadas

@dataclass
class Level2Snapshot:
    """Snapshot completo del order book."""
    timestamp: datetime
    symbol: str
    bids: List[Level2Quote]  # Ordenados de mayor a menor precio
    asks: List[Level2Quote]  # Ordenados de menor a mayor precio

    def get_best_bid(self) -> Level2Quote:
        return self.bids[0] if self.bids else None

    def get_best_ask(self) -> Level2Quote:
        return self.asks[0] if self.asks else None

    def get_mid_price(self) -> float:
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        if best_bid and best_ask:
            return (best_bid.price + best_ask.price) / 2.0
        return 0.0

    def get_spread(self) -> float:
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        if best_bid and best_ask:
            return best_ask.price - best_bid.price
        return 0.0
```

### Métricas de Profundidad

#### 1. Depth Imbalance

Mide el desbalance de liquidez entre bid y ask:

$$
DepthImbalance = \frac{Q_{bid} - Q_{ask}}{Q_{bid} + Q_{ask}}
$$

Donde:
- $Q_{bid}$ = suma de cantidades en los primeros N niveles de bid
- $Q_{ask}$ = suma de cantidades en los primeros N niveles de ask
- Típicamente $N = 5$ niveles

**Interpretación**:
- $DepthImbalance > +0.30$: Mayor liquidez en bid (soporte fuerte)
- $-0.30 < DepthImbalance < +0.30$: Liquidez balanceada
- $DepthImbalance < -0.30$: Mayor liquidez en ask (resistencia fuerte)

#### 2. Spread Score

Penaliza spreads amplios que indican baja liquidez:

$$
SpreadScore = 1.0 - \min\left(\frac{Spread}{Spread_{typical}}, 1.0\right)
$$

Donde $Spread_{typical}$ es el spread promedio histórico del símbolo.

**Interpretación**:
- $SpreadScore = 1.0$: Spread normal o estrecho (óptimo)
- $SpreadScore = 0.0$: Spread muy amplio (evitar ejecución)

#### 3. Liquidity Depth

Cantidad total disponible en los primeros N niveles:

$$
LiquidityDepth = Q_{bid} + Q_{ask}
$$

**Normalización**: Comparar con profundidad típica del símbolo.

### Implementación

```python
class Level2DepthMonitor:
    """
    Monitorea profundidad del order book en tiempo real.
    """
    def __init__(self, config: Dict[str, Any]):
        self.depth_levels = config['depth_levels']  # e.g., 5 niveles
        self.snapshot_history = deque(maxlen=100)
        self.spread_history = deque(maxlen=1000)

        # Calibración por símbolo
        self.typical_spread = {}
        self.typical_depth = {}

    def update_snapshot(self, snapshot: Level2Snapshot):
        """
        Actualiza con nuevo snapshot del order book.
        """
        self.snapshot_history.append(snapshot)
        self.spread_history.append(snapshot.get_spread())

        # Actualizar típicos (rolling)
        symbol = snapshot.symbol
        if symbol not in self.typical_spread:
            self.typical_spread[symbol] = snapshot.get_spread()
            self.typical_depth[symbol] = self._calculate_total_depth(snapshot)
        else:
            # Exponential moving average
            alpha = 0.01
            self.typical_spread[symbol] = (
                alpha * snapshot.get_spread() +
                (1 - alpha) * self.typical_spread[symbol]
            )
            self.typical_depth[symbol] = (
                alpha * self._calculate_total_depth(snapshot) +
                (1 - alpha) * self.typical_depth[symbol]
            )

    def calculate_depth_imbalance(self, snapshot: Level2Snapshot) -> float:
        """
        Calcula depth imbalance en los primeros N niveles.

        Returns:
            Imbalance en rango [-1.0, +1.0]
        """
        bid_quantity = sum(
            level.quantity
            for level in snapshot.bids[:self.depth_levels]
        )
        ask_quantity = sum(
            level.quantity
            for level in snapshot.asks[:self.depth_levels]
        )

        total_quantity = bid_quantity + ask_quantity

        if total_quantity == 0:
            return 0.0

        return (bid_quantity - ask_quantity) / total_quantity

    def calculate_spread_score(self, snapshot: Level2Snapshot) -> float:
        """
        Calcula spread score normalizado [0.0, 1.0].

        Returns:
            1.0 = spread óptimo, 0.0 = spread muy amplio
        """
        current_spread = snapshot.get_spread()
        typical_spread = self.typical_spread.get(snapshot.symbol, current_spread)

        if typical_spread == 0:
            return 1.0

        spread_ratio = current_spread / typical_spread
        return max(0.0, 1.0 - min(spread_ratio, 1.0))

    def calculate_liquidity_depth_score(self, snapshot: Level2Snapshot) -> float:
        """
        Calcula score de profundidad de liquidez [0.0, 1.0].

        Returns:
            1.0 = liquidez excelente, 0.0 = liquidez muy baja
        """
        current_depth = self._calculate_total_depth(snapshot)
        typical_depth = self.typical_depth.get(snapshot.symbol, current_depth)

        if typical_depth == 0:
            return 1.0

        depth_ratio = current_depth / typical_depth

        # Sigmoid: 1.0 cuando depth >= typical, decay suave si menor
        return 1.0 / (1.0 + np.exp(-5 * (depth_ratio - 0.8)))

    def _calculate_total_depth(self, snapshot: Level2Snapshot) -> float:
        """
        Suma de cantidades en los primeros N niveles (bid + ask).
        """
        bid_quantity = sum(
            level.quantity
            for level in snapshot.bids[:self.depth_levels]
        )
        ask_quantity = sum(
            level.quantity
            for level in snapshot.asks[:self.depth_levels]
        )
        return bid_quantity + ask_quantity

    def detect_liquidity_wall(self, snapshot: Level2Snapshot,
                              threshold_ratio: float = 3.0) -> Optional[Dict]:
        """
        Detecta liquidity walls (órdenes grandes que pueden actuar como soporte/resistencia).

        Args:
            threshold_ratio: Ratio mínimo vs cantidad promedio para considerar wall

        Returns:
            Dict con información del wall si existe, None en caso contrario
        """
        # Calcular cantidad promedio en book
        all_quantities = (
            [level.quantity for level in snapshot.bids] +
            [level.quantity for level in snapshot.asks]
        )

        if not all_quantities:
            return None

        avg_quantity = np.mean(all_quantities)

        # Buscar niveles con cantidad >> promedio
        for level in snapshot.bids:
            if level.quantity >= threshold_ratio * avg_quantity:
                return {
                    'side': 'BID',
                    'price': level.price,
                    'quantity': level.quantity,
                    'distance_from_mid': snapshot.get_mid_price() - level.price,
                    'ratio_to_avg': level.quantity / avg_quantity,
                }

        for level in snapshot.asks:
            if level.quantity >= threshold_ratio * avg_quantity:
                return {
                    'side': 'ASK',
                    'price': level.price,
                    'quantity': level.quantity,
                    'distance_from_mid': level.price - snapshot.get_mid_price(),
                    'ratio_to_avg': level.quantity / avg_quantity,
                }

        return None
```

### Output de Level 2

```python
@dataclass
class Level2Signal:
    """Señal de Level 2 depth para microstructure scoring."""
    timestamp: datetime
    symbol: str
    depth_imbalance: float          # [-1.0, +1.0]
    spread_score: float             # [0.0, 1.0]
    liquidity_depth_score: float    # [0.0, 1.0]
    liquidity_wall: Optional[Dict]  # Información de wall si existe
    best_bid: float
    best_ask: float
    mid_price: float
    spread_bps: float               # Spread en basis points
```

---

## COMPONENTE 4: SpoofingDetector

### Definición

El **SpoofingDetector** identifica patrones de **manipulación** en el order book:

1. **Spoofing**: Colocar órdenes grandes sin intención de ejecución para mover precio, luego cancelarlas
2. **Layering**: Colocar múltiples órdenes en varios niveles para crear apariencia de liquidez falsa
3. **Iceberg Orders**: Órdenes grandes ocultas que se revelan gradualmente
4. **Quote Stuffing**: Colocación y cancelación rápida de órdenes para generar ruido

### Detección de Spoofing

**Patrón típico**:
1. Aparece orden grande en bid/ask (e.g., 10x cantidad promedio)
2. Precio se mueve hacia la orden
3. Orden se cancela antes de ser ejecutada
4. Precio revierte

**Algoritmo**:

```python
class SpoofingDetector:
    """
    Detecta patrones de spoofing y manipulación en Level 2.
    """
    def __init__(self, config: Dict[str, Any]):
        self.order_tracking = {}  # {order_id: OrderInfo}
        self.spoofing_events = []
        self.config = config

        # Thresholds
        self.large_order_ratio = config.get('large_order_ratio', 5.0)
        self.fast_cancel_seconds = config.get('fast_cancel_seconds', 2.0)
        self.min_price_move_bps = config.get('min_price_move_bps', 5.0)

    def track_order_add(self, order_id: str, snapshot: Level2Snapshot,
                        level: Level2Quote, side: str):
        """
        Registra aparición de nueva orden en book.
        """
        avg_quantity = self._get_avg_book_quantity(snapshot)

        self.order_tracking[order_id] = {
            'timestamp_add': snapshot.timestamp,
            'price': level.price,
            'quantity': level.quantity,
            'side': side,
            'mid_at_add': snapshot.get_mid_price(),
            'is_large': level.quantity >= self.large_order_ratio * avg_quantity,
            'cancelled': False,
            'executed': False,
        }

    def track_order_cancel(self, order_id: str, snapshot: Level2Snapshot):
        """
        Registra cancelación de orden y detecta spoofing.
        """
        if order_id not in self.order_tracking:
            return

        order_info = self.order_tracking[order_id]
        order_info['cancelled'] = True
        order_info['timestamp_cancel'] = snapshot.timestamp
        order_info['mid_at_cancel'] = snapshot.get_mid_price()

        # Verificar patrón de spoofing
        if self._is_spoofing_pattern(order_info, snapshot):
            self._record_spoofing_event(order_info, snapshot)

    def _is_spoofing_pattern(self, order_info: Dict, snapshot: Level2Snapshot) -> bool:
        """
        Detecta si la cancelación coincide con patrón de spoofing.

        Criterios:
        1. Orden grande (>= large_order_ratio * avg)
        2. Cancelada rápidamente (< fast_cancel_seconds)
        3. Precio se movió hacia la orden
        4. Orden nunca ejecutada (aún en book al cancelarse)
        """
        if not order_info['is_large']:
            return False

        if order_info['executed']:
            return False

        # Calcular tiempo de vida
        lifetime = (
            order_info['timestamp_cancel'] -
            order_info['timestamp_add']
        ).total_seconds()

        if lifetime >= self.fast_cancel_seconds:
            return False

        # Verificar movimiento de precio hacia la orden
        mid_at_add = order_info['mid_at_add']
        mid_at_cancel = order_info['mid_at_cancel']
        price_move = mid_at_cancel - mid_at_add

        # Si orden en BID: precio debió bajar hacia ella
        # Si orden en ASK: precio debió subir hacia ella
        if order_info['side'] == 'BID':
            moved_toward_order = price_move < 0
        else:  # ASK
            moved_toward_order = price_move > 0

        if not moved_toward_order:
            return False

        # Verificar magnitud del movimiento
        move_bps = abs(price_move) / mid_at_add * 10000

        if move_bps < self.min_price_move_bps:
            return False

        return True

    def _record_spoofing_event(self, order_info: Dict, snapshot: Level2Snapshot):
        """
        Registra evento de spoofing detectado.
        """
        event = {
            'timestamp': snapshot.timestamp,
            'symbol': snapshot.symbol,
            'side': order_info['side'],
            'price': order_info['price'],
            'quantity': order_info['quantity'],
            'lifetime_seconds': (
                order_info['timestamp_cancel'] -
                order_info['timestamp_add']
            ).total_seconds(),
            'price_move_bps': abs(
                order_info['mid_at_cancel'] - order_info['mid_at_add']
            ) / order_info['mid_at_add'] * 10000,
        }

        self.spoofing_events.append(event)

        logger.warning(
            f"SPOOFING DETECTED: {snapshot.symbol} {order_info['side']} "
            f"{order_info['quantity']} @ {order_info['price']} "
            f"(lifetime={event['lifetime_seconds']:.2f}s, "
            f"move={event['price_move_bps']:.1f}bps)"
        )

    def _get_avg_book_quantity(self, snapshot: Level2Snapshot) -> float:
        """
        Calcula cantidad promedio en book.
        """
        all_quantities = (
            [level.quantity for level in snapshot.bids] +
            [level.quantity for level in snapshot.asks]
        )
        return np.mean(all_quantities) if all_quantities else 1.0

    def get_spoofing_risk_score(self, lookback_minutes: int = 5) -> float:
        """
        Calcula risk score basado en frecuencia de spoofing reciente.

        Returns:
            Score [0.0, 1.0] donde 1.0 = alto riesgo de manipulación
        """
        if not self.spoofing_events:
            return 0.0

        # Filtrar eventos recientes
        cutoff_time = datetime.now() - timedelta(minutes=lookback_minutes)
        recent_events = [
            e for e in self.spoofing_events
            if e['timestamp'] >= cutoff_time
        ]

        if not recent_events:
            return 0.0

        # Score basado en frecuencia (eventos/minuto)
        event_frequency = len(recent_events) / lookback_minutes

        # Sigmoid: 0.0 si <0.5 eventos/min, 1.0 si >=2 eventos/min
        risk_score = 1.0 / (1.0 + np.exp(-3 * (event_frequency - 1.0)))

        return min(risk_score, 1.0)
```

### Detección de Layering

```python
def detect_layering(self, snapshot: Level2Snapshot, side: str) -> bool:
    """
    Detecta layering: múltiples órdenes grandes en varios niveles.

    Patrón:
    - 3+ órdenes grandes en niveles consecutivos
    - Todas del mismo lado
    - Cantidades similares (posiblemente mismo trader)

    Returns:
        True si se detecta patrón de layering
    """
    levels = snapshot.bids if side == 'BID' else snapshot.asks

    if len(levels) < 3:
        return False

    avg_quantity = np.mean([level.quantity for level in levels])

    # Identificar órdenes grandes
    large_orders = [
        level for level in levels
        if level.quantity >= self.large_order_ratio * avg_quantity
    ]

    if len(large_orders) < 3:
        return False

    # Verificar si están en niveles consecutivos
    for i in range(len(large_orders) - 2):
        consecutive_count = 1

        for j in range(i + 1, len(large_orders)):
            # Verificar si cantidades son similares (±20%)
            qty_ratio = large_orders[j].quantity / large_orders[i].quantity
            if 0.8 <= qty_ratio <= 1.2:
                consecutive_count += 1
            else:
                break

        if consecutive_count >= 3:
            return True

    return False
```

### Output de Spoofing

```python
@dataclass
class SpoofingSignal:
    """Señal de spoofing/manipulación para microstructure scoring."""
    timestamp: datetime
    symbol: str
    spoofing_risk_score: float      # [0.0, 1.0]
    layering_detected: bool
    recent_spoofing_events: int     # Últimos 5 minutos
    manipulation_severity: str      # 'NONE', 'LOW', 'MEDIUM', 'HIGH'
```

---

## COMPONENTE 5: MicrostructureScorer

### Definición

El **MicrostructureScorer** es el componente agregador que combina todas las señales de microestructura en un único score [0.0, 1.0] que alimenta al **QualityScorer**.

### Inputs

```python
@dataclass
class MicrostructureInputs:
    """Inputs de todos los componentes de microestructura."""
    vpin_signal: VPINSignal
    orderflow_signal: OrderFlowSignal
    level2_signal: Level2Signal
    spoofing_signal: SpoofingSignal
```

### Fórmula de Agregación

El `microstructure_score` se calcula como promedio ponderado de 4 sub-scores:

$$
MicrostructureScore = w_1 \cdot S_{vpin} + w_2 \cdot S_{flow} + w_3 \cdot S_{depth} + w_4 \cdot S_{manip}
$$

Donde:
- $S_{vpin}$ = score de VPIN (toxicity inversa)
- $S_{flow}$ = score de order flow (alignment con dirección de señal)
- $S_{depth}$ = score de liquidez y profundidad
- $S_{manip}$ = score de ausencia de manipulación (spoofing inverso)

**Pesos por defecto**:
- $w_1 = 0.35$ (VPIN - prioridad alta)
- $w_2 = 0.25$ (Order Flow)
- $w_3 = 0.25$ (Depth)
- $w_4 = 0.15$ (Anti-Manipulación)

### Cálculo de Sub-Scores

#### 1. VPIN Score

$$
S_{vpin} = 1.0 - \min\left(\frac{VPIN}{0.60}, 1.0\right)
$$

**Lógica**:
- VPIN = 0.0 → Score = 1.0 (óptimo, no hay toxic flow)
- VPIN = 0.60 → Score = 0.0 (muy tóxico, evitar)
- Cap en 0.60 (valores mayores también dan score 0.0)

#### 2. Order Flow Score

$$
S_{flow} =
\begin{cases}
1.0 & \text{si OFI alineado con signal direction} \\
0.5 & \text{si OFI neutral} \\
0.0 & \text{si OFI contrario a signal direction}
\end{cases}
$$

**Ejemplo**:
- Signal LONG + OFI > +0.30 → Score = 1.0 (flow confirma)
- Signal LONG + OFI en [-0.30, +0.30] → Score = 0.5 (neutral)
- Signal LONG + OFI < -0.30 → Score = 0.0 (flow contraindica)

**Refinamiento**:
```python
def calculate_flow_score(ofi: float, signal_direction: str) -> float:
    """
    Calcula flow score considerando alineación con señal.

    Args:
        ofi: Order Flow Imbalance [-1.0, +1.0]
        signal_direction: 'LONG' o 'SHORT'

    Returns:
        Score [0.0, 1.0]
    """
    # Caso LONG: OFI positivo es favorable
    if signal_direction == 'LONG':
        if ofi > 0.30:
            return 1.0
        elif ofi > -0.30:
            return 0.5 + (ofi / 0.60)  # Linear en [-0.3, +0.3]
        else:
            return 0.0

    # Caso SHORT: OFI negativo es favorable
    else:  # SHORT
        if ofi < -0.30:
            return 1.0
        elif ofi < 0.30:
            return 0.5 - (ofi / 0.60)  # Linear en [-0.3, +0.3]
        else:
            return 0.0
```

#### 3. Depth Score

$$
S_{depth} = 0.40 \cdot SpreadScore + 0.40 \cdot LiquidityScore + 0.20 \cdot DepthAlignment
$$

Donde:
- $SpreadScore$ = spread normalizado del Level2Monitor
- $LiquidityScore$ = liquidity depth score del Level2Monitor
- $DepthAlignment$ = alignment de depth imbalance con señal

**DepthAlignment**:
```python
def calculate_depth_alignment(depth_imbalance: float, signal_direction: str) -> float:
    """
    Score de alineación de liquidez con dirección de señal.

    Args:
        depth_imbalance: [-1.0, +1.0] (positivo = más liquidez en bid)
        signal_direction: 'LONG' o 'SHORT'

    Returns:
        Score [0.0, 1.0]
    """
    # LONG: favorable si más liquidez en bid (soporte)
    if signal_direction == 'LONG':
        if depth_imbalance > 0.30:
            return 1.0
        elif depth_imbalance > -0.30:
            return 0.5 + (depth_imbalance / 0.60)
        else:
            return 0.0

    # SHORT: favorable si más liquidez en ask (resistencia)
    else:  # SHORT
        if depth_imbalance < -0.30:
            return 1.0
        elif depth_imbalance < 0.30:
            return 0.5 - (depth_imbalance / 0.60)
        else:
            return 0.0
```

#### 4. Anti-Manipulation Score

$$
S_{manip} = 1.0 - SpoofingRiskScore
$$

**Lógica**:
- Si `spoofing_risk_score = 0.0` (no manipulación) → Score = 1.0
- Si `spoofing_risk_score = 1.0` (alta manipulación) → Score = 0.0

### Implementación Completa

```python
class MicrostructureScorer:
    """
    Agrega señales de microestructura en score unificado [0.0, 1.0].
    """
    def __init__(self, config: Dict[str, Any]):
        self.weights = {
            'vpin': config.get('weight_vpin', 0.35),
            'flow': config.get('weight_flow', 0.25),
            'depth': config.get('weight_depth', 0.25),
            'manip': config.get('weight_manip', 0.15),
        }

        # Normalizar pesos
        total_weight = sum(self.weights.values())
        self.weights = {k: v/total_weight for k, v in self.weights.items()}

    def calculate_microstructure_score(
        self,
        inputs: MicrostructureInputs,
        signal_direction: str
    ) -> float:
        """
        Calcula microstructure score agregado.

        Args:
            inputs: Señales de todos los componentes
            signal_direction: 'LONG' o 'SHORT' de la señal de trading

        Returns:
            Score [0.0, 1.0] donde 1.0 = condiciones óptimas de microestructura
        """
        # Sub-score 1: VPIN (toxicity inversa)
        vpin_score = self._calculate_vpin_score(inputs.vpin_signal)

        # Sub-score 2: Order Flow (alignment)
        flow_score = self._calculate_flow_score(
            inputs.orderflow_signal,
            signal_direction
        )

        # Sub-score 3: Depth (liquidez + alignment)
        depth_score = self._calculate_depth_score(
            inputs.level2_signal,
            signal_direction
        )

        # Sub-score 4: Anti-Manipulation
        manip_score = 1.0 - inputs.spoofing_signal.spoofing_risk_score

        # Agregación ponderada
        final_score = (
            self.weights['vpin'] * vpin_score +
            self.weights['flow'] * flow_score +
            self.weights['depth'] * depth_score +
            self.weights['manip'] * manip_score
        )

        return np.clip(final_score, 0.0, 1.0)

    def _calculate_vpin_score(self, vpin_signal: VPINSignal) -> float:
        """
        Convierte VPIN a score (inverso de toxicity).
        """
        # Cap en 0.60: valores mayores también dan score 0.0
        normalized_vpin = min(vpin_signal.vpin / 0.60, 1.0)
        return 1.0 - normalized_vpin

    def _calculate_flow_score(
        self,
        orderflow_signal: OrderFlowSignal,
        signal_direction: str
    ) -> float:
        """
        Calcula flow score considerando alineación.
        """
        ofi = orderflow_signal.ofi

        if signal_direction == 'LONG':
            if ofi > 0.30:
                return 1.0
            elif ofi > -0.30:
                return 0.5 + (ofi / 0.60)
            else:
                return 0.0
        else:  # SHORT
            if ofi < -0.30:
                return 1.0
            elif ofi < 0.30:
                return 0.5 - (ofi / 0.60)
            else:
                return 0.0

    def _calculate_depth_score(
        self,
        level2_signal: Level2Signal,
        signal_direction: str
    ) -> float:
        """
        Calcula depth score combinando spread, liquidez y alignment.
        """
        # Componente 1: Spread (40%)
        spread_component = 0.40 * level2_signal.spread_score

        # Componente 2: Liquidez (40%)
        liquidity_component = 0.40 * level2_signal.liquidity_depth_score

        # Componente 3: Depth Alignment (20%)
        depth_imbalance = level2_signal.depth_imbalance

        if signal_direction == 'LONG':
            if depth_imbalance > 0.30:
                alignment_score = 1.0
            elif depth_imbalance > -0.30:
                alignment_score = 0.5 + (depth_imbalance / 0.60)
            else:
                alignment_score = 0.0
        else:  # SHORT
            if depth_imbalance < -0.30:
                alignment_score = 1.0
            elif depth_imbalance < 0.30:
                alignment_score = 0.5 - (depth_imbalance / 0.60)
            else:
                alignment_score = 0.0

        alignment_component = 0.20 * alignment_score

        return spread_component + liquidity_component + alignment_component

    def get_detailed_breakdown(
        self,
        inputs: MicrostructureInputs,
        signal_direction: str
    ) -> Dict[str, float]:
        """
        Retorna breakdown detallado de componentes del score.

        Útil para debugging y análisis post-trade.
        """
        vpin_score = self._calculate_vpin_score(inputs.vpin_signal)
        flow_score = self._calculate_flow_score(inputs.orderflow_signal, signal_direction)
        depth_score = self._calculate_depth_score(inputs.level2_signal, signal_direction)
        manip_score = 1.0 - inputs.spoofing_signal.spoofing_risk_score

        final_score = (
            self.weights['vpin'] * vpin_score +
            self.weights['flow'] * flow_score +
            self.weights['depth'] * depth_score +
            self.weights['manip'] * manip_score
        )

        return {
            'final_score': final_score,
            'vpin_score': vpin_score,
            'vpin_weight': self.weights['vpin'],
            'vpin_contribution': self.weights['vpin'] * vpin_score,
            'flow_score': flow_score,
            'flow_weight': self.weights['flow'],
            'flow_contribution': self.weights['flow'] * flow_score,
            'depth_score': depth_score,
            'depth_weight': self.weights['depth'],
            'depth_contribution': self.weights['depth'] * depth_score,
            'manip_score': manip_score,
            'manip_weight': self.weights['manip'],
            'manip_contribution': self.weights['manip'] * manip_score,
        }
```

### Output Final

```python
@dataclass
class MicrostructureScore:
    """Score final de microestructura para QualityScorer."""
    timestamp: datetime
    symbol: str
    score: float                    # [0.0, 1.0]
    vpin_component: float
    flow_component: float
    depth_component: float
    manip_component: float
    signal_direction: str           # 'LONG' o 'SHORT'

    # Datos raw para auditoría
    vpin_raw: float
    ofi_raw: float
    depth_imbalance_raw: float
    spoofing_risk_raw: float
```

---

## FLUJOS DE DATOS

### Flujo 1: Tick Processing Pipeline

```
Market Data Feed
       ↓
[Tick arrives: price, volume, timestamp]
       ↓
       ├─→ [Lee-Ready Classifier] → BUY/SELL
       │         ↓
       │   [VPINEstimator]
       │         ↓
       │   Add to volume bucket
       │         ↓
       │   Bucket complete? → Calculate VPIN
       │
       ├─→ [OrderFlowAnalyzer]
       │         ↓
       │   Add to trade buffer
       │         ↓
       │   Calculate OFI, intensity, avg size
       │
       └─→ Continue to aggregation
```

### Flujo 2: Level 2 Processing Pipeline

```
Level 2 Feed (Order Book Snapshot)
       ↓
[Snapshot: bids[], asks[], timestamp]
       ↓
       ├─→ [Level2DepthMonitor]
       │         ↓
       │   Calculate depth imbalance
       │   Calculate spread score
       │   Calculate liquidity depth score
       │   Detect liquidity walls
       │
       ├─→ [SpoofingDetector]
       │         ↓
       │   Track order adds/cancels
       │   Detect spoofing patterns
       │   Detect layering
       │   Calculate spoofing risk score
       │
       └─→ Continue to aggregation
```

### Flujo 3: Signal Generation Pipeline

```
Strategy generates signal
       ↓
[Signal with direction: LONG/SHORT]
       ↓
Query current microstructure state:
       ├─→ Get latest VPIN
       ├─→ Get latest OFI
       ├─→ Get latest Level 2 metrics
       └─→ Get latest spoofing risk
              ↓
       [MicrostructureScorer]
              ↓
       Aggregate into microstructure_score [0-1]
              ↓
       Pass to QualityScorer
              ↓
       QualityScorer calculates full Quality Score
              ↓
       RiskAllocator maps score → risk %
              ↓
       Trade execution (if score >= 0.50)
```

### Latencia Target por Componente

| Componente | Latencia Target | Notas |
|------------|----------------|-------|
| Lee-Ready Classification | <1ms | Por trade |
| VPIN Update | <5ms | Por bucket completo (~100 trades) |
| Order Flow Calculation | <2ms | Por ventana (60s) |
| Level 2 Analysis | <3ms | Por snapshot (~100ms interval) |
| Spoofing Detection | <2ms | Por order book update |
| MicrostructureScorer | <5ms | Agregación final |
| **Total Pipeline** | **<10ms** | Desde tick hasta score |

---

## INTEGRACIÓN CON QUALITYSCORER

### Modificación de QualityScorer (MANDATO 4)

El **QualityScorer** definido en MANDATO 4 calcula:

$$
Quality\_Score = 0.25 \cdot pedigree + 0.25 \cdot signal + 0.20 \cdot microstructure + 0.15 \cdot data + 0.15 \cdot portfolio
$$

El componente `microstructure` ahora proviene del **MicrostructureScorer**:

```python
class QualityScorer:
    """
    Evalúa calidad de señal en 5 dimensiones.

    MANDATO 4 + MANDATO 5 (microstructure enrichment).
    """
    def __init__(self, config: Dict[str, Any]):
        self.weights = {
            'pedigree': 0.25,
            'signal': 0.25,
            'microstructure': 0.20,  # ← Ahora alimentado por MicrostructureEngine
            'data_health': 0.15,
            'portfolio': 0.15,
        }

        # Componentes
        self.microstructure_engine = MicrostructureEngine(config)
        # ... otros componentes ...

    def evaluate_signal(self, signal: Signal, market_state: MarketState) -> QualityScore:
        """
        Evalúa calidad completa de señal.
        """
        # Dimensión 1: Pedigree
        pedigree_score = self._calculate_pedigree(signal.strategy_id)

        # Dimensión 2: Signal Strength
        signal_score = self._calculate_signal_strength(signal)

        # Dimensión 3: Microstructure ← MANDATO 5
        microstructure_score = self.microstructure_engine.get_current_score(
            symbol=signal.symbol,
            direction=signal.direction
        )

        # Dimensión 4: Data Health
        data_health_score = self._calculate_data_health(signal.symbol)

        # Dimensión 5: Portfolio Context
        portfolio_score = self._calculate_portfolio_context(signal)

        # Agregación
        quality_score = (
            self.weights['pedigree'] * pedigree_score +
            self.weights['signal'] * signal_score +
            self.weights['microstructure'] * microstructure_score +
            self.weights['data_health'] * data_health_score +
            self.weights['portfolio'] * portfolio_score
        )

        return QualityScore(
            overall=quality_score,
            pedigree=pedigree_score,
            signal=signal_score,
            microstructure=microstructure_score,
            data_health=data_health_score,
            portfolio=portfolio_score,
        )
```

### MicrostructureEngine Interface

```python
class MicrostructureEngine:
    """
    Engine principal que orquesta todos los componentes de microestructura.
    """
    def __init__(self, config: Dict[str, Any]):
        self.vpin_estimator = VPINEstimator(config['vpin'])
        self.orderflow_analyzer = OrderFlowAnalyzer(config['orderflow'])
        self.level2_monitor = Level2DepthMonitor(config['level2'])
        self.spoofing_detector = SpoofingDetector(config['spoofing'])
        self.scorer = MicrostructureScorer(config['scorer'])

        # State tracking por símbolo
        self.current_state = {}  # {symbol: MicrostructureInputs}

    def process_tick(self, tick: Tick):
        """
        Procesa tick de mercado y actualiza estado.
        """
        symbol = tick.symbol

        # Clasificar trade
        mid_price = self._get_mid_price(symbol)
        prev_mid = self._get_prev_mid_price(symbol)
        side = classify_trade(tick.price, mid_price, prev_mid)

        # Actualizar componentes
        vpin = self.vpin_estimator.process_trade(tick, mid_price, prev_mid)
        self.orderflow_analyzer.add_trade(tick, side)

        # Actualizar estado si hay nuevo VPIN
        if vpin is not None:
            self._update_state(symbol)

    def process_level2_snapshot(self, snapshot: Level2Snapshot):
        """
        Procesa snapshot de Level 2 y actualiza estado.
        """
        symbol = snapshot.symbol

        # Actualizar componentes
        self.level2_monitor.update_snapshot(snapshot)

        # Track orders para spoofing detection
        # (requiere lógica adicional de diff entre snapshots)

        self._update_state(symbol)

    def get_current_score(self, symbol: str, direction: str) -> float:
        """
        Retorna microstructure score actual para un símbolo y dirección.

        Este método es llamado por QualityScorer.
        """
        if symbol not in self.current_state:
            return 0.50  # Score neutral si no hay datos

        inputs = self.current_state[symbol]

        return self.scorer.calculate_microstructure_score(inputs, direction)

    def _update_state(self, symbol: str):
        """
        Actualiza estado interno con señales más recientes.
        """
        # Obtener señales actuales
        vpin_signal = self._get_latest_vpin_signal(symbol)
        orderflow_signal = self._get_latest_orderflow_signal(symbol)
        level2_signal = self._get_latest_level2_signal(symbol)
        spoofing_signal = self._get_latest_spoofing_signal(symbol)

        # Actualizar state
        self.current_state[symbol] = MicrostructureInputs(
            vpin_signal=vpin_signal,
            orderflow_signal=orderflow_signal,
            level2_signal=level2_signal,
            spoofing_signal=spoofing_signal,
        )
```

---

## CALIBRACIÓN Y THRESHOLDS

### Thresholds por Símbolo

```python
MICROSTRUCTURE_THRESHOLDS = {
    'EURUSD': {
        'vpin': {
            'safe_max': 0.30,
            'warning': 0.50,
            'block': 0.60,
        },
        'ofi': {
            'strong_threshold': 0.60,
            'weak_threshold': 0.30,
        },
        'depth': {
            'min_liquidity_ratio': 0.60,  # vs typical
            'max_spread_ratio': 1.50,     # vs typical
            'wall_threshold_ratio': 3.0,  # vs avg quantity
        },
        'spoofing': {
            'fast_cancel_seconds': 2.0,
            'large_order_ratio': 5.0,
            'min_price_move_bps': 5.0,
        },
    },
    'GBPUSD': {
        'vpin': {'safe_max': 0.30, 'warning': 0.50, 'block': 0.60},
        'ofi': {'strong_threshold': 0.60, 'weak_threshold': 0.30},
        'depth': {'min_liquidity_ratio': 0.55, 'max_spread_ratio': 1.60, 'wall_threshold_ratio': 3.0},
        'spoofing': {'fast_cancel_seconds': 2.0, 'large_order_ratio': 5.0, 'min_price_move_bps': 6.0},
    },
    'XAUUSD': {
        'vpin': {'safe_max': 0.35, 'warning': 0.55, 'block': 0.65},
        'ofi': {'strong_threshold': 0.65, 'weak_threshold': 0.35},
        'depth': {'min_liquidity_ratio': 0.50, 'max_spread_ratio': 2.00, 'wall_threshold_ratio': 4.0},
        'spoofing': {'fast_cancel_seconds': 3.0, 'large_order_ratio': 6.0, 'min_price_move_bps': 10.0},
    },
    'BTCUSD': {
        'vpin': {'safe_max': 0.40, 'warning': 0.60, 'block': 0.70},
        'ofi': {'strong_threshold': 0.70, 'weak_threshold': 0.40},
        'depth': {'min_liquidity_ratio': 0.40, 'max_spread_ratio': 2.50, 'wall_threshold_ratio': 5.0},
        'spoofing': {'fast_cancel_seconds': 1.5, 'large_order_ratio': 7.0, 'min_price_move_bps': 20.0},
    },
    'US50': {
        'vpin': {'safe_max': 0.30, 'warning': 0.50, 'block': 0.60},
        'ofi': {'strong_threshold': 0.60, 'weak_threshold': 0.30},
        'depth': {'min_liquidity_ratio': 0.60, 'max_spread_ratio': 1.50, 'wall_threshold_ratio': 3.0},
        'spoofing': {'fast_cancel_seconds': 2.0, 'large_order_ratio': 5.0, 'min_price_move_bps': 5.0},
    },
}
```

### Proceso de Calibración

**Fase 1: Historical Calibration (Backtest)**

```python
def calibrate_microstructure_thresholds(
    historical_data: Dict[str, pd.DataFrame],
    symbol: str
) -> Dict[str, Any]:
    """
    Calibra thresholds usando datos históricos.

    Args:
        historical_data: Dict con 'ticks', 'level2', 'trades'
        symbol: Símbolo a calibrar

    Returns:
        Dict con thresholds calibrados
    """
    # Calcular distribuciones históricas
    vpin_distribution = calculate_vpin_distribution(historical_data['ticks'])
    ofi_distribution = calculate_ofi_distribution(historical_data['trades'])
    spread_distribution = calculate_spread_distribution(historical_data['level2'])
    depth_distribution = calculate_depth_distribution(historical_data['level2'])

    # VPIN thresholds: percentiles 70, 85, 95
    vpin_thresholds = {
        'safe_max': np.percentile(vpin_distribution, 70),
        'warning': np.percentile(vpin_distribution, 85),
        'block': np.percentile(vpin_distribution, 95),
    }

    # OFI thresholds: percentiles 75, 85
    ofi_strong = np.percentile(np.abs(ofi_distribution), 75)
    ofi_weak = np.percentile(np.abs(ofi_distribution), 50)

    ofi_thresholds = {
        'strong_threshold': ofi_strong,
        'weak_threshold': ofi_weak,
    }

    # Depth thresholds: basado en spread y liquidez típica
    typical_spread = np.median(spread_distribution)
    typical_depth = np.median(depth_distribution)

    depth_thresholds = {
        'typical_spread': typical_spread,
        'typical_depth': typical_depth,
        'min_liquidity_ratio': 0.60,
        'max_spread_ratio': 1.50,
        'wall_threshold_ratio': 3.0,
    }

    return {
        'vpin': vpin_thresholds,
        'ofi': ofi_thresholds,
        'depth': depth_thresholds,
    }
```

**Fase 2: Live Adaptation**

```python
class AdaptiveThresholdManager:
    """
    Ajusta thresholds en vivo basado en régimen de mercado.
    """
    def __init__(self, base_thresholds: Dict[str, Any]):
        self.base_thresholds = base_thresholds
        self.current_thresholds = base_thresholds.copy()
        self.regime = 'NORMAL'

    def update_regime(self, market_regime: str):
        """
        Ajusta thresholds según régimen de mercado.

        Args:
            market_regime: 'LOW_VOL', 'NORMAL', 'HIGH_VOL', 'STRESS'
        """
        self.regime = market_regime

        if market_regime == 'LOW_VOL':
            # Ser más estricto con VPIN (menor liquidez)
            self.current_thresholds['vpin']['safe_max'] *= 0.85
            self.current_thresholds['vpin']['block'] *= 0.90

        elif market_regime == 'HIGH_VOL':
            # Ser más permisivo (volatilidad normal en estos regímenes)
            self.current_thresholds['vpin']['safe_max'] *= 1.15
            self.current_thresholds['vpin']['block'] *= 1.10

        elif market_regime == 'STRESS':
            # Muy estricto: evitar trading en stress
            self.current_thresholds['vpin']['safe_max'] *= 0.70
            self.current_thresholds['vpin']['block'] *= 0.80
            self.current_thresholds['depth']['min_liquidity_ratio'] = 0.80

    def get_current_thresholds(self) -> Dict[str, Any]:
        """Retorna thresholds actuales ajustados por régimen."""
        return self.current_thresholds
```

---

## IMPLEMENTACIÓN Y TESTING

### Testing Strategy

#### Unit Tests

```python
class TestVPINEstimator:
    """Tests para VPINEstimator."""

    def test_bucket_accumulation(self):
        """Verifica que buckets se llenen correctamente."""
        estimator = VPINEstimator({'bucket_volume': 100_000, 'vpin_window': 50})

        # Simular trades hasta llenar bucket
        for i in range(100):
            trade = Trade(price=1.1000 + i*0.0001, volume=1000, timestamp=datetime.now())
            vpin = estimator.process_trade(trade, mid_price=1.1000, prev_mid=1.0999)

        assert len(estimator.buckets) > 0
        assert estimator.buckets[-1].accumulated_volume >= 100_000

    def test_vpin_calculation(self):
        """Verifica cálculo de VPIN con imbalances conocidos."""
        estimator = VPINEstimator({'bucket_volume': 100_000, 'vpin_window': 2})

        # Bucket 1: 100% buy
        for i in range(100):
            trade = Trade(price=1.1001, volume=1000, timestamp=datetime.now())
            estimator.process_trade(trade, mid_price=1.1000, prev_mid=1.0999)

        # Bucket 2: 100% sell
        for i in range(100):
            trade = Trade(price=1.0999, volume=1000, timestamp=datetime.now())
            estimator.process_trade(trade, mid_price=1.1000, prev_mid=1.1001)

        vpin = estimator.get_current_vpin()
        assert 0.9 <= vpin <= 1.0  # Debe ser cercano a 1.0 (máximo imbalance)
```

#### Integration Tests

```python
class TestMicrostructureEngine:
    """Tests de integración del engine completo."""

    def test_full_pipeline(self):
        """Verifica pipeline completo desde tick hasta score."""
        config = load_test_config()
        engine = MicrostructureEngine(config)

        # Simular stream de ticks
        ticks = generate_test_ticks(symbol='EURUSD', count=1000)

        for tick in ticks:
            engine.process_tick(tick)

        # Simular snapshots de Level 2
        snapshots = generate_test_level2_snapshots(symbol='EURUSD', count=10)

        for snapshot in snapshots:
            engine.process_level2_snapshot(snapshot)

        # Obtener score
        score = engine.get_current_score(symbol='EURUSD', direction='LONG')

        assert 0.0 <= score <= 1.0
        assert 'EURUSD' in engine.current_state

    def test_latency_requirements(self):
        """Verifica que latencia esté dentro de targets."""
        config = load_test_config()
        engine = MicrostructureEngine(config)

        tick = generate_test_tick(symbol='EURUSD')

        start = time.perf_counter()
        engine.process_tick(tick)
        latency_ms = (time.perf_counter() - start) * 1000

        assert latency_ms < 5.0  # Target: <5ms por tick
```

#### Backtesting

```python
def backtest_microstructure_signals(
    historical_data: Dict[str, pd.DataFrame],
    strategy_signals: List[Signal]
) -> pd.DataFrame:
    """
    Backtests microstructure scoring con datos históricos.

    Returns:
        DataFrame con resultados: signal_id, microstructure_score, actual_slippage, etc.
    """
    config = load_config()
    engine = MicrostructureEngine(config)

    results = []

    # Procesar datos históricos
    for tick in historical_data['ticks'].itertuples():
        engine.process_tick(tick)

    for snapshot in historical_data['level2'].itertuples():
        engine.process_level2_snapshot(snapshot)

    # Evaluar señales
    for signal in strategy_signals:
        score = engine.get_current_score(
            symbol=signal.symbol,
            direction=signal.direction
        )

        # Buscar ejecución real y slippage
        execution = find_execution_for_signal(signal, historical_data['executions'])

        results.append({
            'signal_id': signal.id,
            'timestamp': signal.timestamp,
            'symbol': signal.symbol,
            'direction': signal.direction,
            'microstructure_score': score,
            'actual_slippage_bps': execution.slippage_bps if execution else None,
            'executed': execution is not None,
        })

    return pd.DataFrame(results)
```

### Validación de Calidad

**Métricas de Validación**:

1. **Correlation Score vs Slippage**: Score alto debe correlacionar con bajo slippage
   - Target: Correlation < -0.40 (negativa)

2. **Rejection Rate en VPIN alto**: Cuando VPIN > 0.60, score debe ser < 0.30
   - Target: 95%+ de casos

3. **Flow Alignment Accuracy**: Señales con flow alineado deben tener mayor win rate
   - Target: +10% vs flow no alineado

4. **False Positive Rate**: Spoofing detector no debe generar >5% falsos positivos
   - Target: <5% en test set

```python
def validate_microstructure_quality(backtest_results: pd.DataFrame):
    """
    Valida calidad del microstructure scoring.
    """
    # Métrica 1: Correlation score vs slippage
    correlation = backtest_results['microstructure_score'].corr(
        backtest_results['actual_slippage_bps']
    )

    print(f"Score-Slippage Correlation: {correlation:.3f}")
    assert correlation < -0.30, "Score debe correlacionar negativamente con slippage"

    # Métrica 2: Rejection en VPIN alto
    high_vpin_cases = backtest_results[backtest_results['vpin'] > 0.60]
    low_score_rate = (high_vpin_cases['microstructure_score'] < 0.30).mean()

    print(f"Low Score Rate en VPIN alto: {low_score_rate:.1%}")
    assert low_score_rate > 0.90, "VPIN alto debe generar scores bajos"

    # Métrica 3: Flow alignment accuracy
    aligned = backtest_results[backtest_results['flow_aligned'] == True]
    not_aligned = backtest_results[backtest_results['flow_aligned'] == False]

    win_rate_aligned = aligned['profitable'].mean()
    win_rate_not_aligned = not_aligned['profitable'].mean()

    print(f"Win Rate Aligned: {win_rate_aligned:.1%}")
    print(f"Win Rate Not Aligned: {win_rate_not_aligned:.1%}")

    assert win_rate_aligned > win_rate_not_aligned, "Flow alignment debe mejorar win rate"
```

---

## CONFIGURACIÓN RECOMENDADA

### Configuración de Producción

```python
MICROSTRUCTURE_CONFIG_PRODUCTION = {
    'vpin': {
        'bucket_volume': {
            'EURUSD': 100_000,
            'GBPUSD': 80_000,
            'XAUUSD': 50_000,
            'BTCUSD': 200_000,
            'US50': 150_000,
        },
        'window_size': 50,  # buckets
    },
    'orderflow': {
        'window_seconds': 60,  # 1 minuto
        'intensity_threshold': 2.0,  # trades/second
    },
    'level2': {
        'depth_levels': 5,
        'snapshot_interval_ms': 100,
    },
    'spoofing': {
        'large_order_ratio': 5.0,
        'fast_cancel_seconds': 2.0,
        'min_price_move_bps': 5.0,
        'lookback_minutes': 5,
    },
    'scorer': {
        'weight_vpin': 0.35,
        'weight_flow': 0.25,
        'weight_depth': 0.25,
        'weight_manip': 0.15,
    },
}
```

### Configuración de Backtest

```python
MICROSTRUCTURE_CONFIG_BACKTEST = {
    'vpin': {
        'bucket_volume': 50_000,  # Menor para más granularidad
        'window_size': 30,
    },
    'orderflow': {
        'window_seconds': 30,  # Ventana más corta
        'intensity_threshold': 1.5,
    },
    'level2': {
        'depth_levels': 10,  # Analizar más profundidad
        'snapshot_interval_ms': 500,  # Menos frecuente
    },
    'spoofing': {
        'large_order_ratio': 4.0,  # Más sensible
        'fast_cancel_seconds': 3.0,
        'min_price_move_bps': 3.0,
        'lookback_minutes': 10,
    },
    'scorer': {
        'weight_vpin': 0.35,
        'weight_flow': 0.25,
        'weight_depth': 0.25,
        'weight_manip': 0.15,
    },
}
```

---

## REFERENCIAS Y BIBLIOGRAFÍA

1. **Easley, D., López de Prado, M., & O'Hara, M. (2012)**
   *"Flow Toxicity and Liquidity in a High-Frequency World"*
   Journal of Financial Markets, 15(2), 217-239.

2. **Lee, C. M., & Ready, M. J. (1991)**
   *"Inferring Trade Direction from Intraday Data"*
   Journal of Finance, 46(2), 733-746.

3. **Hasbrouck, J. (2007)**
   *"Empirical Market Microstructure: The Institutions, Economics, and Econometrics of Securities Trading"*
   Oxford University Press.

4. **Kyle, A. S. (1985)**
   *"Continuous Auctions and Insider Trading"*
   Econometrica, 53(6), 1315-1335.

5. **Cartea, Á., Jaimungal, S., & Penalva, J. (2015)**
   *"Algorithmic and High-Frequency Trading"*
   Cambridge University Press.

6. **Lehalle, C. A., & Laruelle, S. (2018)**
   *"Market Microstructure in Practice"* (2nd Edition)
   World Scientific.

7. **Stoikov, S. (2018)**
   *"The Micro-Price: A High-Frequency Estimator of Future Prices"*
   Quantitative Finance, 18(12), 1959-1966.

---

**FIN DE MICROSTRUCTURE_ENGINE_DESIGN.md**

*Diseño completo de componente de microestructura para SUBLIMINE TradingSystem.*
*Integración con Risk Engine (MANDATO 4) y preparación para MultiFrame Context (siguiente documento).*
