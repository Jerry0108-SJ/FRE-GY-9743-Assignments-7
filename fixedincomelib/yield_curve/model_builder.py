"""Build yield-curve components directly from IFR state data.

Tenor conversion and state construction follow the course template. Market IFR
values are used as supplied; the builder performs no instrument-price solving.
"""

import numpy as np

from fixedincomelib.date import Date, Period, add_period, accrued
from fixedincomelib.date.basics import TermOrDate as TermOrTerminationDate
from fixedincomelib.data import Data1D, DataCollection
from fixedincomelib.market import DataConventionIFR
from fixedincomelib.model import BuildMethodCollection, ModelBuilderRegistry
from fixedincomelib.yield_curve.build_method import YieldCurveIndexBuildMethod, YieldCurveFundingBuildMethod
from fixedincomelib.yield_curve.yield_curve_model import YieldCurve, YieldCurveModelComponent

__all__ = ["YieldCurveBuilder"]


class YieldCurveBuilder:

    @staticmethod
    def create_model_yield_curve(
        value_date: Date,
        data_collection: DataCollection,
        build_method_collection: BuildMethodCollection,
    ):
        if not value_date.is_valid():
            raise ValueError("A valid model value date is required.")
        if build_method_collection.num_build_methods == 0:
            raise ValueError("At least one IFR build method is required.")

        model_yield_curve = YieldCurve(value_date, data_collection, build_method_collection)

        # The template's direct-state branch, applied to every IFR build method.
        for _, this_bm in build_method_collection.items:
            if not isinstance(this_bm, (YieldCurveIndexBuildMethod, YieldCurveFundingBuildMethod)):
                raise TypeError("IFR construction requires a yield-curve index or funding build method.")
            data_conv_ifr = this_bm.instantaneous_forward_rate
            if not isinstance(data_conv_ifr, DataConventionIFR):
                raise ValueError(f"{this_bm.target}: an IFR data convention is required.")
            state_data = data_collection.get_data_from_data_collection(
                "INSTANTANEOUS FORWARD RATE", data_conv_ifr.name
            )
            if not isinstance(state_data, Data1D):
                raise TypeError(f"{data_conv_ifr.name}: IFR inputs must be Data1D.")
            component = YieldCurveBuilder.calibrate_single_component_from_state_data(
                value_date, data_conv_ifr, state_data, this_bm
            )
            target_name = this_bm.target_index.name()
            if target_name in model_yield_curve.component_indices:
                raise ValueError(f"Duplicate yield-curve component: {target_name}")
            model_yield_curve.set_model_component(target_name, component)

        # Validate references after all components exist, independent of input order.
        for _, this_bm in build_method_collection.items:
            reference_index = getattr(this_bm.target_index, "reference_index", None)
            if reference_index is not None:
                model_yield_curve.retrieve_model_component(reference_index)

        return model_yield_curve

    @staticmethod
    def calibrate_single_component_from_state_data(
        value_date: Date,
        data_conv: DataConventionIFR,
        state_data: Data1D,
        build_method: YieldCurveIndexBuildMethod | YieldCurveFundingBuildMethod,
    ):

        time_to_anchored_dates = []
        values = []
        market_data = []
        for i in range(len(state_data.axis1)):
            this_x = state_data.axis1[i]
            if TermOrTerminationDate(this_x).is_term():
                # if it is term
                moved_date = add_period(
                    value_date,
                    Period(this_x),
                    data_conv.business_day_convention,
                    data_conv.holiday_convention,
                )
                time = accrued(value_date, moved_date)
            else:
                # if it is date
                time = accrued(value_date, Date(this_x))
            time_to_anchored_dates.append(time)
            values.append(state_data.values[i])
            market_data.append(
                [
                    "INSTANTANEOUS FORWARD RATE",
                    data_conv.conv_name,
                    this_x,
                    "",
                    state_data.values[i],
                    state_data.data_identifier.unit(),
                ]
            )

        combined_data = np.asarray([time_to_anchored_dates, values], dtype=float)
        if combined_data.shape[1] == 0:
            raise ValueError(f"{data_conv.name}: IFR data must contain at least one node.")
        if not np.all(np.isfinite(combined_data)):
            raise ValueError(f"{data_conv.name}: node times and IFR values must be finite.")
        if np.any(combined_data[0] < 0):
            raise ValueError(f"{data_conv.name}: IFR nodes cannot precede the model value date.")
        if not np.all(np.diff(combined_data[0]) > 0):
            raise ValueError(f"{data_conv.name}: IFR node times must be strictly increasing.")

        return YieldCurveModelComponent(
            value_date,
            build_method.target_index,
            combined_data,
            build_method,
            market_data=market_data,
        )


ModelBuilderRegistry().register(
    YieldCurve._model_type.to_string(), YieldCurveBuilder.create_model_yield_curve
)
