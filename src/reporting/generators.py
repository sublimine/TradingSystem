"""
Generators - Generación de informes institucionales

Generan informes:
- Diario: PnL, top trades, riesgo, eventos críticos
- Semanal: equity curve, decay signals, quality distribution
- Mensual/Trimestral/Anual: KPIs completos, breakdown, correlaciones

Output: Markdown + JSON

Mandato: MANDATO 11
Fecha: 2025-11-14
"""

import pandas as pd
from datetime import datetime
from typing import Dict
from . import aggregators, metrics


def generate_daily_report(date: datetime, trades: pd.DataFrame,
                         positions: pd.DataFrame, risk_snapshot: Dict) -> str:
    """
    Generar informe diario (Markdown).

    Contenido:
    - PnL del día
    - Top 5 estrategias por contribución/pérdida
    - Top 10 trades (mejores/peores)
    - Riesgo usado vs disponible
    - Eventos críticos
    """
    md = f"# INFORME DIARIO - ALGORITMO INSTITUCIONAL SUBLIMINE\n\n"
    md += f"**Fecha**: {date.strftime('%Y-%m-%d')}\n\n"
    md += "---\n\n"

    # Resumen ejecutivo
    pnl_stats = metrics.calculate_pnl_stats(trades)
    hit_rate = metrics.calculate_hit_rate(trades)
    avg_r = metrics.calculate_avg_r_multiple(trades)

    md += "## RESUMEN EJECUTIVO\n\n"
    md += f"- **PnL Día**: ${pnl_stats.get('pnl_gross', 0):,.2f} ({pnl_stats.get('return_pct', 0):.2f}%)\n"
    md += f"- **Trades**: {len(trades)} ({(trades['pnl_gross']>0).sum()}W / {(trades['pnl_gross']<=0).sum()}L, hit rate {hit_rate*100:.1f}%)\n"
    md += f"- **R promedio**: {avg_r:.2f}R\n"
    md += f"- **Riesgo Usado**: {risk_snapshot.get('total_risk_used_pct', 0):.1f}% (disponible: {risk_snapshot.get('total_risk_available_pct', 100):.1f}%)\n\n"

    # Top estrategias
    strategy_agg = aggregators.aggregate_by_strategy(trades)
    if not strategy_agg.empty:
        top_strategies = strategy_agg.nlargest(5, 'pnl_gross_sum')
        md += "## TOP 5 ESTRATEGIAS (Contribución PnL)\n\n"
        for idx, (strat, row) in enumerate(top_strategies.iterrows(), 1):
            md += f"{idx}. **{strat}**: ${row['pnl_gross_sum']:,.2f} ({int(row['trade_count'])} trades, {int(row['wins'])}W/{int(row['losses'])}L)\n"
        md += "\n"

    # Top trades
    if not trades.empty:
        top_trades = trades.nlargest(5, 'pnl_gross')
        worst_trades = trades.nsmallest(5, 'pnl_gross')

        md += "## TOP 10 TRADES DEL DÍA\n\n"
        md += "### 🏆 Mejores 5\n\n"
        md += "| # | Estrategia | Símbolo | Dir | R | PnL | Risk% | QS | Notas |\n"
        md += "|---|-----------|---------|-----|---|-----|-------|-----|-------|\n"
        for idx, trade in enumerate(top_trades.itertuples(), 1):
            md += f"| {idx} | {trade.strategy_name[:15]} | {trade.symbol} | {trade.direction} | {trade.r_multiple:.1f}R | ${trade.pnl_gross:,.0f} | {trade.risk_pct:.2f}% | {trade.quality_score_total:.2f} | {trade.setup_type[:30]} |\n"

        md += "\n### 💀 Peores 5\n\n"
        md += "| # | Estrategia | Símbolo | Dir | R | PnL | Risk% | QS | Notas |\n"
        md += "|---|-----------|---------|-----|---|-----|-------|-----|-------|\n"
        for idx, trade in enumerate(worst_trades.itertuples(), 1):
            md += f"| {idx} | {trade.strategy_name[:15]} | {trade.symbol} | {trade.direction} | {trade.r_multiple:.1f}R | ${trade.pnl_gross:,.0f} | {trade.risk_pct:.2f}% | {trade.quality_score_total:.2f} | {trade.notes[:30] if hasattr(trade, 'notes') else ''} |\n"

    md += "\n---\n\n**Próxima revisión**: EOD NY session\n"

    return md


def generate_weekly_report(week_start: datetime, week_end: datetime,
                          trades: pd.DataFrame, equity_curve: pd.Series) -> str:
    """
    Generar informe semanal (Markdown).

    Contenido:
    - Curva de equity
    - Evolución de riesgo medio por trade
    - Distribución QualityScore vs retorno
    - Cambios de lifecycle
    - Señales de decay preliminares
    """
    md = f"# INFORME SEMANAL - ALGORITMO INSTITUCIONAL SUBLIMINE\n\n"
    md += f"**Período**: {week_start.strftime('%Y-%m-%d')} - {week_end.strftime('%Y-%m-%d')}\n\n"
    md += "---\n\n"

    # KPIs semanales
    pnl_stats = metrics.calculate_pnl_stats(trades)
    returns = trades['pnl_gross'] / trades['position_size_usd']
    sharpe = metrics.calculate_sharpe_ratio(returns)
    hit_rate = metrics.calculate_hit_rate(trades)

    md += "## KPIs SEMANALES\n\n"
    md += f"- **PnL Semana**: ${pnl_stats['pnl_gross']:,.2f}\n"
    md += f"- **Sharpe (anualizado)**: {sharpe:.2f}\n"
    md += f"- **Hit Rate**: {hit_rate*100:.1f}%\n"
    md += f"- **Trades**: {len(trades)}\n\n"

    # Quality vs Return
    quality_corr = metrics.calculate_quality_vs_return_correlation(trades)
    quality_dist = metrics.calculate_quality_distribution_by_outcome(trades)

    md += "## CALIBRACIÓN DE QUALITY SCORE\n\n"
    md += f"- **Correlación Quality-Return**: {quality_corr:.3f}\n"
    md += f"- **Quality medio (wins)**: {quality_dist.get('wins_avg_quality', 0):.3f}\n"
    md += f"- **Quality medio (losses)**: {quality_dist.get('losses_avg_quality', 0):.3f}\n"
    md += f"- **Gap**: {quality_dist.get('quality_gap', 0):.3f}\n\n"

    if quality_corr < 0.3:
        md += "⚠️ **ALERTA**: Correlación Quality-Return baja (<0.3). Revisar calibración de QualityScorer.\n\n"

    md += "---\n\n**Próxima revisión**: EOW\n"

    return md


def generate_monthly_report(month_start: datetime, month_end: datetime,
                           trades: pd.DataFrame, strategy_perf: pd.DataFrame) -> str:
    """
    Generar informe mensual (Markdown).

    Contenido:
    - KPIs completos: Sharpe, Sortino, Calmar, MAR
    - Drawdown analysis
    - Breakdown por clase, estrategia, región, factor
    - Scatter QualityScore vs retorno
    - Matriz de correlación
    - Anexo de riesgo
    """
    md = f"# INFORME MENSUAL - ALGORITMO INSTITUCIONAL SUBLIMINE\n\n"
    md += f"**Período**: {month_start.strftime('%Y-%m')}\n\n"
    md += "---\n\n"

    # KPIs completos
    pnl_stats = metrics.calculate_pnl_stats(trades)
    equity_curve = metrics.calculate_equity_curve(trades)
    returns = trades['pnl_gross'] / trades['position_size_usd']

    sharpe = metrics.calculate_sharpe_ratio(returns)
    sortino = metrics.calculate_sortino_ratio(returns)
    dd_stats = metrics.calculate_max_drawdown(equity_curve)
    calmar = metrics.calculate_calmar_ratio(returns, dd_stats['max_dd_pct'])

    md += "## KPIs MENSUALES\n\n"
    md += f"- **PnL Mes**: ${pnl_stats['pnl_gross']:,.2f}\n"
    md += f"- **Retorno**: {pnl_stats['return_pct']:.2f}%\n"
    md += f"- **Sharpe (anualizado)**: {sharpe:.2f}\n"
    md += f"- **Sortino**: {sortino:.2f}\n"
    md += f"- **Calmar**: {calmar:.2f}\n"
    md += f"- **Max Drawdown**: {dd_stats['max_dd_pct']:.2f}% ({dd_stats['max_dd_duration_days']} días)\n\n"

    # Breakdown por clase
    asset_class_agg = aggregators.aggregate_by_asset_class(trades)
    if not asset_class_agg.empty:
        md += "## BREAKDOWN POR CLASE DE ACTIVO\n\n"
        md += "| Clase | PnL | Trades | Risk% | Avg R |\n"
        md += "|-------|-----|--------|-------|-------|\n"
        for asset_class, row in asset_class_agg.iterrows():
            md += f"| {asset_class} | ${row['pnl_gross_sum']:,.0f} | {int(row['trade_count'])} | {row['total_risk_pct']:.1f}% | {row['avg_r_multiple']:.2f}R |\n"
        md += "\n"

    # Estrategias
    strategy_agg = aggregators.aggregate_by_strategy(trades)
    if not strategy_agg.empty:
        md += "## PERFORMANCE POR ESTRATEGIA\n\n"
        top_strategies = strategy_agg.nlargest(10, 'pnl_gross_sum')
        md += "| Estrategia | PnL | Trades | Hit Rate | Avg R | Avg Quality |\n"
        md += "|-----------|-----|--------|----------|-------|-------------|\n"
        for strat, row in top_strategies.iterrows():
            md += f"| {strat[:30]} | ${row['pnl_gross_sum']:,.0f} | {int(row['trade_count'])} | {row['hit_rate']*100:.1f}% | {row['avg_r_multiple']:.2f}R | {row['avg_quality_score']:.2f} |\n"
        md += "\n"

    md += "---\n\n**Próxima revisión**: EOM\n"

    return md


def generate_json_summary(trades: pd.DataFrame, metrics_dict: Dict) -> str:
    """Generar resumen JSON estructurado para uso programático."""
    import json

    summary = {
        'timestamp': datetime.now().isoformat(),
        'total_trades': len(trades),
        'pnl_gross': float(metrics_dict.get('pnl_gross', 0)),
        'pnl_net': float(metrics_dict.get('pnl_net', 0)),
        'return_pct': float(metrics_dict.get('return_pct', 0)),
        'sharpe_ratio': float(metrics_dict.get('sharpe_ratio', 0)),
        'hit_rate': float(metrics_dict.get('hit_rate', 0)),
        'avg_r_multiple': float(metrics_dict.get('avg_r_multiple', 0))
    }

    return json.dumps(summary, indent=2)
