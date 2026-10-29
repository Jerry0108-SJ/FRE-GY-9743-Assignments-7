"""Base interfaces for products and visitors."""

from abc import ABC, abstractmethod

from fixedincomelib.date.basics import Date
from fixedincomelib.market.basics import Currency
from fixedincomelib.product.utilities import LongOrShort
from fixedincomelib.utilities.utils import Registry

__all__ = ["Product", "ProductVisitor", "ProductBuilderRegistry"]


class ProductBuilderRegistry(Registry):
    """Template dispatch: convention types create products; TYPE_DES restores them."""

    def __new__(cls):
        return super().__new__(cls, "", cls.__name__)

    def register(self, key, value) -> None:
        self._map[key.upper()] = value


class ProductVisitor(ABC):
    """Marker base for operations implemented outside the product classes."""


class Product(ABC):
    _version = -1
    _product_type = ""

    def __init__(self) -> None:
        self.first_date_ = None
        self.last_date_ = None
        self.notional_ = None
        self.long_or_short_ = None
        self.currency_ = None

    @abstractmethod
    def accept(self, visitor: ProductVisitor):
        """Dispatch an external operation to this product's visitor handler."""

    @abstractmethod
    def serialize(self) -> dict:
        """Return the product's contractual fields as a dictionary."""

    @classmethod
    @abstractmethod
    def deserialize(cls, input_dict: dict) -> "Product":
        """Rebuild a product from its contractual fields."""

    @property
    def product_type(self) -> str:
        return self._product_type

    @property
    def first_date(self) -> Date:
        return self.first_date_

    @property
    def last_date(self) -> Date:
        return self.last_date_

    @property
    def notional(self) -> float:
        return self.notional_

    @property
    def long_or_short(self) -> LongOrShort:
        return self.long_or_short_

    @property
    def currency(self) -> Currency:
        return self.currency_
