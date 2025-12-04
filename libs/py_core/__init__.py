"""
Shared Python core utilities for SteadyDancer.

This package is intended to wrap model loading, inference pipelines,
and common utilities that can be reused across API / worker apps.
"""

from .config import get_models_dir

__all__ = ["get_models_dir"]

