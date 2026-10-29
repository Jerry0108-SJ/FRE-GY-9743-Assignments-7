"""IFR curve build methods adapted from the course template.

This assignment accepts IFR data for both projection and funding components.
The template's calibration_instruments name is retained for its accepted-data keys.
"""

from typing import Union, List
import QuantLib as ql

from fixedincomelib.market.data_conventions import DataConventionIFR
from fixedincomelib.market.registries import (
    DataConventionRegistry, FundingIdentifier, FundingIdentifierRegistry, IndexRegistry,
)
from fixedincomelib.model import BuildMethod, BuildMethodBuilderRregistry
from fixedincomelib.utilities.numerics import ExtrapMethod, InterpMethod

__all__ = ["YieldCurveIndexBuildMethod", "YieldCurveFundingBuildMethod"]


class YieldCurveIndexBuildMethod(BuildMethod):

    _version = 1
    _build_method_type = 'YIELD_CURVE_INDEX'

    def __init__(self, 
                 target : str,
                 content : Union[List, dict]):

        super().__init__(target, 'YIELD_CURVE_INDEX', content)
        if self.bm_dict['INTERPOLATION METHOD'] == '':
            self.bm_dict['INTERPOLATION METHOD'] = 'PIECEWISE_CONSTANT_LEFT_CONTINUOUS'
        if self.bm_dict['EXTRAPOLATION METHOD'] == '':
            self.bm_dict['EXTRAPOLATION METHOD'] = 'FLAT'
        self.target_index_ = IndexRegistry().get(self.target)

    def calibration_instruments(self) -> set:
        return {'INSTANTANEOUS FORWARD RATE'}

    def additional_entries(self) -> set:
        return {'REFERENCE INDEX', 'INTERPOLATION METHOD', 'EXTRAPOLATION METHOD'}

    @property
    def target_index(self) -> ql.Index:
        return self.target_index_

    @property
    def reference_index(self):
        if 'REFERENCE INDEX' not in self.bm_dict:
            return None
        return self.bm_dict['REFERENCE INDEX']

    @property
    def instantaneous_forward_rate(self) -> DataConventionIFR:
        if self['INSTANTANEOUS FORWARD RATE'] == '':
            return None
        return DataConventionRegistry().get(self['INSTANTANEOUS FORWARD RATE'])

    @property
    def interpolation_method(self) -> InterpMethod:
        return InterpMethod.from_string(self['INTERPOLATION METHOD'])

    @property
    def extrapolation_method(self) -> ExtrapMethod:
        return ExtrapMethod.from_string(self['EXTRAPOLATION METHOD'])


class YieldCurveFundingBuildMethod(BuildMethod):

    _version = 1
    _build_method_type = 'YIELD_CURVE_FUNDING'

    def __init__(self, 
                 target : str,
                 content : Union[List, dict]):

        super().__init__(target, 'YIELD_CURVE_FUNDING', content)
        if self.bm_dict['INTERPOLATION METHOD'] == '':
            self.bm_dict['INTERPOLATION METHOD'] = 'PIECEWISE_CONSTANT_LEFT_CONTINUOUS'
        if self.bm_dict['EXTRAPOLATION METHOD'] == '':
            self.bm_dict['EXTRAPOLATION METHOD'] = 'FLAT'
        self.target_index_ = FundingIdentifierRegistry().get(self.target)

    def calibration_instruments(self) -> set:
        return {'INSTANTANEOUS FORWARD RATE'}

    def additional_entries(self) -> set:
        return {'REFERENCE INDEX', 'INTERPOLATION METHOD', 'EXTRAPOLATION METHOD'}

    @property
    def target_index(self) -> FundingIdentifier:
        return self.target_index_

    @property
    def reference_index(self):
        if 'REFERENCE INDEX' not in self.bm_dict:
            return None
        return self.bm_dict['REFERENCE INDEX']

    @property
    def instantaneous_forward_rate(self) -> DataConventionIFR:
        if self['INSTANTANEOUS FORWARD RATE'] == '':
            return None
        return DataConventionRegistry().get(self['INSTANTANEOUS FORWARD RATE'])

    @property
    def interpolation_method(self) -> InterpMethod:
        return InterpMethod.from_string(self['INTERPOLATION METHOD'])

    @property
    def extrapolation_method(self) -> ExtrapMethod:
        return ExtrapMethod.from_string(self['EXTRAPOLATION METHOD'])


### register
BuildMethodBuilderRregistry().register(YieldCurveIndexBuildMethod._build_method_type, YieldCurveIndexBuildMethod)
BuildMethodBuilderRregistry().register(f'{YieldCurveIndexBuildMethod._build_method_type}_DES', YieldCurveIndexBuildMethod.deserialize)
BuildMethodBuilderRregistry().register(YieldCurveFundingBuildMethod._build_method_type, YieldCurveFundingBuildMethod)
BuildMethodBuilderRregistry().register(f'{YieldCurveFundingBuildMethod._build_method_type}_DES', YieldCurveFundingBuildMethod.deserialize)
