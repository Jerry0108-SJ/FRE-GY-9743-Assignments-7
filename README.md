# FRE-GY-9743-Assignments-2026fall
Assignments for NYU, FRE-GY 9743, Fall 2026.

## HW7: a monotone, convex IFR interpolator

[HW7 notebook](hw7_monotone_convex_interpolator.ipynb) has six pricing cells:
PCP/student pairs for FRA, RFR swap, and overnight basis swap. Each contains an
explicit product-convention dictionary and direct calls to the existing APIs.
Change only `interpolation method` and rebuild the model to select the student's
class through `InterpMethod` and `InterpolatorFactory`. Implement that class in
[numerics.py](fixedincomelib/utilities/numerics.py); its skeleton and factory entry
are supplied. Cell 1 includes the shared imports and IFR data. Run cells 1, 3, 5
for PCP, then all six after completing the student class. No calibration is required.

## HW3: atomic products and the Visitor pattern

The cashflow classes in `fixedincomelib/product/linear_products.py` follow:

```text
Product
└── ProductCashflow
    ├── ProductFixedAccruedCashflow
    └── ProductOvernightIndexCashflow
```

`Product` and `ProductCashflow` are abstract. `ProductCashflow` initializes
currency, signed notional, direction and payment date. Each concrete product
represents one cashflow building block; a visitor collects its display fields.

### Public API

Run `hw3_products.ipynb` from the project root with a Python 3.11 environment
containing the `requirements.txt` dependencies, or use:

```python
from fixedincomelib import (
    qfCreateProductFixedAccruedCashflow,
    qfCreateProductOvernightIndexCashflow,
    qfDisplayProduct,
)

fixed = qfCreateProductFixedAccruedCashflow(
    effective_date="2026-01-02",
    termination_date="2026-04-02",
    currency="USD",
    notional=1_000_000,
    accrual_basis="ACT/360",
    payment_date="2026-04-06",
)

overnight = qfCreateProductOvernightIndexCashflow(
    effective_date="2026-01-02",
    term_or_termination_date="3M",  # also accepts "2026-04-02"
    overnight_index="SOFR-1B",
    notional=-1_000_000,
    compounding_method="compound",
    spread=0.001,  # 10 basis points
    payment_date="2026-04-06",
)

print(qfDisplayProduct(fixed))
print(qfDisplayProduct(overnight))
assert fixed.accrued == 0.25
```

Both creation APIs return product objects. `qfDisplayProduct` returns a
10-row DataFrame with columns `Name` and `Value`.

### Visitor pattern

Read the course tutorial: [IV. Visitor Pattern](https://immense-chocolate-92e.notion.site/IV-Visitor-Pattern-2d4831d0b1d58191bc36ebae3d771d58).

A visitor adds an operation without changing the product classes. Display uses:

```text
qfDisplayProduct(product)
  → product.accept(visitor)
    → visitor.visit(product)
  → visitor.display()
```

`singledispatchmethod` selects the handler registered for the product type.

### Contract fields

| Product | Fields |
|---|---|
| Both | Currency, signed notional, long/short direction, payment date, first/last date |
| Fixed accrued | Effective date, termination date, accrual basis, business-day convention, holiday convention, computed year fraction |
| Overnight index | Effective date, termination date or tenor, index, compounding method, spread; currency comes from the index |

- Fixed `accrued` is a year fraction; this class has no `fixed_rate` field.
  In the example, 90 days / 360 gives 0.25 independently of notional.
- Negative notional implies `SHORT`; zero and positive notional imply `LONG`.
- An omitted, empty or `None` payment date defaults to termination date.
  An explicit payment date is stored separately from the accrual interval.
- Fixed accrual defaults to `F` and `USGS`. The date helper adjusts the accrual
  end for the calculation while preserving the stored contractual dates.
  Use `business_day_convention="NONE"` for no end adjustment.
- For overnight cashflows, explicit termination dates are retained. A tenor is
  advanced with the index's fixing calendar and business-day convention.
- Supported indices are `SOFR-1B` (USD), `FF-1B` (USD) and `SONIA-1B` (GBP),
  case-insensitively.
- Compounding labels are `simple`, `arithmetic` and `compound`; spread is an
  annual decimal rate. These are contract fields; creation and display do not price the cashflow.
- `serialize()` / `deserialize()` convert between products and dictionaries.

## HW5: valuation and first-order risk contract

The existing HW5 components provide model helpers, recursive discount-factor
gradients, valuation parameters/engine dispatch, the fixed-accrued engine, and
the public PV/FirstOrderRisk report API.

The scope is an IFR yield-curve model and `ProductFixedAccruedCashflow`, whose
product type is `PRODUCT_FIXED_ACCRUED`. Valuation accepts `PV` and
`FirstOrderRisk`. Components use their creation order for this assignment;
calibration ordering and conversion to calibrated-instrument quote risk belong
to a later stage.

The gradient and valuation code in steps 3–5 assumes valid inputs: gradient
arrays have the documented shape and dtype, reference chains are acyclic, and
funding settings match the product currency and available model components.
These methods focus on calculation rather than additional input validation.
The earlier model helpers retain their existing behavior described below.

### Model helpers available now

| Interface | Existing behavior |
|---|---|
| `retrieve_model_component(target)` | Accepts a QuantLib index object, an exact stored component name, or a case-insensitive registry alias |
| `retrieve_model_component_index(target)` | Returns the zero-based gradient block position using the same name resolution as component retrieval |
| `component_indices` | Maps canonical stored names to zero-based gradient block positions in registration order |
| `num_sub_components` | Lists the number of state variables in each component, in the same order |
| `resize_gradient(gradient)` | Validates existing blocks, resizes a Python list in place, allocates zero-filled arrays where needed, and returns `None` |
| `set_model_component(target, component)` | Appends a new component under its canonical identifier name; rejects duplicates and mismatched names before changing model metadata |

An input alias and a stored name can differ: `SOFR-1B` resolves to
`SOFRON Actual/360`. Both lookup helpers now resolve `SOFR-1B`, `sofr-1b`,
the exact stored name, and the corresponding index object to the same
component and position. Funding aliases such as `sofr-1b-flat` follow the same
rule. Lookup does not insert aliases into `component_indices` or change the
component order. With an already built model:

```python
component = model.retrieve_model_component("SOFR-1B")
position = model.retrieve_model_component_index("sofr-1b")
gradient = []
model.resize_gradient(gradient)
assert len(gradient[position]) == component.num_state_data
```

Unknown names and recognized indices absent from the model raise `KeyError`.
Unsupported target types, including integer block positions, raise `TypeError`.
Registration uses `component.component_identifier.name()` as its target;
duplicate or mismatched registration names raise `ValueError` without replacing
the existing component or changing the model's counts and positions.

`resize_gradient` preserves a block's contents when its length already matches.
If the outer list length is wrong, it rebuilds all blocks. Allocation and
clearing are separate responsibilities; this behavior supports accumulation.
Each existing block must be a writable, one-dimensional floating-point NumPy
array, even when its length needs adjusting. Integer arrays are rejected to
avoid truncating future gradient values. Invalid containers, blocks or dtypes
raise `TypeError`; non-vector or read-only arrays raise `ValueError`. All
existing blocks are checked before any replacements, so a validation failure
leaves the input list and its arrays unchanged.

### State variables and gradient layout

For each curve component, `state_data[0]` holds fixed node times and
`state_data[1]` holds IFR node values in decimal-rate units. Derivatives are
with respect to these values, keeping the node times fixed. A component with a
reference curve contributes its local IFR spread to the combined curve.

Model and product gradients use `list[np.ndarray]`, with one one-dimensional
floating-point array per component. Outer order is component creation order;
inner order is the component's state-node order. Components may have different
node counts. For two components with three and two nodes, the layout is:

```python
gradient = [
    np.array([g11, g12, g13]),  # component 0, nodes 0..2
    np.array([g21, g22]),       # component 1, nodes 0..1
]
```

Every model component has a block, including components unrelated to the
requested value. Those components contribute zero. Flattening is reserved for
report formatting and must preserve both component and node order.

### Gradient interfaces

The Python names follow the template's snake_case spelling of the instructor's
`discountFactorGradientWrtStateVariable` operation:

```python
# YieldCurveModelComponent: local IFR contribution only.
def discount_factor_gradient_wrt_state(
    self, expiry_date: Date, gradient_vector: np.ndarray,
    scaler: float = 1.0, accumulate: bool = False,
) -> None: ...

# YieldCurve: full model gradient, including recursive reference dependencies.
def discount_factor_gradient_wrt_state(
    self, index: ql.Index | str, expiry_date: Date,
    gradient_vector: list[np.ndarray],
    scaler: float = 1.0, accumulate: bool = False,
) -> None: ...
```

The component method receives a preallocated floating-point array of length
`num_state_data`. The model method accepts an empty list and uses the model
layout to allocate it. Subsequent calls may reuse a correctly sized list of
floating-point arrays. Both methods write into the supplied container and
return `None`.

For an unscaled derivative `g` and `s = scaler`, the output contract is:

| Mode | Result |
|---|---|
| `accumulate=False` | Replace the output with `s * g`, including zeros in unrelated model blocks |
| `accumulate=True` | Add `s * g` to the existing output; unrelated blocks retain their existing values |

`scaler` scales the new contribution only; it does not scale values already in
the output. It does not implicitly apply a basis-point conversion. Repeated
overwrite calls must give the same result without retaining earlier values.

The component gradient uses the same date-to-time convention as its existing
`discount_factor`. The model gradient follows the same stored component
`reference_index` chain as the model's recursive `discount_factor`. The chain
is assumed to contain existing components and no cycles. At the model value
date, the discount factor is one and its gradient is zero.

### Fixed-accrued valuation engine

`ValuationEngineProductFixedAccrued` uses the existing
`ProductFixedAccruedCashflow` class and the following interfaces:

```python
def __init__(self, model, valuation_parameters_collection, product, request): ...
def calculate_value(self) -> None: ...
def calculate_risk(
    self, gradient: list[np.ndarray],
    scaler: float = 1.0, accumulate: bool = False,
) -> None: ...
```

The constructor obtains the funding curve through
`FundingIndexParameter.get_funding_index(product.currency)` in a
`ValuationParametersCollection`. The model supplies the valuation date.
Product fields describe the contract; valuation parameters select the funding
curve. A template-compatible `calculate_first_order_risk` entry point
delegates to `calculate_risk` with the same arguments.

`calculate_value` updates the engine's `value_` and `cash_`, which are exposed
through the `value` and `cash` properties. `calculate_risk` writes the raw
state-variable gradient into the supplied list using the same scaling and
accumulation contract as the model. Each call must reflect the current model
state, including parameter perturbations.

Let `N = product.notional`, `alpha = product.accrued`, and
`Tp = product.payment_date`. The cash amount is `C = N * alpha`. Notional is
already signed, so no additional long/short multiplier is applied. The product
has no separate fixed-rate field. Its accrual fraction is distinct from the
model's date-to-time conversion for discounting.

| Valuation date `v` | PV (`value`) | Cash (`cash`) | Unscaled state gradient |
|---|---|---|---|
| `v < Tp` | `C * D(Tp)` | `0` | `C * gradient(D(Tp))` |
| `v == Tp` | `C` | `C` | Zero in every block |
| `v > Tp` | `0` | `0` | Zero in every block |

The payment date governs both PV and risk. Risk remains present after the
accrual termination date while payment is still in the future. For a zero
contribution, overwrite mode writes zeros and accumulation mode preserves the
existing output.

### Public report API and units

```python
qfCreateValueReport(model, product, valuation_parameters_collection, request)
```

Requests are case-insensitive strings limited to `PV` and `FirstOrderRisk`;
other requests raise `ValueError`. The API selects the registered valuation
engine, invokes the requested calculation and collects the result.

- `PV` returns the template-style currency/value rows, for example
  `[["USD", pv]]`. The value includes cash payable on the valuation date.
- `FirstOrderRisk` returns a risk report. Engine gradients remain raw and
  grouped by component. The report retains component/node identification in
  model order; its `content` contains unscaled tabular derivatives. Its
  `display()` method returns a DataFrame with `UNIT` and `VALUES`, scaling
  `VALUES` for presentation without modifying the raw content.

For IFR nodes, `UNIT = 0.0001`. A displayed risk is the signed first-order
estimate of the PV change for a **positive one-basis-point shift of that node**:

```text
displayed risk = (dPV / dIFR_node) * 0.0001
```

Apply this factor exactly once, in report presentation. It is neither an
absolute-value risk measure nor an exact finite-bump revaluation. Repeated
`display()` calls must not apply additional scaling.

This assignment supplies IFR state values directly, so the state-to-input
quote mapping is the identity. The report can use the raw state derivatives
without a calibration Jacobian calculation or inversion.

### Valuation parameters and dispatch

`qfCreateValuationParameters(vp_type, content)` supports `ANALYTIC PARAMETER`
and `FUNDING INDEX PARAMETER`, with case-insensitive types/keys and either a
dictionary or list of key/value pairs. The funding parameter accepts a single
`FUNDING INDEX`, or matching semicolon-separated `CURRENCIES` and `FUNDING INDICES`.
The supplied identifiers and currency mappings are assumed valid and consistent
with the product. FX conversion and underlying-funding parameters are outside
this assignment.

`qfCreateValuationParametersCollection(parameters)` adds the default analytic
parameter when omitted; each supplied parameter type should occur once. As in the template,
`ValuationEngineProductRegistry` selects the engine using the tuple
`(model.model_type, product.product_type, analytic_parameter_type)`.
The public API converts the request string to `ValuationRequest` once; engine
constructors receive that enum directly.

```text
qfCreateValueReport(model, product, parameters, request)
  → ValuationEngineProductRegistry.new_valuation_engine(...)
    → ValuationEngineProductFixedAccrued
      PV: calculate_value() → model.discount_factor(...)
      FirstOrderRisk: calculate_risk(...)
        → model.discount_factor_gradient_wrt_state(...)
          → recurse through reference components
          → component.discount_factor_gradient_wrt_state(...)
            → interpolator.gradient_of_integrated_value_wrt_ordinate(...)
  → PV currency/value rows, or RiskReport
```

For a local component, the derivative is `-D(T) * gradient(integral IFR)`.
For a referencing component, the recursive product rule is
`gradient(D_local * D_ref) = D_local * gradient(D_ref) + D_ref * gradient(D_local)`.
Reference contributions are assembled separately before writing the caller's
gradient, so accumulation preserves any existing contributions.

The risk report keeps the template columns `DATA_TYPE`, `DATA_CONVENTION`,
`AXIS1`, `AXIS2`, `MARKET_QUOTE`, `UNIT` and `VALUES`, and adds `COMPONENT` and
zero-based `NODE_INDEX`. `MARKET_QUOTE` reflects the current IFR state, including
any parameter bumps. `report.state_gradient` preserves raw component blocks;
`report.content` contains raw rows. Each report is a snapshot of that calculation.

### Runnable PV and risk example

Run from the project root in the environment containing `requirements.txt`:

```python
import pandas as pd
from fixedincomelib import (
    qfCreateData1D, qfCreateDataCollection,
    qfCreateBuildMethod, qfCreateModelBuildMethodCollection, qfCreateModel,
    qfCreateProductFixedAccruedCashflow,
    qfCreateValuationParameters, qfCreateValuationParametersCollection,
    qfCreateValueReport,
)

data, methods = [], []
for kind, target, convention, dates, rates in [
    ("YIELD_CURVE_INDEX", "SOFR-1B", "SOFR-1B-IFR",
     ["2026-04-02", "2027-01-02", "2028-01-02"], [0.03, 0.04, 0.05]),
    ("YIELD_CURVE_FUNDING", "SOFR-1B-FLAT", "SOFR-1B-FUNDING-IFR",
     ["2026-07-02", "2027-01-02"], [0.001, 0.002]),
]:
    data.append(qfCreateData1D(
        "INSTANTANEOUS FORWARD RATE", convention,
        pd.DataFrame({"values": rates}, index=dates),
    ))
    methods.append(qfCreateBuildMethod(kind, {
        "TARGET": target, "INSTANTANEOUS FORWARD RATE": convention,
    }))

model = qfCreateModel(
    "2026-01-02", "YIELD_CURVE", qfCreateDataCollection(data),
    qfCreateModelBuildMethodCollection(methods),
)
product = qfCreateProductFixedAccruedCashflow(
    "2026-04-02", "2026-07-02", "USD", 1_000_000, "ACT/360",
    payment_date="2026-10-02", business_day_convention="NONE",
)
funding = qfCreateValuationParameters(
    "FUNDING INDEX PARAMETER", {"FUNDING INDEX": "SOFR-1B-FLAT"},
)
parameters = qfCreateValuationParametersCollection([funding])

pv = qfCreateValueReport(model, product, parameters, "PV")
risk = qfCreateValueReport(model, product, parameters, "FirstOrderRisk")
print(pv)                    # [["USD", ...]]
print(risk.state_gradient)   # Raw dPV/dIFR, blocks of length 3 and 2.
print(risk.display())        # Signed PV change per +1 bp at each node.
```


## HW6: interest-rate products and valuation

Open `hw6_interest_rate_products.ipynb` in the same Python environment as HW5.
Use the completed FRA as an example for the vanilla RFR swap and overnight index
basis swap. Assume all inputs are valid. This assignment covers product construction,
convention-driven creation, and PV valuation.

### Products

| Product | Legs | Meaning of `receive` |
|---|---|---|
| `ProductFRA` | One fixed coupon and one term-rate coupon | Receive fixed, pay term rate |
| `ProductRFRSwap` | Fixed stream and overnight stream | Receive fixed, pay overnight |
| `ProductOvernightIndexBasisSwap` | Two overnight streams, spread on leg 1 | Receive leg 1, pay leg 2 |

Use `ProductInterestRateStream` to construct each leg. The supplied
`ValuationEngineInterestRateStream` projects floating rates from each index's
curve and discounts payments using the funding curve. Overnight coupons compound
daily rates, with spread added outside compounding. Basis valuation follows the
template's decomposition into leg-1 index, leg-1 spread, and leg-2 index.
Notional is positive; the product engine applies the pay/receive direction once.

### FRA convention

The FRA fixes the whole-period simple rate at `Ts` and pays at `Te`.
Before fixing, for receive-fixed:

```text
F = (P_projection(t, Ts) / P_projection(t, Te) - 1) / tau
PV = N * tau * (K - F) * D_funding(t, Te)
```

From `Ts` onward, replace `F` with the observed term fixing. The payment at `Te`
is `N * tau * (K - fixing)`. On the payment date it is also today's cash;
after the payment date the remaining value is zero.

`USD-SOFR-FRA` uses ACT/360, USGS, Following, and zero fixing/payment offsets.
Its term fixing is separate from a daily SOFR fixing. Insert observations with
`qfInsertTermRateFixing(index, start, end, accrual_basis, rate)`;
daily observations use `qfInsertIndexFixing(index, date, rate)`.

### Product factory

`qfCreateProductFromDataConvention` calls
`ProductFactory.create_product_from_data_convention`, which selects a registered
builder. `create_fra` is the worked example; follow its structure for the two swap builders.

| Convention | Quote | Example `axis1` |
|---|---|---|
| `USD-SOFR-FRA` | Fixed rate | `3Mx6M`: start/end offsets from value date |
| `USD-SOFR-OIS` | Fixed rate | `3Mx1Y`: start offset, then tenor; `1Y`: spot tenor |
| `USD-FF-3M-OVER-USD-SOFR-OIS-3M` | Spread on leg 1 | Same date rules as swap |

Two explicit ISO dates are also supported. The basis convention's template name
is retained; its fields specify SOFR as leg 1 and Fed Funds as leg 2.

### Valuation

`qfCreateValueReport(model, product, parameters, "PV")` returns the product PV.
`qfCreateCashflowsReport(model, product, parameters).display()` shows the payment
dates, rates, amounts, funding discount factors, and signed cashflow PVs.
The notebook checks the FRA formula, swap leg sums, and factory/direct creation.
HW6 has no par-rate or risk exercises; the existing HW5 functionality is retained.
### Exercise locations

| # | File | Class / method | Method line | Task |
|---|---|---|---:|---|
| 1 | `fixedincomelib/product/linear_products.py` | `ProductRFRSwap.__init__` | 478 | Construct the fixed and overnight legs. |
| 2 | `fixedincomelib/product/linear_products.py` | `ProductOvernightIndexBasisSwap.__init__` | 709 | Construct both overnight legs; add spread to leg 1. |
| 3 | `fixedincomelib/product/product_factory.py` | `ProductFactory.create_rfr_swap` | 35 | Create the swap from its convention, dates, and quote. |
| 4 | `fixedincomelib/product/product_factory.py` | `ProductFactory.create_overnight_index_basis_swap` | 95 | Create the basis swap from both index conventions and spread. |
| 5 | `fixedincomelib/yield_curve/valuation_engine.py` | `ValuationEngineProductRfrSwap.calculate_value` | 162 | Combine leg PVs and cash using the supplied signs. |
| 6 | `fixedincomelib/yield_curve/valuation_engine.py` | `ValuationEngineProductOvernightIndexBasisSwap.calculate_value` | 221 | Combine the three signed component PVs and cash. |

These six methods are implemented in this directory. Restart the kernel and run all cells.
