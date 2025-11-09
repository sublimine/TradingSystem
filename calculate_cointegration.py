"""
Cálculo de cointegración, hedge ratios y parámetros del sistema
Este es el cerebro matemático que determina los parámetros de trading
"""

import psycopg2
import pandas as pd
import numpy as np
from scipy import stats
from statsmodels.tsa.stattools import adfuller, coint
from statsmodels.tsa.vector_ar.vecm import coint_johansen
import json
from datetime import datetime

# Configuración de PostgreSQL
DB_CONFIG = {
    'host': 'localhost',
    'database': 'trading_system',
    'user': 'postgres',
    'password': 'Trading2025',  # ← CAMBIA ESTO
    'port': 5432
}

# Pares para pairs trading (cointegración)
PAIRS_TO_TEST = [
    ('EURUSD', 'GBPUSD'),
    ('AUDUSD', 'NZDUSD'),
]

def connect_db():
    """Conecta a PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ Error al conectar: {e}")
        return None

def load_daily_prices(conn, symbol):
    """Carga precios de cierre diarios de un símbolo"""
    query = """
        SELECT timestamp, close
        FROM bars
        WHERE symbol = %s AND timeframe = 'D1'
        ORDER BY timestamp ASC
    """
    df = pd.read_sql_query(query, conn, params=(symbol,))
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    return df['close']

def test_cointegration_johansen(prices1, prices2):
    """
    Test de Johansen para cointegración
    Retorna: cointegrado (bool), hedge_ratio (float), eigenvalue, trace_stat
    """
    df = pd.DataFrame({
        'price1': prices1,
        'price2': prices2
    }).dropna()
    
    if len(df) < 50:
        return False, None, None, None
    
    result = coint_johansen(df.values, det_order=0, k_ar_diff=1)
    
    trace_stat = result.lr1[0]
    critical_value_95 = result.cvt[0, 1]
    eigenvalue = result.eig[0]
    is_cointegrated = trace_stat > critical_value_95
    hedge_ratio = result.evec[1, 0] / result.evec[0, 0]
    
    return is_cointegrated, hedge_ratio, eigenvalue, trace_stat

def calculate_half_life(spread):
    """Calcula el half-life de reversión a la media del spread"""
    spread_lag = spread.shift(1).dropna()
    spread_diff = spread.diff().dropna()
    spread_lag = spread_lag[spread_diff.index]
    
    slope, intercept, r_value, p_value, std_err = stats.linregress(
        spread_lag.values, spread_diff.values
    )
    
    if slope < 0:
        half_life = -np.log(2) / np.log(1 + slope)
    else:
        half_life = np.inf
    
    return half_life, slope, p_value

def calculate_atr(conn, symbol, period=14):
    """Calcula Average True Range en múltiples ventanas"""
    query = """
        SELECT timestamp, high, low, close
        FROM bars
        WHERE symbol = %s AND timeframe = 'M1'
        ORDER BY timestamp DESC
        LIMIT 20000
    """
    df = pd.read_sql_query(query, conn, params=(symbol,))
    df = df.sort_values('timestamp')
    
    df['prev_close'] = df['close'].shift(1)
    df['tr'] = df[['high', 'low', 'prev_close']].apply(
        lambda row: max(
            row['high'] - row['low'],
            abs(row['high'] - row['prev_close']) if pd.notna(row['prev_close']) else 0,
            abs(row['low'] - row['prev_close']) if pd.notna(row['prev_close']) else 0
        ),
        axis=1
    )
    
    atr_1h = df['tr'].rolling(window=60).mean().iloc[-1]
    atr_4h = df['tr'].rolling(window=240).mean().iloc[-1]
    atr_1d = df['tr'].rolling(window=1440).mean().iloc[-1]
    
    return {
        '1h': float(atr_1h) if pd.notna(atr_1h) else None,
        '4h': float(atr_4h) if pd.notna(atr_4h) else None,
        '1d': float(atr_1d) if pd.notna(atr_1d) else None
    }

def calculate_correlation(prices1, prices2, windows=[20, 60, 250]):
    """Calcula correlación rolling en múltiples ventanas (días)"""
    df = pd.DataFrame({'p1': prices1, 'p2': prices2}).dropna()
    
    correlations = {}
    for window in windows:
        if len(df) >= window:
            rolling_corr = df['p1'].rolling(window=window).corr(df['p2'])
            correlations[f'{window}d'] = float(rolling_corr.iloc[-1])
    
    return correlations

def save_parameter(conn, param_name, param_value, description):
    """Guarda o actualiza un parámetro en system_parameters"""
    cursor = conn.cursor()
    
    if isinstance(param_value, (dict, list)):
        param_value = json.dumps(param_value)
    elif not isinstance(param_value, str):
        param_value = str(param_value)
    
    query = """
        INSERT INTO system_parameters (parameter_name, parameter_value, description, last_updated)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (parameter_name) 
        DO UPDATE SET 
            parameter_value = EXCLUDED.parameter_value,
            description = EXCLUDED.description,
            last_updated = EXCLUDED.last_updated
    """
    
    cursor.execute(query, (param_name, param_value, description, datetime.now()))
    conn.commit()
    cursor.close()

def main():
    print("=" * 70)
    print("CÁLCULO DE COINTEGRACIÓN Y PARÁMETROS DEL SISTEMA")
    print("=" * 70)
    print()
    
    conn = connect_db()
    if conn is None:
        return
    
    print("📊 PARTE 1: ANÁLISIS DE COINTEGRACIÓN")
    print("=" * 70)
    print()
    
    cointegration_results = {}
    
    for symbol1, symbol2 in PAIRS_TO_TEST:
        print(f"Analizando par: {symbol1} ↔ {symbol2}")
        print("-" * 70)
        
        prices1 = load_daily_prices(conn, symbol1)
        prices2 = load_daily_prices(conn, symbol2)
        
        df = pd.DataFrame({'p1': prices1, 'p2': prices2}).dropna()
        prices1_aligned = df['p1']
        prices2_aligned = df['p2']
        
        print(f"  Datos disponibles: {len(prices1_aligned)} días")
        
        is_coint, hedge_ratio, eigenvalue, trace_stat = test_cointegration_johansen(
            prices1_aligned, prices2_aligned
        )
        
        print(f"  Test de Johansen:")
        print(f"    Trace statistic: {trace_stat:.2f}")
        print(f"    Eigenvalue: {eigenvalue:.4f}")
        print(f"    Cointegrado: {'✅ SÍ' if is_coint else '❌ NO'}")
        
        if is_coint:
            print(f"    Hedge ratio (β): {hedge_ratio:.4f}")
            
            spread = np.log(prices1_aligned) - hedge_ratio * np.log(prices2_aligned)
            half_life, ar_coef, p_value = calculate_half_life(spread)
            
            print(f"    Half-life: {half_life:.2f} días")
            print(f"    AR coefficient: {ar_coef:.4f}")
            print(f"    P-value: {p_value:.4f}")
            
            spread_mean = spread.mean()
            spread_std = spread.std()
            
            print(f"    Spread mean: {spread_mean:.6f}")
            print(f"    Spread std: {spread_std:.6f}")
            
            correlations = calculate_correlation(prices1_aligned, prices2_aligned)
            print(f"    Correlaciones:")
            for window, corr in correlations.items():
                print(f"      {window}: {corr:.4f}")
            
            pair_name = f"{symbol1}_{symbol2}"
            save_parameter(conn, f"coint_{pair_name}_hedge_ratio", hedge_ratio,
                         f"Hedge ratio para pair {symbol1}-{symbol2}")
            save_parameter(conn, f"coint_{pair_name}_half_life", half_life,
                         f"Half-life de reversión en días para {symbol1}-{symbol2}")
            save_parameter(conn, f"coint_{pair_name}_spread_mean", spread_mean,
                         f"Media histórica del spread {symbol1}-{symbol2}")
            save_parameter(conn, f"coint_{pair_name}_spread_std", spread_std,
                         f"Desviación estándar del spread {symbol1}-{symbol2}")
            save_parameter(conn, f"coint_{pair_name}_eigenvalue", eigenvalue,
                         f"Eigenvalue de cointegración {symbol1}-{symbol2}")
            save_parameter(conn, f"coint_{pair_name}_correlations", correlations,
                         f"Correlaciones rolling {symbol1}-{symbol2}")
            
            cointegration_results[pair_name] = {
                'cointegrated': True,
                'hedge_ratio': hedge_ratio,
                'half_life': half_life,
                'spread_mean': spread_mean,
                'spread_std': spread_std,
                'eigenvalue': eigenvalue
            }
        else:
            print(f"    ⚠️  No hay cointegración significativa")
            cointegration_results[f"{symbol1}_{symbol2}"] = {'cointegrated': False}
        
        print()
    
    print()
    print("📈 PARTE 2: CÁLCULO DE VOLATILIDAD (ATR)")
    print("=" * 70)
    print()
    
    symbols = ['EURUSD', 'GBPUSD', 'AUDUSD', 'NZDUSD', 'USDCAD', 'USDJPY']
    
    for symbol in symbols:
        print(f"Calculando ATR para {symbol}...")
        atr_values = calculate_atr(conn, symbol)
        
        atr_1h_str = f"{atr_values['1h']:.6f}" if atr_values['1h'] is not None else 'N/A'
        atr_4h_str = f"{atr_values['4h']:.6f}" if atr_values['4h'] is not None else 'N/A'
        atr_1d_str = f"{atr_values['1d']:.6f}" if atr_values['1d'] is not None else 'N/A'
        
        print(f"  ATR 1 hora:  {atr_1h_str}")
        print(f"  ATR 4 horas: {atr_4h_str}")
        print(f"  ATR 1 día:   {atr_1d_str}")
        
        save_parameter(conn, f"atr_{symbol}", atr_values,
                      f"Average True Range para {symbol} en múltiples ventanas")
        print()
    
    print()
    print("=" * 70)
    print("RESUMEN Y RECOMENDACIONES")
    print("=" * 70)
    print()
    
    tradeable_pairs = [k for k, v in cointegration_results.items() if v.get('cointegrated')]
    
    print(f"Pares cointegrados detectados: {len(tradeable_pairs)}")
    
    if len(tradeable_pairs) == 0:
        print("\n⚠️  NINGÚN PAR MOSTRÓ COINTEGRACIÓN FORMAL")
        print("\nESTRATEGIA RECOMENDADA:")
        print("  → Mean-reversion adaptativa basada en correlación rolling")
        print("  → Momentum microestructural con DOM imbalance")
        print("  → Sin requerir cointegración estadística formal")
    else:
        for pair in tradeable_pairs:
            params = cointegration_results[pair]
            print(f"\n  ✅ {pair.replace('_', ' ↔ ')}")
            print(f"     Hedge ratio: {params['hedge_ratio']:.4f}")
            print(f"     Half-life: {params['half_life']:.2f} días")
            print(f"     Eigenvalue: {params['eigenvalue']:.4f}")
    
    save_parameter(conn, 'last_cointegration_update', datetime.now().strftime('%Y-%m-%d'),
                  'Última fecha de actualización de parámetros de cointegración')
    
    print()
    print("✅ Parámetros calculados y guardados en system_parameters")
    print()
    
    conn.close()

if __name__ == "__main__":
    main()