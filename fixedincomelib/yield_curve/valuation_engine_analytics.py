"""Rate helpers for term coupons and overnight coupons."""

import numpy as np
import QuantLib as ql

from fixedincomelib.date import Date
from fixedincomelib.market.data_conventions import CompoundingMethod
from fixedincomelib.market.registries import IndexFixingsManager


class ValuationEngineAnalyticsForwardRate:
    """Simple term rate projected before Ts and fixed once at Ts."""

    def __init__(self, model, valuation_parameters_collection, projection_index,
                 effective_date, termination_date, accrual_basis):
        self.model_ = model
        self.projection_index_ = projection_index
        self.effective_date_ = effective_date
        self.termination_date_ = termination_date
        self.accrual_basis_ = accrual_basis
        self.accrued_ = accrual_basis.value.yearFraction(effective_date, termination_date)
        self.index_value_ = None

    def calculate_value(self):
        if self.model_.value_date >= self.effective_date_:
            self.index_value_ = IndexFixingsManager().get_term_fixing(
                self.projection_index_, self.effective_date_, self.termination_date_, self.accrual_basis_)
        else:
            self.df_s_ = self.model_.discount_factor(self.projection_index_, self.effective_date_)
            self.df_e_ = self.model_.discount_factor(self.projection_index_, self.termination_date_)
            self.index_value_ = (self.df_s_ / self.df_e_ - 1.0) / self.accrued_


    def value(self):
        return self.index_value_


class ValuationEngineAnalyticsOvernightIndex:
    """Template overnight helper, with explicit observation intervals.

    Compound coupons multiply daily factors; arithmetic coupons add daily
    interest. Spread is handled outside this helper, without daily compounding.
    Historical means fixing_date < value_date. Today's overnight fixing is used
    if supplied, otherwise projected; term FRA fixings are required on Ts.
    Observation periods span weekends/holidays, with clipped accrual weights
    for an explicit coupon boundary inside an observation period.
    """

    def __init__(self, model, valuation_parameters_collection, overnight_index,
                 effective_date, term_or_termination_date,
                 compounding_method=CompoundingMethod.COMPOUND):
        self.model_ = model
        self.overnight_index_ = overnight_index
        self.effective_date_ = Date(effective_date)
        calendar = overnight_index.fixingCalendar()
        term = term_or_termination_date
        self.termination_date_ = Date(
            calendar.advance(self.effective_date_, term.get_term(), overnight_index.businessDayConvention())
            if term.is_term() else term.get_date())
        self.compounding_method_ = compounding_method
        day_counter = overnight_index.dayCounter()
        self.accrued_ = day_counter.yearFraction(self.effective_date_, self.termination_date_)
        self.intervals_ = []
        observation_start = calendar.adjust(self.effective_date_, ql.Preceding)
        while observation_start < self.termination_date_:
            observation_end = calendar.advance(observation_start, ql.Period("1D"))
            start = max(observation_start, self.effective_date_)
            end = min(observation_end, self.termination_date_)
            full_accrual = day_counter.yearFraction(observation_start, observation_end)
            coupon_accrual = day_counter.yearFraction(start, end)
            self.intervals_.append((Date(observation_start), Date(observation_end),
                                    Date(overnight_index.fixingDate(observation_start)),
                                    coupon_accrual, full_accrual))
            observation_start = observation_end
        self.index_value_ = None

    def calculate_value(self):
        fixings = IndexFixingsManager()
        self.factors_ = []
        for start, end, fixing_date, accrual, full_accrual in self.intervals_:
            historical = fixing_date < self.model_.value_date
            observed_today = (fixing_date == self.model_.value_date and
                              fixings.exist_fixing(self.overnight_index_, fixing_date))
            if historical or observed_today:
                rate = fixings.get_fixing(self.overnight_index_, fixing_date)
                factor = 1.0 + accrual * rate
            else:
                df_s = self.model_.discount_factor(self.overnight_index_, start)
                df_e = self.model_.discount_factor(self.overnight_index_, end)
                weight = accrual / full_accrual
                factor = 1.0 + weight * (df_s / df_e - 1.0)
            self.factors_.append(factor)
        if self.compounding_method_ == CompoundingMethod.COMPOUND:
            amount = np.prod(self.factors_) - 1.0
        else:
            amount = sum(factor - 1.0 for factor in self.factors_)
        self.index_value_ = float(amount / self.accrued_)


    def value(self):
        return self.index_value_
