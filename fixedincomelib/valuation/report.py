"""PV/cash reports and IFR risk with basis-point scaling only on display."""

import pandas as pd

from fixedincomelib.market.basics import Currency


class PVCashReport:
    def __init__(self, currencies: Currency | list[Currency]) -> None:
        self.currencies_ = list(dict.fromkeys(currencies if isinstance(currencies, list) else [currencies]))
        self.pv_ = dict.fromkeys(self.currencies_, 0.0)
        self.cash_ = dict.fromkeys(self.currencies_, 0.0)

    def set_pv(self, currency: Currency, value: float) -> None:
        self.pv_[currency] = value

    def set_cash(self, currency: Currency, value: float) -> None:
        self.cash_[currency] = value

    @property
    def pv(self) -> list:
        """Total value, including any cash payable on the value date."""
        return [[currency.code(), self.pv_[currency]] for currency in self.currencies_]

    @property
    def cash(self) -> list:
        return [[currency.code(), self.cash_[currency]] for currency in self.currencies_]

    def display(self) -> pd.DataFrame:
        rows = []
        for currency in self.currencies_:
            rows.extend([
                [currency.code(), "PV", self.pv_[currency] - self.cash_[currency]],
                [currency.code(), "CASH", self.cash_[currency]],
            ])
        return pd.DataFrame(rows, columns=["Currency", "Type", "Value"])


class RiskReport:
    """Snapshot of raw IFR derivatives, with the template's seven data columns.

    COMPONENT and NODE_INDEX identify each row explicitly. ``state_gradient``
    retains the original block structure; ``display`` applies UNIT exactly
    once to a fresh DataFrame and never alters ``content``.
    """

    def __init__(self, content: list, state_gradient: list) -> None:
        self.content_ = [list(row) for row in content]
        self.state_gradient_ = [block.copy() for block in state_gradient]
        self.schema_ = [
            "DATA_TYPE", "DATA_CONVENTION", "AXIS1", "AXIS2", "MARKET_QUOTE",
            "UNIT", "VALUES", "COMPONENT", "NODE_INDEX",
        ]

    @classmethod
    def from_model_gradient(cls, model, gradient: list):
        rows = []
        for name, position in model.component_indices.items():
            component = model.retrieve_model_component(name)
            for node, metadata in enumerate(component.market_data):
                # Direct IFR inputs are the state variables. No calibration
                # Jacobian is needed; use the current state after any bumps.
                rows.append([
                    *metadata[:4], float(component.state_data[1][node]),
                    float(metadata[5]), float(gradient[position][node]), name, node,
                ])
        return cls(rows, gradient)

    @property
    def content(self) -> list:
        return self.content_

    @property
    def schema(self) -> list:
        return self.schema_

    @property
    def state_gradient(self) -> list:
        return self.state_gradient_

    def display(self) -> pd.DataFrame:
        frame = pd.DataFrame(self.content, columns=self.schema)
        frame["VALUES"] = frame["VALUES"] * frame["UNIT"]
        return frame


class CashflowsReport:
    """Snapshot of scheduled cashflows; composite-leg amounts carry their signs."""

    def __init__(self, content):
        self.content = [dict(row) for row in content]

    def display(self):
        return pd.DataFrame(self.content)
