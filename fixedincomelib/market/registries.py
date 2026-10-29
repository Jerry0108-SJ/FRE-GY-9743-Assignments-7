"""Look up indices, funding identifiers and market data conventions."""

from typing import Any, Self, Optional

import pandas as pd
import QuantLib as ql

from fixedincomelib.utilities.utils import Registry
from fixedincomelib.market.basics import Currency
from fixedincomelib.date.basics import Date

__all__ = [
    "IndexRegistry",
    "DataConventionRegFunction",
    "DataConventionRegistry",
    "DataIdentifierRegistry",
    "FundingIdentifier",
    "FundingIdentifierRegistry",
    "IndexFixingsManager",
]


class IndexRegistry:
    _constructors = {
        "SOFR-1B": ql.Sofr,
        "FF-1B": ql.FedFunds,
        "SONIA-1B": ql.Sonia,
    }

    def get(self, key: str) -> ql.OvernightIndex:
        return self._constructors[key.upper()]()

    @classmethod
    def look_up_index_name(cls, index: ql.Index) -> str:
        names = {constructor().name(): alias for alias, constructor in cls._constructors.items()}
        return names[index.name()]


class IndexFixingsManager:
    """Store daily overnight fixings and whole-period term fixings separately."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.daily_ = {}
            cls._instance.term_ = {}
        return cls._instance

    @staticmethod
    def _index_key(index):
        obj = IndexRegistry().get(index) if isinstance(index, str) else index
        return IndexRegistry.look_up_index_name(obj)

    @classmethod
    def _term_key(cls, index, start, end, accrual_basis):
        basis = getattr(accrual_basis, "value", accrual_basis)
        return (cls._index_key(index), Date(start).ISO(), Date(end).ISO(), basis.name())


    def insert_fixing(self, index, date, fixing):
        self.daily_[(self._index_key(index), Date(date).ISO())] = float(fixing)

    def exist_fixing(self, index, date):
        return (self._index_key(index), Date(date).ISO()) in self.daily_

    def get_fixing(self, index, date):
        key = (self._index_key(index), Date(date).ISO())
        return self.daily_[key]

    def insert_term_fixing(self, index, start, end, accrual_basis, fixing):
        self.term_[self._term_key(index, start, end, accrual_basis)] = float(fixing)

    def get_term_fixing(self, index, start, end, accrual_basis):
        key = self._term_key(index, start, end, accrual_basis)
        return self.term_[key]

    def clear(self):
        self.daily_.clear()
        self.term_.clear()


class DataConventionRegFunction(Registry):

    def __new__(cls) -> Self:
        return super().__new__(cls, "", cls.__name__)

    def register(self, key: Any, value: Any) -> None:
        super().register(key, value)
        self._map[key] = value


class DataConventionRegistry(Registry):

    def __new__(cls) -> Self:
        return super().__new__(cls, "data_conventions", "DataConevention")

    def register(self, key: Any, value: Any) -> None:
        value_ = value.copy()
        super().register(key, value_)
        type = value_["type"]
        value_.pop("type")
        func = DataConventionRegFunction().get(type)
        self._map[key] = func(key, value_)

    def display_all_data_conventions(self) -> pd.DataFrame:
        to_print = []
        for k, v in self._map.items():
            to_print.append([k, v.type()])
        return pd.DataFrame(to_print, columns=["Name", "Type"])


class DataIdentifierRegistry(Registry):

    def __new__(cls) -> Self:
        return super().__new__(cls, "", cls.__name__)

    def register(self, key: Any, value: Any) -> None:
        super().register(key, value)
        self._map[key] = value


class FundingIdentifier(ql.Index):

    def __init__(self, unique_name: str, currency: str, reference_index: Optional[str] = ""):
        self.name_ = unique_name
        self.currency_ = Currency(currency)
        self.reference_index_ = None
        if reference_index != "":
            self.reference_index_ = IndexRegistry().get(reference_index)

    def name(self):
        return self.name_

    def currency(self) -> Currency:
        return self.currency_

    @property
    def reference_index(self) -> ql.Index:
        return self.reference_index_


class FundingIdentifierRegistry(Registry):

    def __new__(cls) -> Self:
        return super().__new__(cls, "fundingidentifiers", "FundingIdentifier")

    def register(self, key: Any, value: Any) -> None:
        super().register(key, value)
        reference_index = value.get("Reference Index", "")
        self._map[key.upper()] = FundingIdentifier(key.upper(), value["Currency"], reference_index)

    def get(self, key: Any, **args) -> Any:
        return self._map[key.upper()]

    def display_all_indices(self) -> pd.DataFrame:
        to_print = []
        for k, _ in self._map.items():
            fi: FundingIdentifier = self.get(k)
            to_print.append([k, fi.name()])
        return pd.DataFrame(to_print, columns=["Name", "fundingIdentifier"])
