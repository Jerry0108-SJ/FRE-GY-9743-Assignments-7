"""One-dimensional data supplied by callers, using the course template."""

from typing import Sequence
import pandas as pd

from fixedincomelib.market import DataConvention, DataConventionRegistry
from fixedincomelib.data.basics import DataObject, DataObjectDeserializerRegistry

__all__ = ["Data1D"]


class Data1D(DataObject):

    _version = 1
    _data_shape = 'DATA1D'

    def __init__(
        self,
        data_type: str,
        data_convention: DataConvention,
        axis1: Sequence[str],
        values: Sequence[float]
    ):
        super().__init__(data_type, data_convention)
        if len(axis1) != len(values):
            raise ValueError("`axis1` and `values` must be the same length")
        self.axis1_ = list(axis1)
        self.values_ = list(values)

    @property
    def data_shape(self):
        return self._data_shape

    @property
    def axis1(self):
        return self.axis1_

    @property
    def values(self):
        return self.values_

    def display(self) -> pd.DataFrame:
        df = pd.DataFrame(columns=['axis1', 'values'])
        df['axis1'] = self.axis1
        df['values'] = self.values
        return df

    def serialize(self) -> dict:
        content = {}
        content['VERSION'] = self._version
        content['DATA_SHAPE'] = self.data_shape
        content['DATA_TYPE'] = self.data_type
        content['DATA_CONVENTION'] = self.data_convention.name
        content['AXIS1'] = self.axis1
        content['VALUES'] = self.values
        return content
        
    @classmethod
    def deserialize(cls, input_dict : dict) -> "DataObject":
        assert 'VERSION' in input_dict
        version = input_dict['VERSION']
        assert 'DATA_TYPE' in input_dict
        data_type = input_dict['DATA_TYPE']
        assert 'DATA_CONVENTION' in input_dict
        data_conv = DataConventionRegistry().get(input_dict['DATA_CONVENTION'])
        assert 'AXIS1' in input_dict
        axis1 = input_dict['AXIS1']
        assert 'VALUES' in input_dict
        values = input_dict['VALUES']
        return cls(data_type, data_conv, axis1, values)


DataObjectDeserializerRegistry().register(Data1D._data_shape, Data1D.deserialize)
