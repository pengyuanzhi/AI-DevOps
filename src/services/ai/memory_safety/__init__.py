"""
Memory Safety Package

Provides memory safety detection and fix suggestions for C/C++ code.
"""
from .service import MemorySafetyService, memory_safety_service

__all__ = ["MemorySafetyService", "memory_safety_service"]
