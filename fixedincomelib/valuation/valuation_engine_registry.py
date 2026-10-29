"""Dispatch by model type, product type and valuation parameter type."""

from fixedincomelib.utilities import Registry
from fixedincomelib.valuation.valuation_parameters import AnalyticValParam


class ValuationEngineProductRegistry(Registry):
    def __new__(cls):
        return super().__new__(cls, "", cls.__name__)

    def register(self, key, value) -> None:
        self._map[key] = value

    def get(self, key, **kwargs):
        # Unlike string registries, engine keys are tuples.
        return self._map[key]

    @classmethod
    def new_valuation_engine(cls, model, product, valuation_parameters_collection, valuation_request):
        key = (model.model_type, product.product_type, AnalyticValParam._vp_type)
        engine_cls = cls().get(key)
        return engine_cls(model, valuation_parameters_collection, product, valuation_request)
