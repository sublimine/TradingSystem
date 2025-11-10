"""
Modulo de Gestion de Riesgo Institucional
Calculo dinamico de tamano de posicion basado en volatilidad y capital
"""

def calculate_position_size(capital: float, risk_pct: float, entry_price: float,
                           stop_loss: float, contract_size: float = 100000,
                           symbol: str = "") -> float:
    """
    Calcula tamano de posicion basado en porcentaje de riesgo del capital.

    Args:
        capital: Capital disponible en cuenta (equity)
        risk_pct: Porcentaje de capital a arriesgar (1.0 = 1%)
        entry_price: Precio de entrada planificado
        stop_loss: Precio de stop loss
        contract_size: Tamano del contrato (100000 para forex standard)
        symbol: Simbolo del instrumento (para detectar tipo)

    Returns:
        Tamano en lotes MT5 (minimo 0.01, maximo 100.0)

    Formula profesional por tipo de instrumento:
        Riesgo_USD = Capital * (risk_pct / 100)
        Distancia = |entry - stop|

        Para Forex (EURUSD, etc.):
            - 4 decimales, pip = 0.0001
            - Valor_pip = 10 USD/pip para 1 lote standard

        Para Metales (XAUUSD, XAGUSD):
            - 2 decimales, pip = 0.01
            - Valor_pip = contract_size * 0.01 (ej: 100oz * $0.01 = $1/pip)

        Para Indices (US30, NAS100):
            - 2 decimales, pip = 1.0
            - Valor_pip = contract_size / precio

        Lotes = Riesgo_USD / (Distancia_en_pips * Valor_pip)
    """
    # Validaciones basicas
    if capital <= 0 or entry_price <= 0:
        return 0.01

    if risk_pct <= 0 or risk_pct > 5:  # Limite maximo 5% por operacion
        risk_pct = 1.0

    # Calcular monto a arriesgar
    risk_money = capital * (risk_pct / 100.0)

    # Calcular distancia al stop
    price_distance = abs(entry_price - stop_loss)

    if price_distance == 0:
        return 0.01

    # Detectar tipo de instrumento y calcular correctamente
    symbol_upper = symbol.upper()

    # Metales preciosos (Oro, Plata)
    if 'XAU' in symbol_upper or 'GOLD' in symbol_upper:
        # Oro: 2 decimales, pip = 0.01
        # Contrato típico: 100 onzas
        pip_size = 0.01
        distance_pips = price_distance / pip_size
        # Valor de 1 pip para 1 lote = contract_size * pip_size
        # Para 1 lote de oro (100 oz): 100 * $0.01 = $1 por pip
        pip_value = contract_size * pip_size

    elif 'XAG' in symbol_upper or 'SILVER' in symbol_upper:
        # Plata: 3 decimales, pip = 0.001
        # Contrato típico: 5000 onzas
        pip_size = 0.001
        distance_pips = price_distance / pip_size
        # Para 1 lote de plata (5000 oz): 5000 * $0.001 = $5 por pip
        pip_value = contract_size * pip_size

    elif 'BTC' in symbol_upper or 'ETH' in symbol_upper:
        # Cripto: Variable, usamos distancia directa
        # Para cripto, simplificamos: riesgo / distancia
        pip_value = 1.0  # Valor de 1 punto de precio
        distance_pips = price_distance

    else:
        # Forex standard (EURUSD, GBPUSD, etc.)
        # 4 o 5 decimales, pip = 0.0001
        pip_size = 0.0001
        distance_pips = price_distance / pip_size
        # Valor de 1 pip para 1 lote standard = $10
        pip_value = 10.0

    # Calcular lotes necesarios
    # lots = Riesgo / (Distancia_pips * Valor_pip)
    lots = risk_money / (distance_pips * pip_value)

    # Redondear a 2 decimales
    lots = round(lots, 2)

    # Aplicar limites
    lots = max(0.01, lots)  # Minimo MT5
    lots = min(100.0, lots)  # Maximo prudente

    return lots


def validate_position_size(lots: float, symbol: str, max_lots: float = 100.0) -> bool:
    """
    Valida que el tamano de posicion sea apropiado.
    
    Args:
        lots: Tamano de posicion en lotes
        symbol: Simbolo del instrumento
        max_lots: Maximo de lotes permitido
        
    Returns:
        True si la posicion es valida
    """
    if lots < 0.01:
        return False
    
    if lots > max_lots:
        return False
    
    # Para cripto, aplicar limites mas restrictivos
    if 'BTC' in symbol or 'ETH' in symbol:
        if lots > 10.0:
            return False
    
    return True


def calculate_stop_loss_atr(current_price: float, atr: float, 
                           direction: str, multiplier: float = 2.0) -> float:
    """
    Calcula stop loss basado en ATR (Average True Range).
    
    Args:
        current_price: Precio actual
        atr: Average True Range
        direction: 'LONG' o 'SHORT'
        multiplier: Multiplicador de ATR (default 2.0)
        
    Returns:
        Precio de stop loss
    """
    if direction.upper() == 'LONG':
        return current_price - (atr * multiplier)
    else:  # SHORT
        return current_price + (atr * multiplier)


def calculate_max_position_exposure(capital: float, max_exposure_pct: float = 10.0) -> float:
    """
    Calcula exposicion maxima permitida en posiciones abiertas.
    
    Args:
        capital: Capital disponible
        max_exposure_pct: Porcentaje maximo de exposicion total
        
    Returns:
        Monto maximo en USD para todas las posiciones
    """
    return capital * (max_exposure_pct / 100.0)
