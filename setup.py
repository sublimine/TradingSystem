"""
Setup configuration for Institutional Trading System
Permite instalar el proyecto en modo editable para desarrollo.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Leer README si existe
readme_file = Path(__file__).parent / "README.md"
long_description = ""
if readme_file.exists():
    long_description = readme_file.read_text(encoding="utf-8")

setup(
    name="institutional-trading-system",
    version="0.1.0",
    author="Trading System Developer",
    description="Institutional-grade algorithmic trading system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.11",
    
    # Encontrar todos los paquetes en src/
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    
    # Dependencias de runtime
    install_requires=[
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "pyyaml>=6.0",
        "python-dateutil>=2.8.0",
        "pytz>=2023.0",
        "scikit-learn>=1.3.0",
        "scipy>=1.11.0",
    ],
    
    # Dependencias opcionales
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "hypothesis>=6.82.0",
        ],
        "optimization": [
            "cvxpy>=1.4.0",
        ],
    },
    
    # Clasificadores
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "Programming Language :: Python :: 3.11",
    ],
)
