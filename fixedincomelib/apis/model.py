"""Create IFR yield-curve models and query their discount factors."""

from typing import Optional

from fixedincomelib.date import Date
from fixedincomelib.data import DataCollection
from fixedincomelib.market.registries import FundingIdentifierRegistry, IndexRegistry
from fixedincomelib.model import Model, ModelType, BuildMethodCollection
from fixedincomelib.yield_curve.model_builder import YieldCurveBuilder
from fixedincomelib.yield_curve.yield_curve_model import YieldCurve

__all__ = ["qfCreateModel", "qfDiscountFactor"]


def qfCreateModel(
    value_date: str,
    model_type: str,
    data_collection: DataCollection,
    build_method_collection: BuildMethodCollection,
):

    model_type_enum = ModelType.from_string(model_type)
    if model_type_enum == ModelType.YIELD_CURVE:
        return YieldCurveBuilder.create_model_yield_curve(
            Date(value_date), data_collection, build_method_collection
        )
    else:
        raise Exception("Currently only support model type yield curve.")


def qfDiscountFactor(
    model: Model,
    index: str,
    expiry_date: str,
    payment_currency: Optional[str] = None,
):

    if not isinstance(model, YieldCurve):
        raise TypeError("model must be a YieldCurve")
    if not isinstance(index, str):
        raise TypeError("Index name must be a string")

    # Registry.exists checks exact keys; normalize before choosing a registry.
    index = index.upper()
    if FundingIdentifierRegistry().exists(index):
        index_obj = FundingIdentifierRegistry().get(index)
    else:
        index_obj = IndexRegistry().get(index)
    return model.discount_factor(index_obj, Date(expiry_date), payment_currency)
