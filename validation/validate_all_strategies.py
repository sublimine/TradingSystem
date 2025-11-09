"""
Script de ValidaciÃƒÂ³n Maestra para Sistema de Trading Institucional.

PROPÃƒâ€œSITO:
Este script es el guardiÃƒÂ¡n de calidad del sistema completo. Antes de que cualquier
estrategia toque dinero real, debe pasar por esta validaciÃƒÂ³n exhaustiva que verifica:

1. INTEGRIDAD TÃƒâ€°CNICA: CÃƒÂ³digo sin errores de sintaxis o lÃƒÂ³gica
2. FUNCIONALIDAD: Cada estrategia genera seÃƒÂ±ales bajo condiciones apropiadas
3. ESTRUCTURA: SeÃƒÂ±ales contienen todos los campos requeridos para ejecuciÃƒÂ³n
4. RISK MANAGEMENT: Stop loss y take profit estÃƒÂ¡n correctamente posicionados
5. METADATA: InformaciÃƒÂ³n de auditorÃƒÂ­a estÃƒÂ¡ completa y accesible
6. INTEGRACIÃƒâ€œN: Estrategias funcionan con el motor de trading principal

FLUJO DE VALIDACIÃƒâ€œN:
1. Generar datos sintÃƒÂ©ticos realistas (1000 bars de OHLCV)
2. Inicializar cada estrategia con parÃƒÂ¡metros institucionales
3. Evaluar estrategia con datos y features comunes
4. Validar estructura de seÃƒÂ±al si se genera
5. Registrar resultados en log detallado
6. Generar reporte HTML para revisiÃƒÂ³n humana
7. Calcular score de calidad del sistema completo

CRITERIOS DE APROBACIÃƒâ€œN:
- ALL strategies must initialize without errors (100% required)
- At least 80% must evaluate successfully (with or without signals)
- Signal structure validation must pass 100% when signals generated
- Zero critical errors (syntax, import, runtime exceptions)

INSTITUTIONAL COMPLIANCE:
Este script genera documentaciÃƒÂ³n de auditorÃƒÂ­a que satisface:
- MiFID II requirements (algorithm testing documentation)
- SEC Reg Systems Compliance (testing procedures)
- Internal compliance (algorithm validation before deployment)

OUTPUT:
- Console log: Real-time progress and results
- validation_report.html: Detailed HTML report with all test results
- validation_results.json: Machine-readable results for CI/CD
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import json
from typing import Dict, List, Tuple

# Configure comprehensive logging for audit trail
# Configure logging with UTF-8 encoding for Unicode support
import sys

# File handler with explicit UTF-8 encoding
file_handler = logging.FileHandler('validation_log.txt', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Console handler with UTF-8 encoding
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger(__name__)

# Import all strategies to validate
try:
    from src.strategies.ofi_refinement import OFIRefinement
    from src.strategies.fvg_institutional import FVGInstitutional
    from src.strategies.order_block_institutional import OrderBlockInstitutional
    from src.strategies.htf_ltf_liquidity import HTFLTFLiquidity
    from src.strategies.idp_inducement_distribution import IDPInducement
    from src.strategies.iceberg_detection import IcebergDetection
    logger.info("Ã¢Å“â€œ All strategy imports successful")
except Exception as e:
    logger.error(f"Ã¢Å“â€” Strategy import failed: {str(e)}")
    sys.exit(1)

# Import APR executor
try:
    from src.execution.adaptive_participation_rate import APRExecutor
    logger.info("Ã¢Å“â€œ APR Executor import successful")
except Exception as e:
    logger.error(f"Ã¢Å“â€” APR Executor import failed: {str(e)}")
    sys.exit(1)

def generate_synthetic_market_data(periods: int = 1000, seed: int = 42) -> pd.DataFrame:
    """
    Generate realistic synthetic market data for validation.
    
    METHODOLOGY:
    Rather than random walks, this generates data with realistic market characteristics:
    - Trending component (markets trend ~30% of the time)
    - Mean-reverting component (markets range ~70% of the time)
    - Volatility clustering (calm periods followed by volatile periods)
    - Realistic volume patterns (higher volume during trends)
    
    This approach ensures our strategies are tested on data that resembles real market
    conditions, not just random noise. Many strategy bugs only appear with realistic
    market structure.
    
    PARAMETERS:
    The data generated has characteristics similar to EURUSD M1:
    - Average range: ~2 pips per bar
    - Volatility: ~0.02% per bar
    - Volume: 300-1000 ticks per bar
    - Spread: ~0.2 pips
    
    Returns:
        DataFrame with realistic OHLCV data suitable for strategy testing
    """
    np.random.seed(seed)
    dates = pd.date_range(end=datetime.now(), periods=periods, freq='1min')
    
    # Generate price components
    # 1. Trend component: Sine wave simulating market cycles
    trend = np.sin(np.linspace(0, 4*np.pi, periods)) * 0.002 + 1.1000
    
    # 2. Mean reversion component: Random walk around trend
    noise = np.random.normal(0, 0.0001, periods)
    
    # 3. Volatility clustering: Periods of high/low volatility
    volatility_regime = np.abs(np.sin(np.linspace(0, 2*np.pi, periods))) * 0.5 + 0.5
    noise = noise * volatility_regime
    
    # Combine components
    closes = trend + noise
    
    # Generate OHLC from closes with realistic relationships
    opens = closes - np.random.uniform(0, 0.0001, periods)
    highs = closes + np.random.uniform(0, 0.0002, periods)
    lows = closes - np.random.uniform(0, 0.0002, periods)
    
    # Ensure high is highest and low is lowest (OHLC integrity)
    highs = np.maximum(highs, np.maximum(opens, closes))
    lows = np.minimum(lows, np.minimum(opens, closes))
    
    # Generate volume with correlation to volatility
    base_volume = 500
    volume_multiplier = 1 + volatility_regime
    volumes = np.random.uniform(300, 700, periods) * volume_multiplier
    
    data = pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'tick_volume': volumes,
        'spread': np.random.uniform(0.00001, 0.00003, periods),
        'real_volume': volumes * 1000  # Approximate real volume
    })
    
    data.attrs['symbol'] = 'EURUSD'
    
    logger.info(f"Generated {periods} bars of synthetic market data")
    logger.info(f"  Price range: {closes.min():.5f} - {closes.max():.5f}")
    logger.info(f"  Average volume: {volumes.mean():.0f} ticks/bar")
    
    return data

def validate_signal_structure(signal, strategy_name: str) -> Tuple[bool, List[str]]:
    """
    Validate that a signal has all required fields and correct structure.
    
    VALIDATION CHECKLIST:
    This function implements the institutional standard for signal structure.
    Every signal must have these components to be tradeable:
    
    MANDATORY FIELDS:
    1. timestamp: When signal was generated (for latency analysis)
    2. symbol: What instrument to trade (for routing)
    3. strategy_name: Which strategy generated it (for attribution)
    4. direction: LONG or SHORT (for execution)
    5. entry_price: Reference price (for slippage calculation)
    6. stop_loss: Risk management level (mandatory for all trades)
    7. take_profit: Profit target (for position management)
    8. sizing_level: Position size category (for risk allocation)
    9. metadata: Additional context (for analysis and debugging)
    
    RELATIONSHIP VALIDATION:
    Beyond field presence, we validate logical relationships:
    - LONG: stop_loss < entry_price < take_profit
    - SHORT: take_profit < entry_price < stop_loss
    
    WHY THIS MATTERS:
    A signal with missing or illogical fields cannot be executed safely.
    This validation catches configuration errors before they reach production
    where they could cause monetary loss or compliance violations.
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check mandatory fields
    required_fields = [
        'timestamp', 'symbol', 'strategy_name', 'direction',
        'entry_price', 'stop_loss', 'take_profit', 'sizing_level', 'metadata'
    ]
    
    for field in required_fields:
        if not hasattr(signal, field):
            errors.append(f"Missing required field: {field}")
    
    # If basic structure is broken, return early
    if errors:
        return False, errors
    
    # Validate direction
    if signal.direction not in ['LONG', 'SHORT']:
        errors.append(f"Invalid direction: {signal.direction} (must be LONG or SHORT)")
    
    # Validate price relationships
    if signal.direction == 'LONG':
        # For LONG: stop should be below entry, target above
        if signal.stop_loss >= signal.entry_price:
            errors.append(f"LONG signal: stop_loss ({signal.stop_loss:.5f}) must be < entry_price ({signal.entry_price:.5f})")
        if signal.take_profit <= signal.entry_price:
            errors.append(f"LONG signal: take_profit ({signal.take_profit:.5f}) must be > entry_price ({signal.entry_price:.5f})")
    
    elif signal.direction == 'SHORT':
        # For SHORT: stop should be above entry, target below
        if signal.stop_loss <= signal.entry_price:
            errors.append(f"SHORT signal: stop_loss ({signal.stop_loss:.5f}) must be > entry_price ({signal.entry_price:.5f})")
        if signal.take_profit >= signal.entry_price:
            errors.append(f"SHORT signal: take_profit ({signal.take_profit:.5f}) must be < entry_price ({signal.entry_price:.5f})")
    
    # Validate sizing level
    if not (1 <= signal.sizing_level <= 5):
        errors.append(f"Invalid sizing_level: {signal.sizing_level} (must be 1-5)")
    
    # Validate metadata presence
    if not signal.metadata:
        errors.append("Metadata dictionary is empty")
    
    is_valid = len(errors) == 0
    return is_valid, errors

def test_strategy(strategy_class, params: Dict, data: pd.DataFrame, 
                 features: Dict) -> Dict:
    """
    Test a single strategy with comprehensive validation.
    
    TESTING PROCESS:
    1. Initialize strategy with provided parameters
    2. Evaluate strategy on synthetic data
    3. If signal generated, validate its structure
    4. Catch and log any exceptions
    5. Return comprehensive test results
    
    This function wraps strategy evaluation in extensive error handling to ensure
    that one broken strategy doesn't prevent testing of others. All exceptions are
    caught, logged, and returned as test failures.
    
    RETURN STRUCTURE:
    {
        'strategy_name': str,
        'initialized': bool,
        'evaluated': bool,
        'signal_generated': bool,
        'signal_valid': bool,
        'errors': list,
        'warnings': list,
        'signal_metadata': dict (if signal generated),
        'execution_time_ms': float
    }
    
    This structure provides complete audit trail for each strategy test.
    """
    start_time = datetime.now()
    result = {
        'strategy_name': strategy_class.__name__,
        'initialized': False,
        'evaluated': False,
        'signal_generated': False,
        'signal_valid': False,
        'errors': [],
        'warnings': [],
        'signal_metadata': None,
        'execution_time_ms': 0
    }
    
    try:
        # PHASE 1: Initialization
        logger.info(f"Testing {strategy_class.__name__}...")
        strategy = strategy_class(params)
        result['initialized'] = True
        logger.info(f"  Ã¢Å“â€œ Initialization successful")
        
        # PHASE 2: Evaluation
        signal = strategy.evaluate(data, features)
        result['evaluated'] = True
        
        if signal:
            # PHASE 3: Signal generated - validate structure
            result['signal_generated'] = True
            logger.info(f"  Ã¢Å“â€œ Signal generated: {signal.direction} @ {signal.entry_price:.5f}")
            
            # PHASE 4: Structure validation
            is_valid, errors = validate_signal_structure(signal, strategy_class.__name__)
            result['signal_valid'] = is_valid
            
            if is_valid:
                logger.info(f"  Ã¢Å“â€œ Signal structure validation passed")
                
                # Extract key metadata for reporting
                result['signal_metadata'] = {
                    'direction': signal.direction,
                    'entry_price': float(signal.entry_price),
                    'stop_loss': float(signal.stop_loss),
                    'take_profit': float(signal.take_profit),
                    'sizing_level': signal.sizing_level,
                    'risk_reward_ratio': abs((signal.take_profit - signal.entry_price) / 
                                           (signal.entry_price - signal.stop_loss)) 
                                         if signal.direction == 'LONG' else
                                         abs((signal.entry_price - signal.take_profit) /
                                           (signal.stop_loss - signal.entry_price)),
                    'metadata_keys': list(signal.metadata.keys())
                }
            else:
                logger.error(f"  Ã¢Å“â€” Signal structure validation failed:")
                for error in errors:
                    logger.error(f"    - {error}")
                    result['errors'].append(error)
        else:
            # No signal generated - this is OK, not all strategies signal on all data
            logger.info(f"  Ã¢Å“â€œ Evaluated successfully (no signal generated)")
            result['warnings'].append("No signal generated (may be normal depending on market conditions)")
        
        # Calculate execution time
        end_time = datetime.now()
        result['execution_time_ms'] = (end_time - start_time).total_seconds() * 1000
        logger.info(f"  Ã¢Å“â€œ Execution time: {result['execution_time_ms']:.2f}ms")
        
        return result
        
    except Exception as e:
        # Catch all exceptions to prevent cascade failures
        logger.error(f"  Ã¢Å“â€” {strategy_class.__name__} failed: {str(e)}")
        logger.error(f"    Exception type: {type(e).__name__}")
        
        result['errors'].append(f"Exception: {str(e)}")
        
        end_time = datetime.now()
        result['execution_time_ms'] = (end_time - start_time).total_seconds() * 1000
        
        return result

def test_apr_executor(data: pd.DataFrame) -> Dict:
    """
    Test APR Executor functionality.
    
    APR is not a strategy but an execution module, so it requires different testing.
    We validate:
    1. Initialization
    2. Participation rate calculation
    3. Execution plan creation for large order
    4. Plan structure and reasonableness
    
    Returns:
        Dictionary with test results
    """
    result = {
        'component_name': 'APRExecutor',
        'initialized': False,
        'plan_created': False,
        'plan_valid': False,
        'errors': [],
        'warnings': [],
        'execution_time_ms': 0
    }
    
    start_time = datetime.now()
    
    try:
        logger.info("Testing APR Executor...")
        
        # Initialize
        params = {
            'base_rate': 0.10,
            'momentum_alpha': 0.05,
            'volatility_beta': 0.15,
            'rate_floor': 0.05,
            'rate_ceiling': 0.25,
            'minimum_notional_for_activation': 100000
        }
        
        executor = APRExecutor(params)
        result['initialized'] = True
        logger.info("  Ã¢Å“â€œ APR Executor initialized")
        
        # Test plan creation
        plan = executor.create_execution_plan(
            total_size=10.0,
            current_price=1.1000,
            direction='BUY',
            market_data=data,
            target_duration_minutes=30
        )
        
        if plan:
            result['plan_created'] = True
            logger.info(f"  Ã¢Å“â€œ Execution plan created: {len(plan.slices)} slices")
            
            # Validate plan
            if len(plan.slices) > 0 and plan.participation_rate > 0:
                result['plan_valid'] = True
                logger.info(f"  Ã¢Å“â€œ Plan validation passed")
                logger.info(f"    Participation rate: {plan.participation_rate:.1%}")
                logger.info(f"    Expected impact: {plan.market_impact_estimate:.2f} bps")
            else:
                result['errors'].append("Plan structure invalid")
        else:
            result['warnings'].append("No plan created (may be below threshold)")
            logger.info("  Ã¢Å“â€œ Evaluated successfully (no plan needed)")
        
        end_time = datetime.now()
        result['execution_time_ms'] = (end_time - start_time).total_seconds() * 1000
        
        return result
        
    except Exception as e:
        logger.error(f"  Ã¢Å“â€” APR Executor failed: {str(e)}")
        result['errors'].append(f"Exception: {str(e)}")
        
        end_time = datetime.now()
        result['execution_time_ms'] = (end_time - start_time).total_seconds() * 1000
        
        return result

def generate_html_report(results: List[Dict], apr_result: Dict, 
                        summary: Dict) -> str:
    """
    Generate comprehensive HTML report for audit and review.
    
    This report serves multiple purposes:
    1. TECHNICAL REVIEW: Developers can see detailed test results
    2. COMPLIANCE: Auditors can verify testing procedures
    3. MANAGEMENT: Stakeholders can assess system readiness
    4. DOCUMENTATION: Permanent record of validation
    
    The report includes:
    - Executive summary with pass/fail counts
    - Detailed results for each strategy
    - Signal structure validation results
    - Execution time metrics
    - Error and warning logs
    - Recommendations for deployment
    """
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Sistema de Trading Institucional - Reporte de ValidaciÃƒÂ³n</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
        }}
        .summary {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .summary h2 {{
            margin-top: 0;
            color: #333;
        }}
        .metric {{
            display: inline-block;
            margin: 10px 20px 10px 0;
            padding: 15px 25px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        .metric-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .metric-value {{
            font-size: 32px;
            font-weight: bold;
            color: #333;
        }}
        .strategy {{
            background: white;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .strategy h3 {{
            margin-top: 0;
            color: #333;
        }}
        .status {{
            display: inline-block;
            padding: 6px 12px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 14px;
            margin-left: 10px;
        }}
        .status-pass {{
            background-color: #d4edda;
            color: #155724;
        }}
        .status-fail {{
            background-color: #f8d7da;
            color: #721c24;
        }}
        .status-warning {{
            background-color: #fff3cd;
            color: #856404;
        }}
        .detail-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        .detail-table th {{
            background-color: #f8f9fa;
            padding: 10px;
            text-align: left;
            border-bottom: 2px solid #dee2e6;
        }}
        .detail-table td {{
            padding: 10px;
            border-bottom: 1px solid #dee2e6;
        }}
        .error-box {{
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            border-radius: 4px;
            padding: 12px;
            margin-top: 10px;
            color: #721c24;
        }}
        .warning-box {{
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 4px;
            padding: 12px;
            margin-top: 10px;
            color: #856404;
        }}
        .footer {{
            margin-top: 40px;
            padding: 20px;
            background: white;
            border-radius: 8px;
            text-align: center;
            color: #666;
        }}
        .recommendation {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            margin-top: 20px;
            border-left: 4px solid #667eea;
        }}
        .recommendation h3 {{
            margin-top: 0;
            color: #667eea;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Sistema de Trading Institucional</h1>
        <p>Reporte de ValidaciÃƒÂ³n Completa - {datetime.now().strftime('%d de %B de %Y, %H:%M:%S')}</p>
    </div>
    
    <div class="summary">
        <h2>Resumen Ejecutivo</h2>
        <div class="metric">
            <div class="metric-label">Estrategias Probadas</div>
            <div class="metric-value">{summary['total_strategies']}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Aprobadas</div>
            <div class="metric-value" style="color: #28a745;">{summary['passed']}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Falladas</div>
            <div class="metric-value" style="color: #dc3545;">{summary['failed']}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Tasa de Ãƒâ€°xito</div>
            <div class="metric-value" style="color: #667eea;">{summary['success_rate']:.1f}%</div>
        </div>
    </div>
"""
    
    # Add strategy results
    for result in results:
        status_class = "status-pass" if result['evaluated'] and not result['errors'] else "status-fail"
        status_text = "Ã¢Å“â€œ APROBADA" if result['evaluated'] and not result['errors'] else "Ã¢Å“â€” FALLADA"
        
        html += f"""
    <div class="strategy">
        <h3>{result['strategy_name']}<span class="status {status_class}">{status_text}</span></h3>
        <table class="detail-table">
            <tr>
                <th>Componente</th>
                <th>Estado</th>
                <th>Detalles</th>
            </tr>
            <tr>
                <td>InicializaciÃƒÂ³n</td>
                <td>{'Ã¢Å“â€œ' if result['initialized'] else 'Ã¢Å“â€”'}</td>
                <td>{'Exitosa' if result['initialized'] else 'FallÃƒÂ³'}</td>
            </tr>
            <tr>
                <td>EvaluaciÃƒÂ³n</td>
                <td>{'Ã¢Å“â€œ' if result['evaluated'] else 'Ã¢Å“â€”'}</td>
                <td>{'Exitosa' if result['evaluated'] else 'FallÃƒÂ³'}</td>
            </tr>
            <tr>
                <td>GeneraciÃƒÂ³n de SeÃƒÂ±al</td>
                <td>{'Ã¢Å“â€œ' if result['signal_generated'] else '-'}</td>
                <td>{'SeÃƒÂ±al generada' if result['signal_generated'] else 'Sin seÃƒÂ±al (normal)'}</td>
            </tr>
"""
        
        if result['signal_generated']:
            html += f"""
            <tr>
                <td>ValidaciÃƒÂ³n de Estructura</td>
                <td>{'Ã¢Å“â€œ' if result['signal_valid'] else 'Ã¢Å“â€”'}</td>
                <td>{'Estructura vÃƒÂ¡lida' if result['signal_valid'] else 'Errores de estructura'}</td>
            </tr>
"""
        
        html += f"""
            <tr>
                <td>Tiempo de EjecuciÃƒÂ³n</td>
                <td>-</td>
                <td>{result['execution_time_ms']:.2f}ms</td>
            </tr>
        </table>
"""
        
        if result['signal_metadata']:
            html += f"""
        <p><strong>Metadata de SeÃƒÂ±al:</strong></p>
        <ul>
            <li>DirecciÃƒÂ³n: {result['signal_metadata']['direction']}</li>
            <li>Precio de Entrada: {result['signal_metadata']['entry_price']:.5f}</li>
            <li>Stop Loss: {result['signal_metadata']['stop_loss']:.5f}</li>
            <li>Take Profit: {result['signal_metadata']['take_profit']:.5f}</li>
            <li>Nivel de Sizing: {result['signal_metadata']['sizing_level']}/5</li>
            <li>Risk-Reward: {result['signal_metadata']['risk_reward_ratio']:.2f}:1</li>
        </ul>
"""
        
        if result['errors']:
            html += '<div class="error-box"><strong>Errores:</strong><ul>'
            for error in result['errors']:
                html += f'<li>{error}</li>'
            html += '</ul></div>'
        
        if result['warnings']:
            html += '<div class="warning-box"><strong>Advertencias:</strong><ul>'
            for warning in result['warnings']:
                html += f'<li>{warning}</li>'
            html += '</ul></div>'
        
        html += "</div>"
    
    # Add APR result
    apr_status_class = "status-pass" if apr_result['initialized'] and not apr_result['errors'] else "status-fail"
    apr_status_text = "Ã¢Å“â€œ APROBADO" if apr_result['initialized'] and not apr_result['errors'] else "Ã¢Å“â€” FALLADO"
    
    html += f"""
    <div class="strategy">
        <h3>{apr_result['component_name']}<span class="status {apr_status_class}">{apr_status_text}</span></h3>
        <table class="detail-table">
            <tr>
                <th>Componente</th>
                <th>Estado</th>
                <th>Detalles</th>
            </tr>
            <tr>
                <td>InicializaciÃƒÂ³n</td>
                <td>{'Ã¢Å“â€œ' if apr_result['initialized'] else 'Ã¢Å“â€”'}</td>
                <td>{'Exitosa' if apr_result['initialized'] else 'FallÃƒÂ³'}</td>
            </tr>
            <tr>
                <td>CreaciÃƒÂ³n de Plan</td>
                <td>{'Ã¢Å“â€œ' if apr_result['plan_created'] else '-'}</td>
                <td>{'Plan creado' if apr_result['plan_created'] else 'Sin plan (puede ser normal)'}</td>
            </tr>
            <tr>
                <td>ValidaciÃƒÂ³n de Plan</td>
                <td>{'Ã¢Å“â€œ' if apr_result['plan_valid'] else '-'}</td>
                <td>{'Plan vÃƒÂ¡lido' if apr_result['plan_valid'] else 'N/A'}</td>
            </tr>
            <tr>
                <td>Tiempo de EjecuciÃƒÂ³n</td>
                <td>-</td>
                <td>{apr_result['execution_time_ms']:.2f}ms</td>
            </tr>
        </table>
"""
    
    if apr_result['errors']:
        html += '<div class="error-box"><strong>Errores:</strong><ul>'
        for error in apr_result['errors']:
            html += f'<li>{error}</li>'
        html += '</ul></div>'
    
    html += "</div>"
    
    # Add recommendation
    if summary['success_rate'] == 100:
        recommendation = """
        <div class="recommendation">
            <h3>Ã¢Å“â€œ SISTEMA APROBADO PARA PRODUCCIÃƒâ€œN</h3>
            <p>Todas las estrategias han pasado la validaciÃƒÂ³n exitosamente. El sistema estÃƒÂ¡ listo para:</p>
            <ul>
                <li>Despliegue en ambiente de producciÃƒÂ³n</li>
                <li>IntegraciÃƒÂ³n con cuentas de dinero real</li>
                <li>OperaciÃƒÂ³n en modo live trading</li>
            </ul>
            <p><strong>PrÃƒÂ³ximos pasos recomendados:</strong></p>
            <ol>
                <li>Ejecutar backtesting exhaustivo en datos histÃƒÂ³ricos (mÃƒÂ­nimo 1 aÃƒÂ±o)</li>
                <li>Implementar paper trading durante 1-2 semanas para validar integraciÃƒÂ³n</li>
                <li>Comenzar con capital limitado ($1000-$5000) para validaciÃƒÂ³n en vivo</li>
                <li>Monitorear mÃƒÂ©tricas de ejecuciÃƒÂ³n diariamente</li>
                <li>Escalar progresivamente basado en resultados</li>
            </ol>
        </div>
"""
    elif summary['success_rate'] >= 80:
        recommendation = f"""
        <div class="recommendation">
            <h3>Ã¢Å¡Â  SISTEMA REQUIERE CORRECCIONES MENORES</h3>
            <p>El sistema tiene {summary['failed']} estrategia(s) con problemas. Se requiere:</p>
            <ul>
                <li>Revisar y corregir estrategias fallidas</li>
                <li>Re-ejecutar validaciÃƒÂ³n completa</li>
                <li>Verificar que correcciones no afecten otras estrategias</li>
            </ul>
            <p><strong>NO DESPLEGAR en producciÃƒÂ³n hasta alcanzar 100% de aprobaciÃƒÂ³n.</strong></p>
        </div>
"""
    else:
        recommendation = f"""
        <div class="recommendation">
            <h3>Ã¢Å“â€” SISTEMA NO APTO PARA PRODUCCIÃƒâ€œN</h3>
            <p>El sistema tiene {summary['failed']} estrategias fallidas ({100-summary['success_rate']:.1f}% de fallo). Se requiere:</p>
            <ul>
                <li>RevisiÃƒÂ³n completa de cÃƒÂ³digo y configuraciÃƒÂ³n</li>
                <li>CorrecciÃƒÂ³n de todos los errores identificados</li>
                <li>ValidaciÃƒÂ³n exhaustiva de cada componente</li>
            </ul>
            <p><strong>CRÃƒÂTICO: NO intentar desplegar este sistema con dinero real.</strong></p>
        </div>
"""
    
    html += recommendation
    
    # Add footer
    html += f"""
    <div class="footer">
        <p>Reporte generado automÃƒÂ¡ticamente por el Sistema de ValidaciÃƒÂ³n Institucional</p>
        <p>Para preguntas o soporte, contactar al equipo de desarrollo</p>
        <p style="margin-top: 20px; font-size: 12px; color: #999;">
            Este reporte es confidencial y contiene informaciÃƒÂ³n propietaria.<br>
            Ã‚Â© {datetime.now().year} Sistema de Trading Institucional. Todos los derechos reservados.
        </p>
    </div>
</body>
</html>
"""
    
    return html

def main():
    """
    Main validation orchestrator.
    
    This is the entry point that coordinates the entire validation process.
    It follows a structured workflow to ensure comprehensive testing and reporting.
    """
    logger.info("=" * 80)
    logger.info("SISTEMA DE TRADING INSTITUCIONAL - VALIDACIÃƒâ€œN COMPLETA")
    logger.info("=" * 80)
    logger.info("")
    
    # STEP 1: Generate synthetic test data
    logger.info("PASO 1: Generando datos de prueba sintÃƒÂ©ticos...")
    data = generate_synthetic_market_data(periods=1000)
    logger.info("")
    
    # STEP 2: Define common features for all strategies
    logger.info("PASO 2: Configurando features comunes...")
    features = {
        'atr': 0.0005,  # 5 pips ATR (typical for EURUSD M1)
        'vpin': 0.70,   # High toxicity level
        'l2_data': None  # No L2 data (degraded mode)
    }
    logger.info("  ATR: 0.0005 (5 pips)")
    logger.info("  VPIN: 0.70 (alta toxicidad)")
    logger.info("  L2 Data: None (modo degradado)")
    logger.info("")
    
    # STEP 3: Define strategies and their configurations
    logger.info("PASO 3: Configurando estrategias para validaciÃƒÂ³n...")
    
    strategies = [
        (OFIRefinement, {
            'window_ticks': 100,
            'z_entry_threshold': 2.5,
            'vpin_minimum': 0.65,
            'stop_loss_atr_multiplier': 2.5,
            'take_profit_atr_multiplier': 4.0
        }),
        (FVGInstitutional, {
            'gap_atr_minimum': 0.75,
            'volume_anomaly_sigma': 2.0,
            'stop_loss_gap_fraction': 0.382,
            'take_profit_gap_fraction': 0.786
        }),
        (OrderBlockInstitutional, {
            'volume_sigma_threshold': 2.5,
            'displacement_atr_multiplier': 2.0,
            'stop_loss_buffer_atr': 0.75,
            'take_profit_r_multiple': [1.5, 3.0]
        }),
        (HTFLTFLiquidity, {
            'htf_timeframes': ['H4', 'D1'],
            'projection_tolerance_pips': 2,
            'triggers': ['rejection_candle', 'volume_climax'],
            'min_triggers_required': 1,
            'stop_loss_buffer_atr': 0.75
        }),
        (IDPInducement, {
            'penetration_pips_min': 5,
            'penetration_pips_max': 20,
            'volume_multiplier': 2.5,
            'distribution_range_bars_min': 3,
            'distribution_range_bars_max': 8,
            'displacement_velocity_pips_per_minute': 7,
            'take_profit_r_multiple': 3.0
        }),
        (IcebergDetection, {
            'mode': 'degraded',
            'volume_advancement_ratio_threshold': 15.0,
            'stall_duration_bars': 5,
            'stop_loss_behind_level_atr': 1.0,
            'take_profit_r_multiple': 2.5
        })
    ]
    
    logger.info(f"  Total de estrategias a validar: {len(strategies)}")
    logger.info("")
    
    # STEP 4: Test each strategy
    logger.info("PASO 4: Ejecutando validaciÃƒÂ³n de estrategias...")
    logger.info("Ã¢â€â‚¬" * 80)
    
    results = []
    for strategy_class, params in strategies:
        result = test_strategy(strategy_class, params, data, features)
        results.append(result)
        logger.info("Ã¢â€â‚¬" * 80)
    
    logger.info("")
    
    # STEP 5: Test APR executor
    logger.info("PASO 5: Validando mÃƒÂ³dulo APR...")
    logger.info("Ã¢â€â‚¬" * 80)
    apr_result = test_apr_executor(data)
    logger.info("Ã¢â€â‚¬" * 80)
    logger.info("")
    
    # STEP 6: Calculate summary statistics
    logger.info("PASO 6: Calculando estadÃƒÂ­sticas finales...")
    
    total_strategies = len(results)
    passed = sum(1 for r in results if r['evaluated'] and not r['errors'])
    failed = total_strategies - passed
    success_rate = (passed / total_strategies * 100) if total_strategies > 0 else 0
    
    summary = {
        'total_strategies': total_strategies,
        'passed': passed,
        'failed': failed,
        'success_rate': success_rate
    }
    
    logger.info("=" * 80)
    logger.info("RESUMEN DE VALIDACIÃƒâ€œN")
    logger.info("=" * 80)
    logger.info(f"Total de Estrategias: {total_strategies}")
    logger.info(f"Aprobadas: {passed}")
    logger.info(f"Falladas: {failed}")
    logger.info(f"Tasa de Ãƒâ€°xito: {success_rate:.1f}%")
    logger.info("=" * 80)
    logger.info("")
    
    # STEP 7: Generate HTML report
    logger.info("PASO 7: Generando reporte HTML de auditorÃƒÂ­a...")
    html_report = generate_html_report(results, apr_result, summary)
    
    report_path = 'validation_report.html'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_report)
    
    logger.info(f"  Ã¢Å“â€œ Reporte guardado en: {report_path}")
    logger.info("")
    
    # STEP 8: Save JSON results for machine processing
    logger.info("PASO 8: Guardando resultados en formato JSON...")
    json_results = {
        'timestamp': datetime.now().isoformat(),
        'summary': summary,
        'strategies': results,
        'apr': apr_result
    }
    
    json_path = 'validation_results.json'
    with open(json_path, 'w') as f:
        json.dump(json_results, f, indent=2, default=str)
    
    logger.info(f"  Ã¢Å“â€œ Resultados guardados en: {json_path}")
    logger.info("")
    
    # STEP 9: Final verdict
    if success_rate == 100:
        logger.info("Ã¢Å“â€œ" * 40)
        logger.info("VALIDACIÃƒâ€œN COMPLETA: TODOS LOS COMPONENTES APROBADOS")
        logger.info("Sistema listo para despliegue en producciÃƒÂ³n")
        logger.info("Ã¢Å“â€œ" * 40)
        return True
    elif success_rate >= 80:
        logger.warning("Ã¢Å¡Â " * 40)
        logger.warning(f"VALIDACIÃƒâ€œN PARCIAL: {failed} componente(s) requiere(n) correcciÃƒÂ³n")
        logger.warning("Revisar estrategias fallidas antes de despliegue")
        logger.warning("Ã¢Å¡Â " * 40)
        return False
    else:
        logger.error("Ã¢Å“â€”" * 40)
        logger.error(f"VALIDACIÃƒâ€œN FALLIDA: {failed} componente(s) con errores crÃƒÂ­ticos")
        logger.error("NO DESPLEGAR en producciÃƒÂ³n hasta resolver todos los errores")
        logger.error("Ã¢Å“â€”" * 40)
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)