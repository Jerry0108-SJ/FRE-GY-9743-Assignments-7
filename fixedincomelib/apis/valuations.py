"""Public valuation parameters, PV/risk reports, and HW6 cashflow reports."""

from fixedincomelib.valuation import (
    RiskReport, ValuationParameters, ValuationParametersBuilderRegistry,
    ValuationParametersCollection, ValuationRequest, ValuationEngineProductRegistry,
)
# Import the implementation to register its (model, product, method) key.
from fixedincomelib.yield_curve.valuation_engine import ValuationEngineProductFixedAccrued

__all__ = [
    "qfCreateValuationParameters", "qfCreateValuationParametersCollection", "qfCreateValueReport",
]


def qfCreateValuationParameters(vp_type: str, content: list | dict) -> ValuationParameters:
    parameter_cls = ValuationParametersBuilderRegistry().get(vp_type)
    return parameter_cls(content)


def qfCreateValuationParametersCollection(
    valuation_parameters: list[ValuationParameters],
) -> ValuationParametersCollection:
    return ValuationParametersCollection(valuation_parameters)


def qfCreateValueReport(model, product, valuation_parameters_collection, request: str):
    """Return currency/PV rows or a RiskReport whose display uses 1 bp units.

    Request strings are case-insensitive. Only PV and FirstOrderRisk are
    supported; state-to-quote conversion is identity for direct IFR inputs.
    """
    parsed_request = ValuationRequest.from_string(request)
    engine = ValuationEngineProductRegistry.new_valuation_engine(
        model, product, valuation_parameters_collection, parsed_request,
    )
    if parsed_request == ValuationRequest.PV:
        engine.calculate_value()
        return engine.get_value_and_cash().pv
    gradient = []
    engine.calculate_risk(gradient)
    return RiskReport.from_model_gradient(model, gradient)


def qfCreateCashflowsReport(model, product, valuation_parameters_collection):
    """Return a cashflow snapshot for an interest-rate stream or composite product."""
    engine = ValuationEngineProductRegistry.new_valuation_engine(
        model, product, valuation_parameters_collection, ValuationRequest.PV)
    return engine.create_cash_flows_report()


__all__ += ["qfCreateCashflowsReport"]
