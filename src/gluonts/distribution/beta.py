# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the "license" file accompanying this file. This file is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language governing
# permissions and limitations under the License.

# Standard library imports
import math
from functools import partial
from typing import Dict, Optional, Tuple, List

# Third-party imports
import numpy as np

# First-party imports
from gluonts.distribution import Dirichlet
from gluonts.model.common import Tensor
from gluonts.support.util import erf, erfinv
from gluonts.core.component import validated

# Relative imports
from .distribution import Distribution, _sample_multiple, getF, softplus
from .distribution_output import DistributionOutput


class Beta(Distribution):
    r"""
    Beta distribution.

    Parameters
    ----------
    alpha
        Tensor containing the alpha shape parameters, of shape `(*batch_shape, *event_shape)`.
    beta
        Tensor containing the beta shape parameters, of shape `(*batch_shape, *event_shape)`.
    F
    """

    is_reparameterizable = False

    @validated()
    def __init__(self, alpha: Tensor, beta: Tensor, F=None) -> None:
        self.alpha = alpha
        self.beta = beta
        self.F = (
            F if F else getF(alpha)
        )  # assuming alpha and beta of same type

    @property
    def batch_shape(self) -> Tuple:
        return self.alpha.shape

    @property
    def event_shape(self) -> Tuple:
        return ()

    @property
    def event_dim(self) -> int:
        return 0

    def log_prob(self, x: Tensor) -> Tensor:
        F = self.F
        alpha, beta = self.alpha, self.beta

        return (
            (alpha - 1) * F.log(x)
            + (beta - 1) * F.log(1 - x)
            - F.gammaln(alpha)
            - F.gammaln(beta)
            + F.gammaln(alpha + beta)
        )

    @property
    def mean(self) -> Tensor:
        return self.alpha / (self.alpha + self.beta)

    @property
    def variance(self) -> Tensor:
        F = self.F
        alpha, beta = self.alpha, self.beta

        return (alpha * beta) / (F.square(alpha + beta) * (alpha + beta + 1))

    @property
    def stddev(self) -> Tensor:
        return self.F.sqrt(self.variance)

    def sample(
        self, num_samples: Optional[int] = None, dtype=np.float32
    ) -> Tensor:
        def s(alpha: Tensor, beta: Tensor) -> Tensor:
            F = getF(alpha)
            samples_X = F.sample_gamma(
                alpha=alpha, beta=F.ones_like(alpha), dtype=dtype
            )
            samples_Y = F.sample_gamma(
                alpha=beta, beta=F.ones_like(beta), dtype=dtype
            )
            return samples_X / (samples_X + samples_Y)

        return _sample_multiple(
            s, alpha=self.alpha, beta=self.beta, num_samples=num_samples
        )

    @property
    def args(self) -> List:
        return [self.alpha, self.beta]


class BetaOutput(DistributionOutput):
    args_dim: Dict[str, int] = {"alpha": 1, "beta": 1}
    distr_cls: type = Beta

    @classmethod
    def domain_map(cls, F, alpha, beta):
        r"""
        Maps raw tensors to valid arguments for constructing a Beta
        distribution.

        Parameters
        ----------
        F:
        alpha:
            Tensor of shape `(*batch_shape, 1)`
        beta:
            Tensor of shape `(*batch_shape, 1)`

        Returns
        -------
        Tuple[Tensor, Tensor]:
            Two squeezed tensors, of shape `(*batch_shape)`: both have entries mapped to the
            positive orthant.
        """
        alpha = softplus(F, alpha) + 1e-8
        beta = softplus(F, beta) + 1e-8
        return alpha.squeeze(axis=-1), beta.squeeze(axis=-1)

    @property
    def event_shape(self) -> Tuple:
        return ()
