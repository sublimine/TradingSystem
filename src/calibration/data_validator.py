"""
Data Validation for Calibration Pipeline - MANDATO 22

Validates that data is REAL (not synthetic) before running official calibration.

Critical Rules:
- REAL data: Located in data/historical/REAL/ with prefix REAL_*
- SYNTHETIC data: Located in data/historical/ with suffix *_SYNTHETIC.csv
- Official calibration ONLY runs with REAL data
- Synthetic data = BLOCKED status

Author: SUBLIMINE Institutional Trading System
Date: 2025-11-14
Mandato: MANDATO 22 - Orquestación Calibración Real
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DataStatus(Enum):
    """Data availability status."""
    READY = "ready"                    # REAL data available
    BLOCKED_NO_DATA = "blocked_no_data"  # No data files found
    BLOCKED_ONLY_SYNTHETIC = "blocked_only_synthetic"  # Only synthetic data


@dataclass
class DataValidationResult:
    """Result of data validation."""
    status: DataStatus
    real_files: List[Path]
    synthetic_files: List[Path]
    missing_symbols: List[str]
    ready_symbols: List[str]
    message: str


class CalibrationDataValidator:
    """
    Validates data availability for calibration pipeline.

    Rules:
    - REAL data: data/historical/REAL/REAL_*.csv
    - SYNTHETIC data: data/historical/*_SYNTHETIC.csv
    - Official calibration requires REAL data
    """

    def __init__(
        self,
        real_data_dir: str = "data/historical/REAL",
        synthetic_data_dir: str = "data/historical"
    ):
        """
        Initialize validator.

        Args:
            real_data_dir: Directory for REAL data
            synthetic_data_dir: Directory for SYNTHETIC data
        """
        self.real_data_dir = Path(real_data_dir)
        self.synthetic_data_dir = Path(synthetic_data_dir)

    def validate(
        self,
        required_symbols: List[str],
        timeframe: str = "M15"
    ) -> DataValidationResult:
        """
        Validate data availability for calibration.

        Args:
            required_symbols: List of required symbols (e.g., ["EURUSD", "XAUUSD"])
            timeframe: Required timeframe (e.g., "M15")

        Returns:
            DataValidationResult with status and details
        """
        logger.info("=" * 80)
        logger.info("MANDATO 22 - DATA VALIDATION FOR CALIBRATION")
        logger.info("=" * 80)
        logger.info(f"Required symbols: {required_symbols}")
        logger.info(f"Timeframe: {timeframe}")
        logger.info("")

        # Find REAL data files
        real_files = self._find_real_data_files()

        # Find SYNTHETIC data files
        synthetic_files = self._find_synthetic_data_files()

        logger.info(f"REAL data files found: {len(real_files)}")
        for f in real_files:
            logger.info(f"  ✓ {f.name}")

        logger.info(f"SYNTHETIC data files found: {len(synthetic_files)}")
        for f in synthetic_files:
            logger.info(f"  ⚠️  {f.name}")

        logger.info("")

        # Check which required symbols have REAL data
        ready_symbols = []
        missing_symbols = []

        for symbol in required_symbols:
            # Expected filename: REAL_{SYMBOL}_{TIMEFRAME}.csv
            expected_filename = f"REAL_{symbol}_{timeframe}.csv"
            expected_path = self.real_data_dir / expected_filename

            if expected_path.exists():
                ready_symbols.append(symbol)
                logger.info(f"✅ {symbol}: REAL data available ({expected_filename})")
            else:
                missing_symbols.append(symbol)
                logger.warning(f"❌ {symbol}: REAL data MISSING ({expected_filename})")

        logger.info("")

        # Determine status
        if len(real_files) == 0:
            if len(synthetic_files) > 0:
                status = DataStatus.BLOCKED_ONLY_SYNTHETIC
                message = (
                    "BLOCKED: Only SYNTHETIC data available. "
                    "Official calibration requires REAL data from MT5 or broker. "
                    f"Missing REAL data for: {', '.join(missing_symbols)}"
                )
            else:
                status = DataStatus.BLOCKED_NO_DATA
                message = (
                    "BLOCKED: No data files found (REAL or SYNTHETIC). "
                    f"Required REAL data for symbols: {', '.join(required_symbols)}. "
                    "Run: python scripts/download_mt5_history.py"
                )
        elif len(missing_symbols) > 0:
            status = DataStatus.BLOCKED_NO_DATA
            message = (
                f"BLOCKED: Missing REAL data for {len(missing_symbols)} symbols: "
                f"{', '.join(missing_symbols)}. "
                f"Available: {', '.join(ready_symbols)}. "
                "Download missing symbols with: python scripts/download_mt5_history.py"
            )
        else:
            status = DataStatus.READY
            message = (
                f"READY: All {len(ready_symbols)} required symbols have REAL data. "
                "Calibration can proceed."
            )

        result = DataValidationResult(
            status=status,
            real_files=real_files,
            synthetic_files=synthetic_files,
            missing_symbols=missing_symbols,
            ready_symbols=ready_symbols,
            message=message
        )

        logger.info("=" * 80)
        logger.info(f"VALIDATION STATUS: {status.value.upper()}")
        logger.info("=" * 80)
        logger.info(result.message)
        logger.info("=" * 80)
        logger.info("")

        return result

    def _find_real_data_files(self) -> List[Path]:
        """Find REAL data files in real_data_dir."""
        if not self.real_data_dir.exists():
            logger.warning(f"REAL data directory does not exist: {self.real_data_dir}")
            return []

        # Pattern: REAL_*.csv
        real_files = list(self.real_data_dir.glob("REAL_*.csv"))
        return sorted(real_files)

    def _find_synthetic_data_files(self) -> List[Path]:
        """Find SYNTHETIC data files in synthetic_data_dir."""
        if not self.synthetic_data_dir.exists():
            return []

        # Pattern: *_SYNTHETIC.csv
        synthetic_files = list(self.synthetic_data_dir.glob("*_SYNTHETIC.csv"))
        return sorted(synthetic_files)

    def get_available_symbols_from_real_data(self, timeframe: str = "M15") -> List[str]:
        """
        Extract list of symbols from available REAL data files.

        Args:
            timeframe: Timeframe to check

        Returns:
            List of symbol names
        """
        real_files = self._find_real_data_files()

        symbols = []
        for file in real_files:
            # Parse filename: REAL_{SYMBOL}_{TF}.csv
            name = file.stem  # Remove .csv
            parts = name.split("_")

            if len(parts) >= 3 and parts[0] == "REAL":
                symbol = parts[1]
                tf = parts[2]

                if tf == timeframe:
                    symbols.append(symbol)

        return sorted(symbols)
