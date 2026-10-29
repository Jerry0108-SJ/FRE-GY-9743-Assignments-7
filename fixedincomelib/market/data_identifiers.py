"""Data identifiers for IFR inputs, taken from the course template."""

from typing import Tuple
from abc import ABC, abstractmethod

from fixedincomelib.market.data_conventions import DataConvention, DataConventionIFR
from fixedincomelib.market.registries import DataIdentifierRegistry

__all__ = ["DataIdentifier", "DataIdentifierIFR"]


class DataIdentifier(ABC):

    _data_type = ''

    def __init__(self, data_convention : DataConvention|str) -> None:
        self.data_convention_ = data_convention
        self.data_identifier_ = (self._data_type, data_convention if isinstance(data_convention, str) else data_convention.name)
    
    @property
    def data_type(self) -> str:
        return self._data_type
    
    @property
    def data_convention(self) -> DataConvention|str:
        return self.data_convention_
    
    @property
    def data_identifier(self) -> Tuple[str, str]:
        return self.data_identifier_

    def to_string(self):
        name =  self.data_convention if isinstance(self.data_convention, str) else self.data_convention.name
        return f'{self.data_type}:{name}'
    
    @abstractmethod
    def unit(self):
        pass


class DataIdentifierIFR(DataIdentifier):

    _data_type = 'Instantaneous Forward Rate'

    def __init__(self, data_convention: DataConventionIFR) -> None:
        super().__init__(data_convention)

    def unit(self):
        return 0.0001


DataIdentifierRegistry().register(DataIdentifierIFR._data_type.upper(), DataIdentifierIFR)
