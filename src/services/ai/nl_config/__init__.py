"""
Natural Language Configuration Package

Generates CI/CD configurations from natural language descriptions.
"""
from .service import NLConfigService, nl_config_service

__all__ = ["NLConfigService", "nl_config_service"]
