#!/usr/bin/env python3
"""
Brain Layer Offline Training Script

MANDATO 14: Genera políticas del Brain-layer basadas en performance histórica.

Uso:
    python scripts/train_brain_policies.py [--lookback DAYS] [--output DIR]

Ejemplo:
    python scripts/train_brain_policies.py --lookback 90 --output reports/brain
"""

import sys
import argparse
import logging
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.brain_layer.offline_trainer import BrainOfflineTrainer

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Punto de entrada principal."""
    parser = argparse.ArgumentParser(
        description='Train Brain-layer policies from historical data'
    )
    parser.add_argument(
        '--lookback',
        type=int,
        default=90,
        help='Lookback window in days (default: 90)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output directory for reports (default: reports/brain/)'
    )
    parser.add_argument(
        '--db-config',
        type=str,
        default=None,
        help='Path to reporting_db.yaml (default: config/reporting_db.yaml)'
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("BRAIN OFFLINE TRAINING - STARTING")
    logger.info("=" * 80)
    logger.info(f"Lookback window: {args.lookback} days")
    logger.info(f"Output directory: {args.output or 'reports/brain/'}")
    logger.info("")

    try:
        # Inicializar trainer
        trainer = BrainOfflineTrainer(
            db_config_path=args.db_config,
            lookback_days=args.lookback
        )

        # Ejecutar training completo
        policies = trainer.run_full_training(output_dir=args.output)

        logger.info("")
        logger.info("=" * 80)
        logger.info(f"TRAINING COMPLETE - {len(policies)} policies generated")
        logger.info("=" * 80)
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Review policies in config/brain_policies.yaml")
        logger.info("2. Check report in reports/brain/BRAIN_REPORT_*.md")
        logger.info("3. Restart trading system to load new policies")

        return 0

    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
