# Copyright 2020 MIT Probabilistic Computing Project.
# See LICENSE.txt

"""Convert SPN to JSON."""

from fractions import Fraction

import scipy.stats
import sympy

from ..spn import ContinuousLeaf
from ..spn import DiscreteLeaf
from ..spn import NominalLeaf
from ..spn import ProductSPN
from ..spn import SumSPN

# Needed for "eval"
from sympy import *
from ..transforms import Id
from ..transforms import Identity
from ..transforms import Radical
from ..transforms import Exponential
from ..transforms import Logarithm
from ..transforms import Abs
from ..transforms import Reciprocal
from ..transforms import Poly
from ..transforms import Piecewise
from ..transforms import EventInterval
from ..transforms import EventFiniteReal
from ..transforms import EventFiniteNominal
from ..transforms import EventOr
from ..transforms import EventAnd
from ..sym_util import NominalValue

def env_from_json(env):
    if env is None:
        return None
    # Used in eval.
    return {eval(k): eval(v) for k, v in env.items()}

def env_to_json(env):
    if len(env) == 1:
        return None
    return {repr(k): repr(v) for k, v in env.items()}

def scipy_dist_from_json(dist):
    constructor = getattr(scipy.stats, dist['name'])
    return constructor(*dist['args'], **dist['kwds'])

def scipy_dist_to_json(dist):
    return {
        'name': dist.dist.name,
        'args': dist.args,
        'kwds': dist.kwds
    }

def spn_from_json(metadata):
    if metadata['class'] == 'NominalLeaf':
        symbol = Id(metadata['symbol'])
        dist = {x: Fraction(w[0], w[1]) for x, w in metadata['dist']}
        return NominalLeaf(symbol, dist)
    if metadata['class'] == 'ContinuousLeaf':
        symbol = Id(metadata['symbol'])
        dist = scipy_dist_from_json(metadata['dist'])
        support = sympy.sympify(metadata['support'])
        conditioned = metadata['conditioned']
        env = env_from_json(metadata['env'])
        return ContinuousLeaf(symbol, dist, support, conditioned, env=env)
    if metadata['class'] == 'DiscreteLeaf':
        symbol = Id(metadata['symbol'])
        dist = scipy_dist_from_json(metadata['dist'])
        support = sympy.sympify(metadata['support'])
        conditioned = metadata['conditioned']
        env = env_from_json(metadata['env'])
        return DiscreteLeaf(symbol, dist, support, conditioned, env=env)
    if metadata['class'] == 'SumSPN':
        children = [spn_from_json(c) for c in metadata['children']]
        weights = metadata['weights']
        return SumSPN(children, weights)
    if metadata['class'] == 'ProductSPN':
        children = [spn_from_json(c) for c in metadata['children']]
        return ProductSPN(children)

    assert False, 'Cannot convert %s to SPN' % (metadata,)

def spn_to_json(spn):
    if isinstance(spn, NominalLeaf):
        return {
            'class'        : 'NominalLeaf',
            'symbol'       : spn.symbol.token,
            'dist'         : [
                (str(x), (w.numerator, w.denominator))
                for x, w in spn.dist.items()
            ],
            'env'         : env_to_json(spn.env),
        }
    if isinstance(spn, ContinuousLeaf):
        return {
            'class'         : 'ContinuousLeaf',
            'symbol'        : spn.symbol.token,
            'dist'          : scipy_dist_to_json(spn.dist),
            'support'       : repr(spn.support),
            'conditioned'   : spn.conditioned,
            'env'           : env_to_json(spn.env),
        }
    if isinstance(spn, DiscreteLeaf):
        return {
            'class'         : 'DiscreteLeaf',
            'symbol'        : spn.symbol.token,
            'dist'          : scipy_dist_to_json(spn.dist),
            'support'       : repr(spn.support),
            'conditioned'   : spn.conditioned,
            'env'           : env_to_json(spn.env),
        }
    if isinstance(spn, SumSPN):
        return {
            'class'        : 'SumSPN',
            'children'      : [spn_to_json(c) for c in spn.children],
            'weights'       : spn.weights,
        }
    if isinstance(spn, ProductSPN):
        return {
            'class'        : 'ProductSPN',
            'children'      : [spn_to_json(c) for c in spn.children],
        }
    assert False, 'Cannot convert %s to JSON' % (spn,)
