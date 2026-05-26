"""
conftest.py — Configuration globale pytest.
Filtre les DeprecationWarnings des dépendances tierces (passlib, httpx)
qui ne sont pas sous notre contrôle.
"""
import warnings
import pytest


def pytest_configure(config):
    """Filtre les warnings de libs tierces au démarrage de pytest."""
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        module="passlib",
    )
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        module="httpx",
    )
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        module="jose",
    )