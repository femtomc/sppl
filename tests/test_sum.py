# Copyright 2020 MIT Probabilistic Computing Project.
# See LICENSE.txt

from fractions import Fraction
from math import log

import pytest

import numpy
import sympy

from spn.distributions import Gamma
from spn.distributions import NominalDist
from spn.distributions import Norm
from spn.math_util import allclose
from spn.math_util import isinf_neg
from spn.math_util import logdiffexp
from spn.math_util import logsumexp
from spn.spn import ContinuousReal
from spn.spn import ExposedSumSPN
from spn.spn import NominalDistribution
from spn.spn import ProductSPN
from spn.spn import SumSPN
from spn.sym_util import NominalSet
from spn.transforms import Identity

rng = numpy.random.RandomState(1)

def test_sum_normal_gamma():
    X = Identity('X')
    weights = [
        log(Fraction(2, 3)),
        log(Fraction(1, 3))
    ]
    spn = SumSPN(
        [X >> Norm(loc=0, scale=1), X >> Gamma(loc=0, a=1),], weights)

    assert spn.logprob(X > 0) == logsumexp([
        spn.weights[0] + spn.children[0].logprob(X > 0),
        spn.weights[1] + spn.children[1].logprob(X > 0),
    ])
    assert spn.logprob(X < 0) == log(Fraction(2, 3)) + log(Fraction(1, 2))
    samples = spn.sample(100, rng)
    assert all(s[X] for s in samples)
    spn.sample_func(lambda X: abs(X**3), 100, rng)
    with pytest.raises(ValueError):
        spn.sample_func(lambda Y: abs(X**3), 100, rng)

    spn_condition = spn.condition(X < 0)
    assert isinstance(spn_condition, ContinuousReal)
    assert spn_condition.conditioned
    assert spn_condition.logprob(X < 0) == 0
    samples = spn_condition.sample(100, rng)
    assert all(s[X] < 0 for s in samples)

    assert spn.logprob(X < 0) == logsumexp([
        spn.weights[0] + spn.children[0].logprob(X < 0),
        spn.weights[1] + spn.children[1].logprob(X < 0),
    ])

def test_sum_normal_gamma_exposed():
    X = Identity('X')
    W = Identity('W')
    weights = (W >> NominalDist({
        '0': Fraction(2,3),
        '1': Fraction(1,3),
    }))
    children = {
        '0': X >> Norm(loc=0, scale=1),
        '1': X >> Gamma(loc=0, a=1),
    }
    spn = ExposedSumSPN(children, weights)

    assert spn.logprob(W << {'0'}) == log(Fraction(2, 3))
    assert spn.logprob(W << {'1'}) == log(Fraction(1, 3))
    assert allclose(spn.logprob((W << {'0'}) | (W << {'1'})), 0)
    assert spn.logprob((W << {'0'}) & (W << {'1'})) == -float('inf')

    assert allclose(
        spn.logprob((W << {'0', '1'}) & (X < 1)),
        spn.logprob(X < 1))

    assert allclose(
        spn.logprob((W << {'0'}) & (X < 1)),
        spn.weights[0] + spn.children[0].logprob(X < 1))

    spn_condition = spn.condition((W << {'1'}) | (W << {'0'}))
    assert isinstance(spn_condition, SumSPN)
    assert len(spn_condition.weights) == 2
    assert \
        allclose(spn_condition.weights[0], log(Fraction(2,3))) \
            and allclose(spn_condition.weights[0], log(Fraction(2,3))) \
        or \
        allclose(spn_condition.weights[1], log(Fraction(2,3))) \
            and allclose(spn_condition.weights[0], log(Fraction(2,3))
        )

    spn_condition = spn.condition((W << {'1'}))
    assert isinstance(spn_condition, ProductSPN)
    assert isinstance(spn_condition.children[0], NominalDistribution)
    assert isinstance(spn_condition.children[1], ContinuousReal)
    assert spn_condition.logprob(X < 5) == spn.children[1].logprob(X < 5)

def test_sum_normal_nominal():
    X = Identity('X')
    children = [
        X >> Norm(loc=0, scale=1),
        X >> NominalDist({'low': Fraction(3, 10), 'high': Fraction(7, 10)}),
    ]
    weights = [log(Fraction(4,7)), log(Fraction(3, 7))]

    spn = SumSPN(children, weights)

    assert allclose(
        spn.logprob(X < 0),
        log(Fraction(4,7)) + log(Fraction(1,2)))

    assert allclose(
        spn.logprob(X << {'low'}),
        log(Fraction(3,7)) + log(Fraction(3, 10)))

    assert allclose(
        spn.logprob(~(X << {'low'})),
        logdiffexp(0, spn.logprob((X << {'low'}))))

    assert isinf_neg(spn.logprob((X < 0) & (X << {'low'})))

    assert allclose(
        spn.logprob((X < 0) | (X << {'low'})),
        logsumexp([spn.logprob(X < 0), spn.logprob(X << {'low'})]))

    assert isinf_neg(spn.logprob(X << {'a'}))
    assert allclose(spn.logprob(~(X << {'a'})), 0)

    assert allclose(
        spn.logprob(X**2 < 9),
        log(Fraction(4, 7)) + spn.children[0].logprob(X**2 < 9))

    spn_condition = spn.condition(X**2 < 9)
    assert isinstance(spn_condition, ContinuousReal)
    assert spn_condition.support == sympy.Interval.open(-3, 3)

    spn_condition = spn.condition((X**2 < 9) | X << {'low'})
    assert isinstance(spn_condition, SumSPN)
    assert spn_condition.children[0].support == sympy.Interval.open(-3, 3)
    assert spn_condition.children[1].support == NominalSet('low', 'high')
    assert isinf_neg(spn_condition.children[1].logprob(X << {'high'}))

    spn_condition = spn.condition((X**2 < 9) | ~(X << {'1'}))
    assert spn_condition.children == spn_condition.children

    # FIXME: Solving this event yields Reals, eliminating the Nominal
    # branch, even though ~(X << {1}) is satisfied by that branch.
    with pytest.raises(AssertionError):
        assert spn.condition((X < 9) | ~(X << {1})) == spn
