"""Model and component infrastructure adapted from the course template.

This stage provides model setup; instrument-calibration risk interfaces are
outside the IFR-only construction path.
"""

import numpy as np
import QuantLib as ql
from enum import Enum
from typing import Any, Dict, Optional, List, Self
from abc import ABCMeta, abstractclassmethod, abstractmethod

from fixedincomelib.date import Date
from fixedincomelib.data import DataCollection
from fixedincomelib.market.registries import FundingIdentifierRegistry, IndexRegistry
from fixedincomelib.product import Product
from fixedincomelib.utilities import Registry
from fixedincomelib.model.build_method import BuildMethod, BuildMethodCollection

__all__ = [
    "ModelDeserializerRegistry", "ModelBuilderRegistry", "ModelType", "ModelComponent", "Model",
]


class ModelDeserializerRegistry(Registry):
    
    def __new__(cls) -> Self:
        return super().__new__(cls, '', cls.__name__)

    def register(self, key : Any, value : Any) -> None:
        super().register(key, value)
        self._map[key] = value


class ModelBuilderRegistry(Registry):
    
    def __new__(cls) -> Self:
        return super().__new__(cls, '', cls.__name__)

    def register(self, key : Any, value : Any) -> None:
        super().register(key, value)
        self._map[key] = value


class ModelType(Enum):
    
    YIELD_CURVE = 'YIELD_CURVE'
    IR_SABR = 'IR_SABR'

    @classmethod
    def from_string(cls, value: str) -> 'ModelType':
        if not isinstance(value, str):
            raise TypeError("value must be a string")
        try:
            return cls(value.upper())
        except ValueError:
            raise ValueError(f"Invalid token: {value}")

    def to_string(self) -> str:
        return self.value


class ModelComponent:

    def __init__(self, 
                 value_date : Date,
                 component_identifier : ql.Index,
                 state_data : Any,
                 build_method : BuildMethod,
                 calibration_product : List[Product],
                 calibration_funding : List[str],
                 market_data : List) -> None:
        
        self.value_date_ = value_date
        self.component_identifier_ = component_identifier
        self.calibration_product_ = calibration_product
        self.calibration_funding_ = calibration_funding
        self.build_method_ = build_method
        self.state_data_ = state_data
        self.num_state_data_ = -1
        self.market_data_ = market_data

    def perturb_model_parameter(self, parameter_id : int, perturb_size : float, override_parameter : Optional[bool]=False):
        if override_parameter:
            self.state_data[1][parameter_id] = perturb_size
        else:
            self.state_data[1][parameter_id] += perturb_size

    @property
    def value_date(self) -> Date:
        return self.value_date_

    @property
    def component_identifier(self) -> ql.IborIndex | ql.OvernightIndex:
        return self.component_identifier_

    @property
    def calibration_product(self) -> List[Product]:
        return self.calibration_product_
    
    @property
    def calibration_funding(self) -> List[str]:
        return self.calibration_funding_

    @property
    def build_method(self) -> BuildMethod:
        return self.build_method_
    
    @property
    def state_data(self) -> Any:
        return self.state_data_
    
    @property
    def num_state_data(self) -> int:
        return self.num_state_data_

    @property
    def market_data(self) -> Any:
        return self.market_data_


class Model(metaclass=ABCMeta):

    def __init__(self, 
                 value_date : Date, 
                 model_type : ModelType,
                 data_collection : DataCollection,
                 build_method_collection : BuildMethodCollection) -> None:
        
        self.value_date_ = value_date
        self.model_type_ = model_type
        self.data_collection_ = data_collection
        self.build_method_collection_ = build_method_collection
        self.components_ : Dict[str, ModelComponent] = {}
        self.component_indices_ : Dict[str, int] = {}
        self.sub_model_ = None        
        # risk
        self.is_jacobian_calculated_ = False
        self.num_components_ = 0
        self.num_sub_components_ = [] # for each component, how mnay state variables
        self.model_jacobian_ : np.ndarray = np.asarray([])

    @property    
    def value_date(self) -> Date:
        return self.value_date_
    
    @property
    def model_type(self) -> str:
        return self.model_type_.to_string()
    
    @property
    def data_collection(self) -> DataCollection:
        return self.data_collection_
    
    @property
    def build_method_collection(self) -> BuildMethodCollection:
        return self.build_method_collection_

    @property
    def num_components(self) -> int:
        return self.num_components_
    
    @property
    def component_indices(self) -> Dict[str, int]:
        """Map canonical component names to zero-based gradient block positions.

        Positions follow component registration order. Index aliases such as
        ``SOFR-1B`` may differ from the stored ``index.name()`` key. Use
        ``retrieve_model_component_index`` to resolve aliases to positions.
        """
        return self.component_indices_

    @property
    def num_sub_components(self) -> List[int]:
        """Return state-variable counts in the same order as gradient blocks."""
        return self.num_sub_components_

    @property
    def model_jacobian(self) -> np.ndarray:
        return self.model_jacobian_

    @property
    def sub_model(self) -> 'Model':
        return self.sub_model_

    @property
    def is_jacobian_calculated(self) -> bool:
        return self.is_jacobian_calculated_

    @abstractmethod
    def serialize(self) -> dict:
        pass

    @abstractclassmethod
    def deserialize(cls, input_dict : dict) -> 'Model':
        pass

    def resize_gradient(self, gradient: List[np.ndarray]) -> None:
        """Resize a list of one-dimensional component gradients in place.

        An empty list becomes one zero-filled array per registered component;
        array lengths follow ``num_sub_components``. If the outer length is
        wrong, all blocks are rebuilt. Otherwise, only blocks with the wrong
        length are replaced, and correctly sized blocks retain their values.

        This helper manages allocation, not overwrite/accumulate semantics.
        Gradient calculations must clear or replace existing values when
        overwriting, and preserve them when accumulating. Every existing block
        must be a writable one-dimensional floating-point NumPy array. Inputs
        are checked before any blocks are replaced. Pass a Python list, not an
        empty NumPy array; the method returns ``None``.

        Raises:
            TypeError: The container, a block, or a block's dtype is invalid.
            ValueError: A block is not one-dimensional or is read-only.
        """
        if not isinstance(gradient, list):
            raise TypeError("gradient must be a list of NumPy arrays")
        for i, block in enumerate(gradient):
            if not isinstance(block, np.ndarray):
                raise TypeError(f"gradient[{i}] must be a NumPy array")
            if block.ndim != 1:
                raise ValueError(f"gradient[{i}] must be one-dimensional")
            if not np.issubdtype(block.dtype, np.floating):
                raise TypeError(f"gradient[{i}] must have a floating-point dtype")
            if not block.flags.writeable:
                raise ValueError(f"gradient[{i}] must be writable")

        if len(gradient) != self.num_components:
            gradient[:] = [np.zeros(size) for size in self.num_sub_components]
            return

        for i in range(self.num_components):
            if len(gradient[i]) != self.num_sub_components[i]:
                gradient[i] = np.zeros(self.num_sub_components[i])

    def set_sub_model(self, model : 'Model') -> None:
        self.sub_model_ = model

    def set_model_component(self, target : str, model_component : ModelComponent) -> None:
        """Register a new component under its canonical identifier name.

        A successful registration appends one gradient block position. Reject
        duplicate or mismatched names before changing any model metadata.
        """
        if not isinstance(target, str):
            raise TypeError("Component registration target must be a string")
        canonical_name = model_component.component_identifier.name()
        if target != canonical_name:
            raise ValueError(f"Component registration target must be {canonical_name!r}")
        if target in self.components_:
            raise ValueError(f"Duplicate model component: {target}")

        self.component_indices_[target] = self.num_components_
        self.components_[target] = model_component
        self.num_sub_components_.append(model_component.num_state_data)
        # increment by 1
        self.num_components_ += 1
        
    def _resolve_component_name(self, target: ql.Index | str) -> str:
        """Resolve a stored name, registry alias, or index to an existing key."""
        if isinstance(target, ql.Index):
            name = target.name()
        elif isinstance(target, str):
            if target in self.components_:
                return target
            alias = target.upper()
            funding_registry = FundingIdentifierRegistry()
            if funding_registry.exists(alias):
                name = funding_registry.get(alias).name()
            else:
                try:
                    name = IndexRegistry().get(alias).name()
                except ValueError:
                    raise KeyError(f"This model does not contain component {target!r}.") from None
        else:
            raise TypeError("Component target must be a QuantLib index or a string")

        if name not in self.components_:
            raise KeyError(f"This model does not contain component {name!r}.")
        return name

    def retrieve_model_component(self, target : ql.Index | str) -> ModelComponent:
        """Retrieve a component by index, exact stored name, or registry alias.

        Registry aliases such as ``SOFR-1B`` are case-insensitive. Unknown or
        unbuilt components raise ``KeyError``; unsupported target types,
        including integer block positions, raise ``TypeError``.
        """
        return self.components_[self._resolve_component_name(target)]

    def retrieve_model_component_index(self, target: ql.Index | str) -> int:
        """Return a gradient block position using the component lookup rules."""
        return self.component_indices[self._resolve_component_name(target)]
    
    def perturb_model_parameter(self, target : ql.Index | str, parameter_id : int, perturb_size : float, override_parameter : Optional[bool]=False):
        component = self.retrieve_model_component(target)
        component.perturb_model_parameter(parameter_id, perturb_size, override_parameter)
