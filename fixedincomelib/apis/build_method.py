"""Create build-method configurations using the course APIs."""

from typing import List
from fixedincomelib.model import BuildMethod, BuildMethodCollection, BuildMethodBuilderRregistry
# Import supported curve build methods so their factory registrations are available.
from fixedincomelib.yield_curve import YieldCurveIndexBuildMethod, YieldCurveFundingBuildMethod

__all__ = ["qfCreateBuildMethod", "qfCreateModelBuildMethodCollection"]


def qfCreateBuildMethod(build_method_type : str, content : dict):
    assert 'TARGET' in content
    func = BuildMethodBuilderRregistry().get(build_method_type)
    return func(content['TARGET'], content)


def qfCreateModelBuildMethodCollection(bm_list : List[BuildMethod]):
    return BuildMethodCollection(bm_list)
