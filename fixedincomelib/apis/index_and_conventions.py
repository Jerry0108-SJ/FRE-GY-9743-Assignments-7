"""Explicit fixing inputs for the course's rate cashflows."""

from fixedincomelib.date import Date
from fixedincomelib.market.basics import AccrualBasis
from fixedincomelib.market.registries import IndexFixingsManager

__all__ = ["qfInsertIndexFixing", "qfInsertTermRateFixing"]


def qfInsertIndexFixing(index, fixing_date, fixing):
    """Insert or replace one daily overnight observation, in decimal-rate units."""
    IndexFixingsManager().insert_fixing(index, Date(fixing_date), fixing)


def qfInsertTermRateFixing(index, effective_date, termination_date, accrual_basis, fixing):
    """Insert the whole-period rate observed at effective_date for a teaching FRA."""
    IndexFixingsManager().insert_term_fixing(
        index, Date(effective_date), Date(termination_date), AccrualBasis(accrual_basis), fixing)
