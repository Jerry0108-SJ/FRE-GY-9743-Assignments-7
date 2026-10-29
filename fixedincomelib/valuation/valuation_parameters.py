"""The template's analytic/funding parameters, assuming valid inputs."""

from abc import ABC, abstractmethod

import pandas as pd

from fixedincomelib.market.basics import Currency
from fixedincomelib.market.registries import FundingIdentifierRegistry
from fixedincomelib.utilities import Registry


class ValuationParametersBuilderRegistry(Registry):
    def __new__(cls):
        return super().__new__(cls, "", cls.__name__)

    def register(self, key, value) -> None:
        self._map[key.upper()] = value


class ValuationParameters(ABC):
    _vp_type = ""

    def __init__(self, content: list | dict) -> None:
        pairs = content.items() if isinstance(content, dict) else content
        self.vp_dict_ = {key.upper(): value for key, value in pairs}
        for key in self.get_valid_keys():
            self.vp_dict_.setdefault(key, "")

    @abstractmethod
    def get_valid_keys(self) -> set:
        pass

    def __getitem__(self, key: str):
        return self.vp_dict_[key.upper()]

    @property
    def vp_type(self) -> str:
        return self._vp_type

    @property
    def content(self) -> dict:
        return self.vp_dict_

    def display(self) -> pd.DataFrame:
        return pd.DataFrame(self.content.items(), columns=["Name", "Value"])


class AnalyticValParam(ValuationParameters):
    _vp_type = "ANALYTIC PARAMETER"

    def get_valid_keys(self) -> set:
        return {"ANALYTIC"}


class FundingIndexParameter(ValuationParameters):
    """Select one funding identifier, or a semicolon-separated currency map.

    Currency mappings and funding choices are assumed correct. Underlying
    funding and FX conversion are outside this assignment.
    """

    _vp_type = "FUNDING INDEX PARAMETER"

    def __init__(self, content: list | dict) -> None:
        super().__init__(content)
        single = self["FUNDING INDEX"].strip()
        registry = FundingIdentifierRegistry()
        self.funding_identifier_ = None
        self.funding_identifiers_map_ = {}
        if single:
            self.funding_identifier_ = registry.get(single)
        else:
            currencies = self["CURRENCIES"].split(";")
            identifiers = self["FUNDING INDICES"].split(";")
            self.funding_identifiers_map_ = {
                code.strip().upper(): registry.get(name.strip())
                for code, name in zip(currencies, identifiers)
            }

    def get_valid_keys(self) -> set:
        return {"FUNDING INDEX", "CURRENCIES", "FUNDING INDICES"}

    def get_funding_index(self, currency: Currency | None = None):
        if self.funding_identifier_ is not None:
            return self.funding_identifier_
        return self.funding_identifiers_map_[currency.code()]


class ValuationParametersCollection:
    def __init__(self, vp_list: list[ValuationParameters]) -> None:
        self.vp_col_ = {parameter.vp_type: parameter for parameter in vp_list}
        self.vp_col_.setdefault(AnalyticValParam._vp_type, AnalyticValParam({}))

    @property
    def num_vp(self) -> int:
        return len(self.vp_col_)

    @property
    def items(self):
        return self.vp_col_.items()

    def has_vp_type(self, vp_type: str) -> bool:
        return vp_type.upper() in self.vp_col_

    def get_vp_from_build_method_collection(self, vp_type: str) -> ValuationParameters:
        """Retain the template's accessor spelling for compatibility."""
        return self.vp_col_[vp_type.upper()]


ValuationParametersBuilderRegistry().register(AnalyticValParam._vp_type, AnalyticValParam)
ValuationParametersBuilderRegistry().register(FundingIndexParameter._vp_type, FundingIndexParameter)
