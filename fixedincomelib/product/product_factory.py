"""Convention-driven factory adapted from the instructor template.

Swap axis1 is tenor or start-offset x tenor. FRA uses start-offset x end-offset,
with both offsets measured from value_date, or two explicit ISO dates.
"""

from typing import Any
from fixedincomelib.date import Date, TermOrDate, add_period
from fixedincomelib.market.data_conventions import (
    CompoundingMethod, DataConvention, DataConventionFRA,
    DataConventionRFRSwap, DataConventionOvernightIndexBasisSwap,
)
from fixedincomelib.product.product_interfaces import ProductBuilderRegistry
from fixedincomelib.product.linear_products import ProductFRA, ProductRFRSwap, ProductOvernightIndexBasisSwap
from fixedincomelib.product.utilities import PayOrReceive


class ProductFactory:
    @classmethod
    def create_product_from_data_convention(
        cls,
        value_date: Date,
        axis1: str,
        data_convention: DataConvention,
        values: float,
        **kwargs: Any,
    ):

        convention_obj: DataConvention = data_convention
        prod_type = convention_obj.type()
        func = ProductBuilderRegistry().get(prod_type)
        return func(value_date, axis1, convention_obj, values, **kwargs)

    @classmethod
    def create_rfr_swap(
        cls,
        value_date: Date,
        axis1: str,
        data_convention: DataConventionRFRSwap,
        values: float,
        **kwargs: Any,
    ) -> ProductRFRSwap:

        term_or_effective_date, term_or_termination_date = ProductFactory._tokenize_axis1(axis1)

        pay_offset = data_convention.payment_offset
        on_index_str = data_convention.index_str
        on_index = data_convention.index
        accrual_period = data_convention.acc_period
        accrual_basis = data_convention.acc_basis
        pay_business_day_convention = data_convention.business_day_convention
        pay_holiday_convention = data_convention.holiday_convention
        pay_or_rec = kwargs.get("pay_or_rec", "receive")
        spread = kwargs.get("spread", 0.0)
        compounding_method = CompoundingMethod.from_string(
            kwargs.get("compounding_method", kwargs.get("compound_method", data_convention.compounding_method.to_string()))
        )

        effective_date = value_date
        if term_or_termination_date is None:
            # spot starting
            effective_date = on_index.valueDate(value_date)
            term_or_termination_date = term_or_effective_date
        else:
            # forward starting
            if term_or_effective_date.is_term():
                this_date = on_index.valueDate(value_date)
                effective_date = add_period(
                    this_date,
                    term_or_effective_date.get_term(),
                    on_index.businessDayConvention(),
                    pay_holiday_convention,
                )
            else:
                effective_date = term_or_effective_date.get_date()

        return ProductRFRSwap(
            effective_date=effective_date,
            term_or_termination_date=term_or_termination_date,
            payment_off_set=pay_offset,
            on_index=on_index_str,
            fixed_rate=values,
            pay_or_rec=PayOrReceive.from_string(pay_or_rec),
            notional=kwargs.get("notional", 1e4),
            accrual_period=accrual_period,
            accrual_basis=accrual_basis,
            floating_leg_accrual_period=accrual_period,
            pay_business_day_convention=pay_business_day_convention,
            pay_holiday_convention=pay_holiday_convention,
            spread=spread,
            compounding_method=compounding_method,
        )

    @classmethod
    def create_overnight_index_basis_swap(
        cls,
        value_date: Date,
        axis1: str,
        data_convention: DataConventionOvernightIndexBasisSwap,
        values: float,
        **kwargs: Any,
    ) -> ProductOvernightIndexBasisSwap:

        term_or_effective_date, term_or_termination_date = ProductFactory._tokenize_axis1(axis1)

        pay_offset = data_convention.payment_offset
        on_index_1_str = data_convention.index_1_str
        on_index_2_str = data_convention.index_2_str
        on_index_1 = data_convention.index_1
        on_index_2 = data_convention.index_2
        accrual_period_1 = data_convention.acc_period_1
        accrual_period_2 = data_convention.acc_period_2
        accrual_basis = data_convention.acc_basis
        pay_business_day_convention = data_convention.business_day_convention
        pay_holiday_convention = data_convention.holiday_convention
        pay_or_rec = kwargs.get("pay_or_rec", "receive")
        compounding_method = CompoundingMethod.from_string(
            kwargs.get("compounding_method", kwargs.get("compound_method", data_convention.compounding_method.to_string()))
        )

        effective_date = value_date
        if term_or_termination_date is None:
            # spot starting
            effective_date_1 = on_index_1.valueDate(value_date)
            effective_date_2 = on_index_2.valueDate(value_date)
            effective_date = effective_date_1
            term_or_termination_date = term_or_effective_date
        else:
            # forward starting
            if term_or_effective_date.is_term():
                this_date = on_index_1.valueDate(value_date)
                effective_date = add_period(
                    this_date,
                    term_or_effective_date.get_term(),
                    on_index_1.businessDayConvention(),
                    pay_holiday_convention,
                )
            else:
                effective_date = term_or_effective_date.get_date()

        return ProductOvernightIndexBasisSwap(
            effective_date=effective_date,
            term_or_termination_date=term_or_termination_date,
            payment_off_set=pay_offset,
            on_index_1=on_index_1_str,
            on_index_2=on_index_2_str,
            spread_over_leg_1=values,
            pay_or_rec_leg_1=PayOrReceive.from_string(pay_or_rec),
            notional=kwargs.get("notional", 1e4),
            accrual_period_1=accrual_period_1,
            accrual_basis=accrual_basis,
            accrual_period_2=accrual_period_2,
            pay_business_day_convention=pay_business_day_convention,
            pay_holiday_convention=pay_holiday_convention,
            compounding_method=compounding_method,
        )

    @classmethod
    def create_fra(cls, value_date, axis1, data_convention, values, **kwargs):
        start, end = cls._tokenize_axis1(axis1)
        bdc = data_convention.business_day_convention
        holidays = data_convention.holiday_convention
        if start.is_term():
            effective_date = add_period(value_date, start.get_term(), bdc, holidays)
            termination_date = add_period(value_date, end.get_term(), bdc, holidays)
        else:
            effective_date = start.get_date()
            termination_date = end.get_date()
        return ProductFRA(
            effective_date, TermOrDate(termination_date), data_convention.index_str,
            values, PayOrReceive.from_string(kwargs.get("pay_or_rec", "receive")),
            kwargs.get("notional", 1e4), data_convention.acc_basis, bdc, holidays,
        )

    @staticmethod
    def _tokenize_axis1(axis1):
        tokens = axis1.strip().replace("X", "x").split("x")
        first = TermOrDate(tokens[0].strip())
        second = TermOrDate(tokens[1].strip()) if len(tokens) == 2 else None
        return first, second


ProductBuilderRegistry().register(DataConventionFRA.type(), ProductFactory.create_fra)
ProductBuilderRegistry().register(DataConventionRFRSwap.type(), ProductFactory.create_rfr_swap)
ProductBuilderRegistry().register(DataConventionOvernightIndexBasisSwap.type(),
                                  ProductFactory.create_overnight_index_basis_swap)
