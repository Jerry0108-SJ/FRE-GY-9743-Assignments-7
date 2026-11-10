import copy
import numpy as np
from abc import ABC, abstractmethod
from enum import Enum
from typing import List


class InterpMethod(Enum):

    PIECEWISE_CONSTANT_LEFT_CONTINUOUS = 'PIECEWISE_CONSTANT_LEFT_CONTINUOUS'
    LINEAR = 'LINEAR'
    MONOTONE_CONVEX = 'MONOTONE_CONVEX'

    @classmethod
    def from_string(cls, value: str) -> 'InterpMethod':
        if not isinstance(value, str):
            raise TypeError("value must be a string")
        try:
            return cls(value.upper())
        except ValueError:
            raise ValueError(f"Invalid token: {value}")

    def to_string(self) -> str:
        return self.value


class ExtrapMethod(Enum):

    FLAT = 'FLAT'
    LINEAR = 'LINEAR'

    @classmethod
    def from_string(cls, value: str) -> 'ExtrapMethod':
        if not isinstance(value, str):
            raise TypeError("value must be a string")
        try:
            return cls(value.upper())
        except ValueError:
            raise ValueError(f"Invalid token: {value}")

    def to_string(self) -> str:
        return self.value


class Interpolator1D(ABC):
    """Abstract interface for a 1-D interpolator."""

    def __init__(self,
                 axis1: np.ndarray,
                 values: np.ndarray,
                 interpolation_method: InterpMethod,
                 extrapolation_method: ExtrapMethod) -> None:

        self.axis1_ = axis1
        self.values_ = values
        self.interp_method_ = interpolation_method
        self.extrap_method_ = extrapolation_method
        self.length_ = len(self.axis1_)

    @abstractmethod
    def interpolate(self, x: float) -> float:
        pass

    @abstractmethod
    def integrate(self, start_x: float, end_x: float) -> float:
        pass

    @abstractmethod
    def gradient_wrt_ordinate(self, x: float) -> np.ndarray:
        pass

    @abstractmethod
    def gradient_of_integrated_value_wrt_ordinate(self, start_x: float, end_x: float) -> np.ndarray:
        pass

    @property
    def axis1(self) -> np.ndarray:
        return self.axis1_

    @property
    def values(self) -> np.ndarray:
        return self.values_

    @property
    def length(self) -> int:
        return self.length_

    @property
    def interp_method(self) -> str:
        return self.interp_method_.to_string()

    @property
    def extrap_method(self) -> str:
        return self.extrap_method_.to_string()


class Interpolator1DPCP(Interpolator1D):
    """Piecewise-constant left-continuous interpolator with FLAT extrapolation.

    With axis1 = [1, 3, 5, 7], values = [3, 4, 5, 6]:
        f(0.5) = 3, f(1) = 3, f(1.5) = 4, f(3) = 4, f(5.5) = 6, f(8) = 6
    """

    def __init__(self, axis1: np.ndarray, values: np.ndarray,
                 extrapolation_method: ExtrapMethod) -> None:
        super().__init__(axis1, values,
                         InterpMethod.PIECEWISE_CONSTANT_LEFT_CONTINUOUS,
                         extrapolation_method)
        assert self.extrap_method_ == ExtrapMethod.FLAT

    def interpolate(self, x: float) -> float:
        idx = min(int(np.searchsorted(self.axis1_, x, side='left')), self.length_ - 1)
        return float(self.values_[idx])

    def integrate(self, start_x: float, end_x: float) -> float:
        edges = np.concatenate(([-np.inf], np.asarray(self.axis1_, dtype=float)[:-1], [np.inf]))
        lo = np.maximum(start_x, edges[:-1])
        hi = np.minimum(end_x, edges[1:])
        overlaps = np.maximum(hi - lo, 0.0)
        return float(np.dot(np.asarray(self.values_, dtype=float), overlaps))

    def gradient_wrt_ordinate(self, x: float) -> np.ndarray:
        idx = min(int(np.searchsorted(self.axis1_, x, side='left')), self.length_ - 1)
        grad = np.zeros(self.length_)
        grad[idx] = 1.0
        return grad

    def gradient_of_integrated_value_wrt_ordinate(self, start_x: float, end_x: float) -> np.ndarray:
        edges = np.concatenate(([-np.inf], np.asarray(self.axis1_, dtype=float)[:-1], [np.inf]))
        lo = np.maximum(start_x, edges[:-1])
        hi = np.minimum(end_x, edges[1:])
        return np.maximum(hi - lo, 0.0)



class Interpolator1DMonotoneConvex(Interpolator1D):
    """HW7: C1 shape-preserving quadratic spline through the IFR nodes, FLAT outside them.

    Organised like Hagan-West (estimate a node quantity, collar it, then build each
    interval from at most two parabolas), but applied to slopes because the curve has
    to pass through the node values themselves:

      1. secant slopes  delta_i = (f_{i+1} - f_i) / (t_{i+1} - t_i)
      2. node slopes    s_i = distance-weighted average of delta_{i-1} and delta_i
                        (the Hagan-West weights); each end slope makes its end interval
                        a single parabola
      3. collar         s_i = 0 if the neighbouring secants differ in sign or one is flat,
                        otherwise |s_i| <= 2 * min(|delta_{i-1}|, |delta_i|)
      4. pieces         on [t_i, t_{i+1}] the derivative is the continuous piecewise-linear
                        function through (t_i, s_i), (knot_i, m_i), (t_{i+1}, s_{i+1}).
                        If s_i and s_{i+1} lie on opposite sides of delta_i the knot sits
                        where m_i = delta_i; otherwise it sits at the midpoint. In both
                        cases m_i is the value that makes the curve end at f_{i+1}.

    Result: the curve passes through every node and has a continuous first derivative
    between the first and last node. It is monotone on every node interval, because
    s_i, m_i and s_{i+1} all carry the sign of delta_i. It is convex on a node interval
    whenever s_i < delta_i < s_{i+1}, which holds for convex data (increasing secants).
    One node gives a constant curve and two nodes give a straight line.
    """

    # Smallest share of an interval that either of its two parabolas may occupy.
    _MIN_KNOT_FRACTION = 1.0e-12

    def __init__(self, axis1: np.ndarray, values: np.ndarray,
                 extrapolation_method: ExtrapMethod) -> None:
        super().__init__(axis1, values, InterpMethod.MONOTONE_CONVEX,
                         extrapolation_method)
        # TODO: Prepare your interpolation method.
        assert self.extrap_method_ == ExtrapMethod.FLAT

        x = np.asarray(self.axis1_, dtype=float)
        y = np.asarray(self.values_, dtype=float)
        n = self.length_
        if n == 0:
            raise ValueError("MONOTONE_CONVEX needs at least one node.")
        if n > 1 and not np.all(np.diff(x) > 0.0):
            raise ValueError("MONOTONE_CONVEX needs strictly increasing nodes.")

        self.first_x_, self.last_x_ = float(x[0]), float(x[-1])
        self.first_value_, self.last_value_ = float(y[0]), float(y[-1])

        if n == 1:
            # One node (the funding spread curve): constant, so there are no spline pieces.
            self.piece_start_ = np.empty(0)
            self.piece_value_ = np.empty(0)
            self.piece_slope_ = np.empty(0)
            self.piece_curvature_ = np.empty(0)
            self.area_to_piece_ = np.zeros(1)
            return

        h = np.diff(x)                 # interval lengths
        delta = np.diff(y) / h         # secant slopes

        # Steps 2 and 3: node slopes, collared so that no interval can turn around.
        slope = np.empty(n)
        if n == 2:
            slope[:] = delta[0]
        else:
            left, right = delta[:-1], delta[1:]
            weighted = (h[:-1] * right + h[1:] * left) / (h[:-1] + h[1:])
            cap = 2.0 * np.minimum(np.abs(left), np.abs(right))
            slope[1:-1] = np.where(left * right > 0.0,
                                   np.sign(left) * np.minimum(np.abs(weighted), cap),
                                   0.0)
            slope[0] = 2.0 * delta[0] - slope[1]
            slope[-1] = 2.0 * delta[-1] - slope[-2]

        # Step 4: one knot per interval, at the fraction theta of its length.
        a, b = slope[:-1], slope[1:]
        below, above = delta - a, b - delta      # both > 0: convex piece, both < 0: concave
        shape_preserving = below * above > 0.0
        theta = np.full(n - 1, 0.5)
        theta[shape_preserving] = (above[shape_preserving]
                                   / (below[shape_preserving] + above[shape_preserving]))
        theta = np.clip(theta, self._MIN_KNOT_FRACTION, 1.0 - self._MIN_KNOT_FRACTION)
        knot_slope = 2.0 * delta - theta * a - (1.0 - theta) * b
        left_length, right_length = theta * h, (1.0 - theta) * h
        knot_value = y[:-1] + 0.5 * (a + knot_slope) * left_length

        # Two parabolas per interval, f(start + u) = value + slope * u + curvature * u**2.
        self.piece_start_ = np.column_stack([x[:-1], x[:-1] + left_length]).ravel()
        self.piece_value_ = np.column_stack([y[:-1], knot_value]).ravel()
        self.piece_slope_ = np.column_stack([a, knot_slope]).ravel()
        self.piece_curvature_ = np.column_stack([
            (knot_slope - a) / (2.0 * left_length),
            (b - knot_slope) / (2.0 * right_length),
        ]).ravel()
        length = np.column_stack([left_length, right_length]).ravel()
        area = length * (self.piece_value_
                         + length * (self.piece_slope_ / 2.0
                                     + length * self.piece_curvature_ / 3.0))
        # Integral of the curve from the first node up to the start of each piece.
        self.area_to_piece_ = np.concatenate(([0.0], np.cumsum(area)))

    def _piece(self, x: float) -> int:
        idx = int(np.searchsorted(self.piece_start_, x, side='right')) - 1
        return min(max(idx, 0), len(self.piece_start_) - 1)

    def _area_from_first_node(self, x: float) -> float:
        if x <= self.first_x_:
            return self.first_value_ * (x - self.first_x_)
        if x >= self.last_x_:
            return float(self.area_to_piece_[-1]) + self.last_value_ * (x - self.last_x_)
        k = self._piece(x)
        u = x - self.piece_start_[k]
        return float(self.area_to_piece_[k]
                     + u * (self.piece_value_[k]
                            + u * (self.piece_slope_[k] / 2.0
                                   + u * self.piece_curvature_[k] / 3.0)))

    def interpolate(self, x: float) -> float:
        if x <= self.first_x_:
            return self.first_value_
        if x >= self.last_x_:
            return self.last_value_
        k = self._piece(x)
        u = x - self.piece_start_[k]
        return float(self.piece_value_[k]
                     + u * (self.piece_slope_[k] + u * self.piece_curvature_[k]))

    def integrate(self, start_x: float, end_x: float) -> float:
        return float(self._area_from_first_node(end_x) - self._area_from_first_node(start_x))
    # Optional risk interface
    # The test cells for risk are not prepared but you can do it by your own.
    def gradient_wrt_ordinate(self, x: float) -> np.ndarray:
        raise NotImplementedError("Optional risk: ordinate gradient is not implemented")

    def gradient_of_integrated_value_wrt_ordinate(
        self, start_x: float, end_x: float,
    ) -> np.ndarray:
        raise NotImplementedError("Optional risk: integrated ordinate gradient is not implemented")


class InterpolatorFactory:

    @staticmethod
    def create_1d_interpolator(axis1: np.ndarray | List,
                               values: np.ndarray | List,
                               interpolation_method: InterpMethod,
                               extrapolation_method: ExtrapMethod):

        axis1_ = copy.deepcopy(axis1)
        values_ = copy.deepcopy(values)
        if isinstance(axis1_, list):
            axis1_ = np.array(axis1_)
        if isinstance(values_, list):
            values_ = np.array(values_)
        assert len(axis1_.shape) == 1 and len(values_.shape) == 1
        assert len(axis1_) == len(values_)
        assert np.all(np.diff(axis1_) >= 0)

        if interpolation_method == InterpMethod.PIECEWISE_CONSTANT_LEFT_CONTINUOUS:
            return Interpolator1DPCP(axis1_, values_, extrapolation_method)
        elif interpolation_method == InterpMethod.MONOTONE_CONVEX:
            return Interpolator1DMonotoneConvex(axis1_, values_, extrapolation_method)
        else:
            raise ValueError(f'Unsupported interpolation method: {interpolation_method}')
