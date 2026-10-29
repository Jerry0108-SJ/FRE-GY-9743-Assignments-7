"""Collect product attributes for display using a visitor."""

from functools import singledispatchmethod

import pandas as pd

from fixedincomelib.product.product_interfaces import Product, ProductVisitor
from fixedincomelib.product.linear_products import (
    ProductFixedAccruedCashflow, ProductOvernightIndexCashflow,
    ProductForwardRateCashflow, ProductInterestRateStream, ProductFRA,
    ProductRFRSwap, ProductOvernightIndexBasisSwap,
)

__all__ = ["ProductDisplayVisitor"]


class ProductDisplayVisitor(ProductVisitor):
    def __init__(self) -> None:
        self.nvps_ = []

    @singledispatchmethod
    def visit(self, product: Product):
        raise NotImplementedError(f"No display visitor for {product.product_type}")

    def display(self) -> pd.DataFrame:
        return pd.DataFrame(self.nvps_, columns=["Name", "Value"])

    def _common_items(self, product: Product):
        self.nvps_ = [
            ["Product Type", product.product_type],
            ["Notional", product.notional],
            ["Currency", product.currency.value_str],
            ["Long Or Short", product.long_or_short.to_string().upper()],
        ]

    @visit.register
    def _(self, product: ProductFixedAccruedCashflow):
        self._common_items(product)
        self.nvps_.append(["Effective Date", product.effective_date.ISO()])
        self.nvps_.append(["Termination Date", product.termination_date.ISO()])
        self.nvps_.append(["Accrual Basis", product.accrual_basis.value_str])
        self.nvps_.append(["Payment Date", product.payment_date.ISO()])
        self.nvps_.append(["Business Day Convention", product.business_day_convention.value_str])
        self.nvps_.append(["Holiday Convention", product.holiday_convention.value_str])

    @visit.register
    def _(self, product: ProductForwardRateCashflow):
        self._common_items(product)
        self.nvps_ += [["Effective Date", product.effective_date.ISO()],
                      ["Termination Date", product.termination_date.ISO()],
                      ["Fixing Date", product.fixing_date.ISO()],
                      ["Payment Date", product.payment_date.ISO()],
                      ["Projection Index", product.projection_index_str_],
                      ["Accrual Basis", product.accrual_basis.value_str]]

    @visit.register
    def _(self, product: ProductInterestRateStream):
        self._common_items(product)
        self.nvps_ += [["Effective Date", product.effective_date.ISO()],
                      ["Termination Date", product.termination_date.ISO()],
                      ["Last Payment Date", product.last_date.ISO()],
                      ["Number of Cashflows", product.num_cashflows()],
                      ["Fixed Rate", product.fixed_rate], ["Floating Index", product.float_index],
                      ["Overnight Index", product.is_on_index_ if product.float_index else None]]

    @visit.register
    def _(self, product: ProductFRA):
        self._common_items(product)
        self.nvps_ += [["Effective Date", product.effective_date.ISO()],
                      ["Termination Date", product.termination_date.ISO()],
                      ["Fixing Date", product.fixing_date.ISO()],
                      ["Payment Date", product.payment_date.ISO()],
                      ["Projection Index", product.projection_index_str_],
                      ["Fixed Rate", product.fixed_rate],
                      ["Pay Or Receive Fixed", product.pay_or_rec.to_string().upper()],
                      ["Accrual Basis", product.accrual_basis.value_str]]

    @visit.register
    def _(self, product: ProductRFRSwap):
        self._common_items(product)
        self.nvps_ += [["Effective Date", product.effective_date.ISO()],
                      ["Termination Date", product.termination_date.ISO()],
                      ["Last Payment Date", product.last_date.ISO()],
                      ["ON Index", product.on_index_str_], ["Fixed Rate", product.fixed_rate],
                      ["Spread", product.spread], ["Pay Or Receive Fixed", product.pay_or_rec.to_string().upper()],
                      ["Fixed Accrual Period", str(product.accrual_period)],
                      ["Floating Accrual Period", str(product.floating_leg_accrual_period)],
                      ["Compounding Method", product.compounding_method.to_string().upper()]]

    @visit.register
    def _(self, product: ProductOvernightIndexBasisSwap):
        self._common_items(product)
        self.nvps_ += [["Effective Date", product.effective_date.ISO()],
                      ["Termination Date", product.termination_date.ISO()],
                      ["Last Payment Date", product.last_date.ISO()],
                      ["ON Index Leg 1", product.on_index_str_1_],
                      ["ON Index Leg 2", product.on_index_str_2_],
                      ["Spread Over Leg 1", product.spread],
                      ["Pay Or Receive Leg 1", product.pay_or_rec.to_string().upper()],
                      ["Accrual Period Leg 1", str(product.accrual_period_leg_1)],
                      ["Accrual Period Leg 2", str(product.accrual_period_leg_2)],
                      ["Compounding Method", product.compounding_method.to_string().upper()]]
    @visit.register
    def _(self, product: ProductOvernightIndexCashflow):
        self._common_items(product)
        self.nvps_.append(["Effective Date", product.effective_date.ISO()])
        self.nvps_.append(["Termination Date", product.termination_date.ISO()])
        self.nvps_.append(["ON Index", product.on_index.name()])
        self.nvps_.append(["Compounding Method", product.compounding_method.to_string().upper()])
        self.nvps_.append(["Spread", product.spread])
        self.nvps_.append(["Payment Date", product.payment_date.ISO()])
