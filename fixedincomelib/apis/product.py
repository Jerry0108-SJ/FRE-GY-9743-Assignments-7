"""Create and display cashflows, interest-rate streams and composite products."""

from typing import Optional

import pandas as pd

from fixedincomelib.date.basics import Date, TermOrDate
from fixedincomelib.market.basics import (
    AccrualBasis, BusinessDayConvention, Currency, HolidayConvention,
)
from fixedincomelib.market.data_conventions import CompoundingMethod
from fixedincomelib.product import (
    Product, ProductDisplayVisitor,
    ProductFixedAccruedCashflow, ProductOvernightIndexCashflow,
)

from fixedincomelib.date import Period
from fixedincomelib.market.registries import DataConventionRegistry
from fixedincomelib.product import (
    ProductFactory, PayOrReceive, ProductFRA, ProductRFRSwap,
    ProductOvernightIndexBasisSwap, ProductInterestRateStream,
)


__all__ = [
    "qfCreateProductFixedAccruedCashflow",
    "qfCreateProductOvernightIndexCashflow",
    "qfDisplayProduct",
]


def qfCreateProductFixedAccruedCashflow(
    effective_date: str,
    termination_date: str,
    currency: str,
    notional: float,
    accrual_basis: str,
    payment_date: Optional[str] = "",
    business_day_convention: str = "F",
    holiday_convention: str = "USGS",
) -> ProductFixedAccruedCashflow:
    """Create a fixed-accrual cashflow; omitted payment defaults to termination."""
    return ProductFixedAccruedCashflow(
        Date(effective_date), Date(termination_date), Currency(currency), notional,
        AccrualBasis(accrual_basis),
        None if payment_date is None or payment_date == "" else Date(payment_date),
        BusinessDayConvention(business_day_convention or "F"),
        HolidayConvention(holiday_convention or "USGS"),
    )


def qfCreateProductOvernightIndexCashflow(
    effective_date: str,
    term_or_termination_date: str,
    overnight_index: str,
    notional: float,
    compounding_method: str = "compound",
    spread: float = 0.0,
    payment_date: Optional[str] = "",
) -> ProductOvernightIndexCashflow:
    """Create an overnight cashflow from a date or tenor such as '3M'."""
    return ProductOvernightIndexCashflow(
        Date(effective_date), TermOrDate(term_or_termination_date), overnight_index,
        CompoundingMethod.from_string(compounding_method), spread, notional,
        None if payment_date is None or payment_date == "" else Date(payment_date),
    )


def qfDisplayProduct(product: Product) -> pd.DataFrame:
    """Collect a product's features through its visitor and return Name/Value."""
    visitor = ProductDisplayVisitor()
    product.accept(visitor)
    return visitor.display()


def qfCreateProductFromDataConvention(value_date, data_convention, axis1, values, **kwargs):
    """Create a product using a registered convention and a decimal rate/spread."""
    convention = DataConventionRegistry().get(data_convention)
    return ProductFactory.create_product_from_data_convention(
        Date(value_date), axis1, convention, values, **kwargs)


def qfCreateProductFRA(effective_date, term_or_termination_date, projection_index,
                       fixed_rate, pay_or_rec, notional, accrual_basis="ACT/360",
                       business_day_convention="F", holiday_convention="USGS"):
    """Fix at Ts and pay at Te. Receive means receive fixed/pay the term rate."""
    return ProductFRA(
        Date(effective_date), TermOrDate(term_or_termination_date), projection_index,
        fixed_rate, PayOrReceive.from_string(pay_or_rec), notional, AccrualBasis(accrual_basis),
        BusinessDayConvention(business_day_convention), HolidayConvention(holiday_convention))


def qfCreateProductInterestRateStream(
    effective_date, termination_date, accrual_period, notional, currency,
    accrual_basis, business_day_convention="F", holiday_convention="USGS",
    float_index=None, fixed_rate=None, is_on_index=True, ois_compounding="compound",
    ois_spread=0.0, payment_offset="0D", payment_business_day_convention="F",
    payment_holiday_convention="USGS", rule="BACKWARD", end_of_month=False,
):
    """Create a fixed, overnight, or term-rate leg; None period gives one coupon."""
    return ProductInterestRateStream(
        Date(effective_date), Date(termination_date),
        None if accrual_period is None else Period(accrual_period), notional, Currency(currency),
        AccrualBasis(accrual_basis), BusinessDayConvention(business_day_convention),
        HolidayConvention(holiday_convention), float_index, fixed_rate, is_on_index,
        CompoundingMethod.from_string(ois_compounding), ois_spread,
        payment_offset=Period(payment_offset),
        payment_business_day_convention=BusinessDayConvention(payment_business_day_convention),
        payment_holiday_convention=HolidayConvention(payment_holiday_convention),
        rule=rule, end_of_month=end_of_month)


def qfCreateProductRFRSwap(
    effective_date: str,
    term_or_termination_date: str,
    payment_off_set: str,
    on_index: str,
    fixed_rate: float,
    pay_or_rec: str,
    notional: float,
    accrual_period: str,
    accrual_basis: str,
    floating_leg_accrual_period: Optional[str] = "",
    pay_business_day_convention: Optional[str] = "F",
    pay_holiday_convention: Optional[str] = "USGS",
    spread: Optional[float] = 0.0,
    compounding_method: Optional[str] = "compound",
):

    if floating_leg_accrual_period == "":
        floating_leg_accrual_period = accrual_period

    return ProductRFRSwap(
        Date(effective_date),
        TermOrDate(term_or_termination_date),
        Period(payment_off_set),
        on_index,
        fixed_rate,
        PayOrReceive.from_string(pay_or_rec),
        notional,
        Period(accrual_period),
        AccrualBasis(accrual_basis),
        Period(floating_leg_accrual_period),
        BusinessDayConvention(pay_business_day_convention),
        HolidayConvention(pay_holiday_convention),
        spread,
        CompoundingMethod.from_string(compounding_method),
    )


def qfCreateProductOvernightIndexBasisSwap(
    effective_date: str,
    term_or_termination_date: str,
    payment_off_set: str,
    on_index_leg_1: str,
    on_index_leg_2: str,
    spread_over_leg_1: float,
    pay_or_rec_leg_1: str,
    notional: float,
    accrual_period_1: str,
    accrual_period_2: str,
    accrual_basis: str,
    pay_business_day_convention: Optional[str] = "F",
    pay_holiday_convention: Optional[str] = "USGS",
    compounding_method: Optional[str] = "compound",
):

    return ProductOvernightIndexBasisSwap(
        effective_date=Date(effective_date),
        term_or_termination_date=TermOrDate(term_or_termination_date),
        payment_off_set=Period(payment_off_set),
        on_index_1=on_index_leg_1,
        on_index_2=on_index_leg_2,
        spread_over_leg_1=spread_over_leg_1,
        pay_or_rec_leg_1=PayOrReceive.from_string(pay_or_rec_leg_1),
        notional=notional,
        accrual_period_1=Period(accrual_period_1),
        accrual_period_2=Period(accrual_period_2),
        accrual_basis=AccrualBasis(accrual_basis),
        pay_business_day_convention=BusinessDayConvention(pay_business_day_convention),
        pay_holiday_convention=HolidayConvention(pay_holiday_convention),
        compounding_method=CompoundingMethod.from_string(compounding_method),
    )

__all__ += ["qfCreateProductFromDataConvention", "qfCreateProductFRA",
            "qfCreateProductInterestRateStream", "qfCreateProductRFRSwap",
            "qfCreateProductOvernightIndexBasisSwap"]
