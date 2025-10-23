"""
Service layer package.

Exports:
- calculate_totals: compute hours and cost totals for an estimate with per-role breakdown.
"""
from .estimate_service import calculate_totals, EstimateTotals

__all__ = ["calculate_totals", "EstimateTotals"]
