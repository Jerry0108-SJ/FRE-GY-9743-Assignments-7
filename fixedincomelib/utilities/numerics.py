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
    """Monotone, convex piecewise-quadratic IFR interpolator (HW7).

    Inspired by Hagan & West (2006): the curve is built interval by interval
    from a one-parameter quadratic family whose shape parameter is clipped so
    that the piece can never leave the monotone-and-convex region, exactly as
    Hagan-West clip their g-function into "sectors".

    On node interval [x_i, x_{i+1}] with h_i = x_{i+1} - x_i,
    u = (x - x_i) / h_i in [0, 1] and D_i = f_{i+1} - f_i:

        f(x) = f_i + D_i * ((1 - a_i) * u + a_i * u**2)

    * f(x_i) = f_i and f(x_{i+1}) = f_{i+1} for every a_i, so the curve is
      continuous and passes through all supplied IFR points.
    * f'(x) = (D_i / h_i) * (1 - a_i + 2 a_i u). With |a_i| <= 1 this has the
      sign of D_i on the whole interval  ->  monotone.
    * f''(x) = 2 a_i D_i / h_i**2. Requiring a_i * D_i >= 0  ->  convex.
      Hence a_i is restricted to [0, 1] if D_i > 0, [-1, 0] if D_i < 0 and
      a_i = 0 (flat piece) if D_i = 0.

    Choice of a_i (smoothness): node slopes d_j are estimated with the
    Fritsch-Butland weighted harmonic mean of the neighbouring secant slopes
    (set to 0 at a local extremum of the data; one-sided secant at the two
    end nodes). a_i is then the least-squares fit of the piece's two end
    slopes, m_i (1 - a_i) and m_i (1 + a_i) with m_i = D_i / h_i, to
    (d_i, d_{i+1}), i.e. a_i = (d_{i+1} - d_i) / (2 m_i), clipped into the
    admissible range above. Where the data are locally convex
    (m_{j-1} <= m_j) the incoming slope is further capped, and the outgoing
    slope floored, at d_j, so f'(x_j-) <= f'(x_j+): convex data give a
    globally convex curve (Hagan-West shape preservation). The curve is then
    continuous and close to C1 at the nodes.

    Like Hagan-West's monotone convex method the scheme is local (piece i
    depends on nodes i-1..i+2) and positive (each piece stays between its two
    node values). Unlike their method, the inputs are point IFR values that
    must be interpolated, not interval-average discrete forwards.

    Data that cannot satisfy every requirement: monotonicity, convexity,
    continuity and node-matching inside each interval are hard constraints and
    always hold (the linear piece a_i = 0 is always admissible). What is given
    up is smoothness: when the data are not convex (secants decrease) or turn
    around (local max/min), the clip binds and the curve has a kink at the
    node instead of overshooting or becoming concave.

    Extrapolation: FLAT holds the end-node values; LINEAR continues with the
    end-node slope of the boundary piece. A single node gives a constant.
    ``integrate`` is exact (closed form), so discount factors carry no
    quadrature error.
    """

    def __init__(self, axis1: np.ndarray, values: np.ndarray,
                 extrapolation_method: ExtrapMethod) -> None:
        super().__init__(axis1, values, InterpMethod.MONOTONE_CONVEX,
                         extrapolation_method)
        assert self.extrap_method_ in (ExtrapMethod.FLAT, ExtrapMethod.LINEAR)
        assert self.length_ >= 1

        x = np.asarray(axis1, dtype=float)
        f = np.asarray(values, dtype=float)
        # Coincident abscissae carry no interval; keep the last value given.
        keep = np.append(np.diff(x) > 0.0, True)
        self.x_ = x[keep]
        self.f_ = f[keep]
        n = len(self.x_)

        self.h_ = np.diff(self.x_)
        self.df_ = np.diff(self.f_)
        self.a_ = np.zeros(max(n - 1, 0))
        self.left_slope_ = 0.0
        self.right_slope_ = 0.0
        if n < 2:
            return

        m = self.df_ / self.h_  # secant slopes
        d = np.zeros(n)
        d[0], d[-1] = m[0], m[-1]
        for j in range(1, n - 1):
            m0, m1 = m[j - 1], m[j]
            if m0 * m1 > 0.0:
                # Fritsch-Butland weighted harmonic mean (stays between m0, m1)
                w0 = 2.0 * self.h_[j] + self.h_[j - 1]
                w1 = self.h_[j] + 2.0 * self.h_[j - 1]
                d[j] = (w0 + w1) / (w0 / m0 + w1 / m1)

        for i in range(n - 1):
            if m[i] > 0.0:
                self.a_[i] = np.clip((d[i + 1] - d[i]) / (2.0 * m[i]), 0.0, 1.0)
            elif m[i] < 0.0:
                self.a_[i] = np.clip((d[i + 1] - d[i]) / (2.0 * m[i]), -1.0, 0.0)

        # Shape preservation across nodes (Hagan-West: "the curve is locally
        # monotone and convex if the inputs show the analogous discrete
        # properties"). Where the data are locally convex (m_{j-1} <= m_j),
        # d_j lies in [m_{j-1}, m_j]; capping the incoming slope at d_j and
        # flooring the outgoing slope at d_j makes f'(x_j-) <= f'(x_j+), so
        # convex data give a globally convex curve. Each cap keeps a_i in its
        # admissible range, and only uses d_j, so the method stays local.
        for j in range(1, n - 1):
            if m[j - 1] > m[j]:
                continue  # locally concave data: cannot be convex across x_j
            mp, mn = m[j - 1], m[j]
            if mp > 0.0:      # incoming slope mp(1+a) <= d_j
                self.a_[j - 1] = min(self.a_[j - 1], d[j] / mp - 1.0)
            elif mp < 0.0:
                self.a_[j - 1] = max(self.a_[j - 1], d[j] / mp - 1.0)
            if mn > 0.0:      # outgoing slope mn(1-a) >= d_j
                self.a_[j] = min(self.a_[j], 1.0 - d[j] / mn)
            elif mn < 0.0:
                self.a_[j] = max(self.a_[j], 1.0 - d[j] / mn)

        self.left_slope_ = m[0] * (1.0 - self.a_[0])
        self.right_slope_ = m[-1] * (1.0 + self.a_[-1])

    # ---- helpers ---------------------------------------------------------
    def _piece_value(self, i: int, u: float) -> float:
        a = self.a_[i]
        return float(self.f_[i] + self.df_[i] * ((1.0 - a) * u + a * u * u))

    def _piece_primitive(self, i: int, u: float) -> float:
        """Integral of piece i from x_i to x_i + u * h_i."""
        a = self.a_[i]
        return float(self.h_[i] * (self.f_[i] * u
                                   + self.df_[i] * ((1.0 - a) * u * u / 2.0
                                                    + a * u ** 3 / 3.0)))

    def _left_extrap_integral(self, lo: float, hi: float) -> float:
        """Integral over [lo, hi] subset of (-inf, x_0]."""
        x0, f0 = self.x_[0], self.f_[0]
        if self.extrap_method_ == ExtrapMethod.FLAT:
            return f0 * (hi - lo)
        s = self.left_slope_
        return f0 * (hi - lo) + 0.5 * s * ((hi - x0) ** 2 - (lo - x0) ** 2)

    def _right_extrap_integral(self, lo: float, hi: float) -> float:
        """Integral over [lo, hi] subset of [x_n, inf)."""
        xn, fn = self.x_[-1], self.f_[-1]
        if self.extrap_method_ == ExtrapMethod.FLAT:
            return fn * (hi - lo)
        s = self.right_slope_
        return fn * (hi - lo) + 0.5 * s * ((hi - xn) ** 2 - (lo - xn) ** 2)

    # ---- interface -------------------------------------------------------
    def interpolate(self, x: float) -> float:
        x = float(x)
        if len(self.x_) == 1:
            return float(self.f_[0])
        if x <= self.x_[0]:
            if self.extrap_method_ == ExtrapMethod.FLAT:
                return float(self.f_[0])
            return float(self.f_[0] + self.left_slope_ * (x - self.x_[0]))
        if x >= self.x_[-1]:
            if self.extrap_method_ == ExtrapMethod.FLAT:
                return float(self.f_[-1])
            return float(self.f_[-1] + self.right_slope_ * (x - self.x_[-1]))
        i = int(np.searchsorted(self.x_, x, side='right')) - 1
        u = (x - self.x_[i]) / self.h_[i]
        return self._piece_value(i, u)

    def integrate(self, start_x: float, end_x: float) -> float:
        start_x, end_x = float(start_x), float(end_x)
        if end_x < start_x:
            return -self.integrate(end_x, start_x)
        if end_x == start_x:
            return 0.0
        if len(self.x_) == 1:
            return float(self.f_[0]) * (end_x - start_x)

        total = 0.0
        x0, xn = self.x_[0], self.x_[-1]
        # left extrapolation region
        if start_x < x0:
            total += self._left_extrap_integral(start_x, min(end_x, x0))
        # right extrapolation region
        if end_x > xn:
            total += self._right_extrap_integral(max(start_x, xn), end_x)
        # interior pieces
        lo, hi = max(start_x, x0), min(end_x, xn)
        if hi > lo:
            for i in range(len(self.h_)):
                xl, xr = self.x_[i], self.x_[i + 1]
                a, b = max(lo, xl), min(hi, xr)
                if b <= a:
                    continue
                ua = (a - xl) / self.h_[i]
                ub = (b - xl) / self.h_[i]
                total += self._piece_primitive(i, ub) - self._piece_primitive(i, ua)
        return float(total)

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
