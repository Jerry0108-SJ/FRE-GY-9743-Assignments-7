"""Compounding labels and IFR data conventions from the course template."""

from abc import ABC
from enum import Enum

import pandas as pd
import QuantLib as ql

from fixedincomelib.market.basics import AccrualBasis, BusinessDayConvention, HolidayConvention
from fixedincomelib.date.basics import Period
from fixedincomelib.market.registries import DataConventionRegFunction, IndexRegistry

__all__ = ["CompoundingMethod", "DataConvention", "DataConventionIFR",
           "DataConventionFRA", "DataConventionRFRSwap", "DataConventionOvernightIndexBasisSwap"]


class CompoundingMethod(Enum):
    SIMPLE = "simple"
    ARITHMETIC = "arithmetic"
    COMPOUND = "compound"

    @classmethod
    def from_string(cls, value: str) -> "CompoundingMethod":
        return cls(value.lower())

    def to_string(self) -> str:
        return self.value


class DataConvention(ABC):

    _type = ""

    def __init__(self, unique_name: str, type: str, content: dict):
        super().__init__()
        self.conv_name = unique_name.upper()
        self.conv_type = type.upper()
        self.content = content

    @property
    def name(self):
        return self.conv_name

    @classmethod
    def type(cls):
        return cls._type

    def display(self):
        to_print = []
        for k, v in self.content.items():
            k_ = k
            if k_.endswith("_"):
                k_ = k[:-1]
            to_print.append([k_.upper(), v])
        return pd.DataFrame(to_print, columns=["Name", "Value"])


class DataConventionIFR(DataConvention):

    _type = "INSTANTANEOUS FORWARD RATE"

    def __init__(self, unique_name, content):


        self.index_ = None

        upper_content = {k.upper(): v for k, v in content.items()}
        for k, v in upper_content.items():
            if k.upper() == "INDEX":
                self.index_ = v
            elif k == "BUSINESS_DAY_CONVENTION":
                self.business_day_convention_ = v
            elif k == "HOLIDAY_CONVENTION":
                self.holiday_convention_ = v

        super().__init__(unique_name, DataConventionIFR._type, self.__dict__.copy())

    @property
    def index(self) -> ql.Index:
        return IndexRegistry().get(self.index_)

    @property
    def business_day_convention(self) -> BusinessDayConvention:
        return BusinessDayConvention(self.business_day_convention_)

    @property
    def holiday_convention(self) -> HolidayConvention:
        return HolidayConvention(self.holiday_convention_)


DataConventionRegFunction().register(DataConventionIFR._type, DataConventionIFR)


# Adapted from the instructor template; preserve convention names and accessors.
class DataConventionRFRSwap(DataConvention):

    _type = "RFR SWAP"

    def __init__(self, unique_name, content):


        self.index_ = None
        self.accrual_basis_ = None
        self.accrual_period_ = None
        self.payment_offset_ = None
        self.payment_business_day_convention_ = None
        self.payment_holiday_convention_ = None
        self.compounding_method_ = None

        upper_content = {k.upper(): v for k, v in content.items()}
        for k, v in upper_content.items():
            if k.upper() == "INDEX":
                self.index_ = v
            elif k == "ACCRUAL_BASIS":
                self.accrual_basis_ = v
            elif k == "ACCRUAL_PERIOD":
                self.accrual_period_ = v
            elif k == "PAYMENT_OFFSET":
                self.payment_offset_ = v
            elif k == "PAYMENT_BUSINESS_DAY_CONVENTION":
                self.payment_business_day_convention_ = v
            elif k == "PAYMENT_HOLIDAY_CONVENTION":
                self.payment_holiday_convention_ = v
            elif k == "COMPOUNDING_METHOD":
                self.compounding_method_ = v

        super().__init__(unique_name, DataConventionRFRSwap._type, self.__dict__.copy())

    @property
    def index(self) -> ql.QuantLib.OvernightIndex:
        return IndexRegistry().get(self.index_)

    @property
    def index_str(self) -> str:
        return self.index_

    @property
    def acc_basis(self) -> AccrualBasis:
        return AccrualBasis(self.accrual_basis_)

    @property
    def acc_period(self) -> Period:
        return Period(self.accrual_period_)

    @property
    def payment_offset(self) -> Period:
        return Period(self.payment_offset_)

    @property
    def business_day_convention(self) -> BusinessDayConvention:
        return BusinessDayConvention(self.payment_business_day_convention_)

    @property
    def holiday_convention(self) -> HolidayConvention:
        return HolidayConvention(self.payment_holiday_convention_)

    @property
    def compounding_method(self) -> CompoundingMethod:
        return CompoundingMethod.from_string(self.compounding_method_)

class DataConventionOvernightIndexBasisSwap(DataConvention):

    _type = "OVERNIGHT INDEX BASIS SWAP"

    def __init__(self, unique_name, content):


        self.index_1_ = None
        self.index_2_ = None
        self.accrual_basis_ = None
        self.accrual_period_1_ = None
        self.accrual_period_2_ = None
        self.payment_offset_ = None
        self.payment_business_day_convention_ = None
        self.payment_holiday_convention_ = None
        self.compounding_method_ = None

        upper_content = {k.upper(): v for k, v in content.items()}
        for k, v in upper_content.items():
            if k.upper() == "BASIS_OI_INDEX":
                self.index_1_ = v
            elif k.upper() == "REFERENCE_OI_INDEX":
                self.index_2_ = v
            elif k == "ACCRUAL_BASIS":
                self.accrual_basis_ = v
            elif k == "ACCRUAL_PERIOD_1":
                self.accrual_period_1_ = v
            elif k == "ACCRUAL_PERIOD_2":
                self.accrual_period_2_ = v
            elif k == "PAYMENT_OFFSET":
                self.payment_offset_ = v
            elif k == "PAYMENT_BUSINESS_DAY_CONVENTION":
                self.payment_business_day_convention_ = v
            elif k == "PAYMENT_HOLIDAY_CONVENTION":
                self.payment_holiday_convention_ = v
            elif k == "COMPOUNDING_METHOD":
                self.compounding_method_ = v

        super().__init__(unique_name, DataConventionOvernightIndexBasisSwap._type, self.__dict__.copy())

    @property
    def index_1(self) -> ql.QuantLib.OvernightIndex:
        return IndexRegistry().get(self.index_1_)

    @property
    def index_2(self) -> ql.QuantLib.OvernightIndex:
        return IndexRegistry().get(self.index_2_)

    @property
    def index_1_str(self) -> str:
        return self.index_1_

    @property
    def index_2_str(self) -> str:
        return self.index_2_

    @property
    def acc_basis(self) -> AccrualBasis:
        return AccrualBasis(self.accrual_basis_)

    @property
    def acc_period_1(self) -> Period:
        return Period(self.accrual_period_1_)

    @property
    def acc_period_2(self) -> Period:
        return Period(self.accrual_period_2_)

    @property
    def payment_offset(self) -> Period:
        return Period(self.payment_offset_)

    @property
    def business_day_convention(self) -> BusinessDayConvention:
        return BusinessDayConvention(self.payment_business_day_convention_)

    @property
    def holiday_convention(self) -> HolidayConvention:
        return HolidayConvention(self.payment_holiday_convention_)

    @property
    def compounding_method(self) -> CompoundingMethod:
        return CompoundingMethod.from_string(self.compounding_method_)


class DataConventionFRA(DataConvention):
    """Teaching FRA: fix at Ts, pay at Te; index identifies the projection curve."""

    _type = "FRA"

    def __init__(self, unique_name, content):
        fields = {k.upper(): v for k, v in content.items()}
        self.index_ = fields["INDEX"]
        self.accrual_basis_ = fields["ACCRUAL_BASIS"]
        self.business_day_convention_ = fields["BUSINESS_DAY_CONVENTION"]
        self.holiday_convention_ = fields["HOLIDAY_CONVENTION"]
        super().__init__(unique_name, self._type, fields)

    @property
    def index(self):
        return IndexRegistry().get(self.index_)

    @property
    def index_str(self):
        return self.index_

    @property
    def acc_basis(self):
        return AccrualBasis(self.accrual_basis_)

    @property
    def business_day_convention(self):
        return BusinessDayConvention(self.business_day_convention_)

    @property
    def holiday_convention(self):
        return HolidayConvention(self.holiday_convention_)

    @property
    def fixing_offset(self):
        return Period("0D")

    @property
    def payment_offset(self):
        return Period("0D")


for _convention in (DataConventionFRA, DataConventionRFRSwap, DataConventionOvernightIndexBasisSwap):
    DataConventionRegFunction().register(_convention.type(), _convention)
