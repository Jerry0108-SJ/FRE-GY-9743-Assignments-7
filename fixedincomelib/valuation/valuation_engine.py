"""Minimal product engine contract for PV and raw first-order state risk."""

from abc import ABC, abstractmethod
from enum import Enum

import numpy as np

from fixedincomelib.valuation.report import PVCashReport


class ValuationRequest(Enum):
    PV = "pv"
    FIRST_ORDER_RISK = "firstorderrisk"

    @classmethod
    def from_string(cls, value: str):
        return cls(value.lower())

    def to_string(self) -> str:
        return self.value


class ValuationEngineProduct(ABC):
    def __init__(self, model, valuation_parameters_collection, product, request: ValuationRequest):
        self.model_ = model
        self.valuation_parameters_collection_ = valuation_parameters_collection
        self.product_ = product
        self.request_ = request
        self.value_ = 0.0
        self.cash_ = 0.0

    @property
    def model(self):
        return self.model_

    @property
    def value_date(self):
        return self.model.value_date

    @property
    def value(self) -> float:
        return self.value_

    @property
    def cash(self) -> float:
        return self.cash_

    @abstractmethod
    def calculate_value(self) -> None:
        pass

    def calculate_risk(self, gradient: list[np.ndarray], scaler=1.0, accumulate=False) -> None:
        raise NotImplementedError("Risk is not implemented for this product.")

    def calculate_first_order_risk(self, gradient: list[np.ndarray], scaler=1.0, accumulate=False) -> None:
        """Template-compatible entry point; the implementation lives in calculate_risk."""
        self.calculate_risk(gradient, scaler=scaler, accumulate=accumulate)

    def get_value_and_cash(self) -> PVCashReport:
        report = PVCashReport(self.product_.currency)
        report.set_pv(self.product_.currency, self.value)
        report.set_cash(self.product_.currency, self.cash)
        return report

    @classmethod
    def val_engine_type(cls) -> str:
        return cls.__name__
