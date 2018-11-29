#
# Simplest sampling test: Can we recover a unimodal normal distribution?
#
# This file is part of Pints Functional Testing.
#  Copyright (c) 2017-2018, University of Oxford.
#  For licensing information, see the LICENSE file distributed with the Pints
#  functional testing software package.
#
from __future__ import absolute_import, division
from __future__ import print_function, unicode_literals

import pfunk
import matplotlib.pyplot as plt


class Geweke(pfunk.FunctionalTest):
    """
    Runs the successive-conditional simulator test described in the paper:


    Geweke (2004) Getting It Right, Journal of the American Statistical
    Association, 99:467, 799-804, DOI: 10.1198/016214504000001132


    Arguments:

    ``method``
        A *string* indicating the method to use, e.g. 'AdaptiveCovarianceMCMC'.
        (Must be a string, because we shouldn't import pints before we start
        testing.)

    """

    def __init__(self, method, nchains, pass_threshold, max_iter=200):

        # Can't check method here, don't want to import pints
        self._method = str(method)
        self._nchains = int(nchains)
        self._pass_threshold = float(pass_threshold)
        self._max_iter = int(max_iter)
        self._initial_phase_iter = 200

        # Create name and initialise
        name = 'geweke_mcmc' + self._method + '_' + str(self._nchains)
        super(Geweke, self).__init__(name)

    def _successive_conditional_simulator(self, method, model, parameters, times, log_prior):

        import pints
        import numpy as np

        # Create some toy data
        values = model.simulate(parameters[:-1], times)

        # Add noise
        values += np.random.normal(0, parameters[-1], values.shape)

        # Create an object with links to the model and time series
        problem = pints.SingleOutputProblem(model, times, values)

        # Create a log-likelihood function (adds an extra parameter!)
        log_likelihood = pints.UnknownNoiseLogLikelihood(problem)

        # Create a posterior log-likelihood (log(likelihood * prior))
        log_posterior = pints.LogPosterior(log_likelihood, log_prior)

        # Create a sampling routine
        if issubclass(method, pints.MultiChainMCMC):
            mcmc = method(self._nchains, parameters)
        else:
            mcmc = method(parameters)

        # get past the initial phase
        if mcmc.needs_initial_phase():
            mcmc.set_initial_phase(True)
            for i in range(self._initial_phase_iter):
                x = mcmc.ask()
                if issubclass(method, pints.MultiChainMCMC):
                    mcmc.tell([log_posterior(xi) for xi in x])
                else:
                    mcmc.tell(log_posterior(x))
            mcmc.set_initial_phase(False)

        mcmc.replace(parameters, log_posterior(parameters))
        x = mcmc.ask()
        if isinstance(method, pints.MultiChainMCMC):
            return mcmc.tell([log_posterior(xi) for xi in x])
        else:
            return mcmc.tell(log_posterior(x))

    def _run(self, result, log_path):

        import pints
        import pints.toy as toy
        import numpy as np

        import logging
        log = logging.getLogger(__name__)

        DEBUG = False

        # Store method name
        result['method'] = self._method
        log.info('Using method: ' + self._method)

        # Get method class
        method = getattr(pints, self._method)

        # Check number of chains
        if isinstance(method, pints.SingleChainMCMC) and self._nchains > 1:
            log.warn('SingleChainMCMC run with more than 1 chain.')
        elif isinstance(method, pints.MultiChainMCMC) and self._nchains == 1:
            log.warn('MultiChainMCMC run with only 1 chain.')

        # Load a forward model
        model = toy.LogisticModel()

        # Create some toy data
        times = np.linspace(0, 1000, 1000)

        # Create a uniform prior over both the parameters and the new noise variable
        noise = 0.1
        log_prior = pints.UniformLogPrior(
            [0.01, 400, noise*0.1],
            [0.02, 600, noise*100]
        )

        g_samples = np.empty((self._max_iter, model.n_parameters()+1))

        # implement the marginal-conditional simulator
        # sample from prior
        theta1_samples = log_prior.sample(n=self._max_iter)
        theta1_mean = np.empty((self._max_iter, model.n_parameters()+1))
        theta1_var = np.empty((self._max_iter, model.n_parameters()+1))

        # run model (TODO: not needed is g = theta)
        # add noise according to sampled noise

        for i in range(1, self._max_iter):
            theta1_mean[i, :] = np.mean(theta1_samples[:i, :], axis=0)
            theta1_var[i, :] = np.mean((theta1_samples[:i, :]-theta1_mean[:i, :])**2, axis=0)

        # implement the successive-conditional simulator
        theta2_samples = np.empty((self._max_iter, model.n_parameters()+1))
        theta2_samples[0, :] = log_prior.sample(n=1)

        theta2_mean = np.empty((self._max_iter, model.n_parameters()+1))
        theta2_var = np.empty((self._max_iter, model.n_parameters()+1))
        for i in range(1, self._max_iter):
            print('.', end='', flush=True)
            # implement the successive-conditional simulator
            theta2_samples[i, :] = \
                self._successive_conditional_simulator(method, model,
                                                       theta2_samples[i-1, :],
                                                       times, log_prior)

            theta2_mean[i, :] = np.mean(theta2_samples[:i+1, :], axis=0)
            theta2_var[i, :] = np.mean((theta2_samples[:i+1, :]-theta2_mean[i, :])**2, axis=0)
            g_samples[i, :] = (theta1_mean[i, :] - theta2_mean[i, :]) / \
                np.sqrt(theta1_var[i, :] / (i+1) + theta2_var[i, :]/(i+1))

        DEBUG = True
        if DEBUG:
            import pints.plot
            pints.plot.trace([g_samples])
            plt.show()

        # Store result
        result['p-value'] = 0

        # Store status
        result['status'] = 'done'

    def _analyse(self, results):
        return pfunk.assert_not_deviated_from(
            0, self._pass_threshold, results, 'kld')

    def _plot(self, results):

        figs = []

        # Figure: KL per commit
        figs.append(pfunk.plot.variable(
            results,
            'kld',
            'Normal w. ' + self._method,
            'Kullback-Leibler divergence', 3 * self._pass_threshold)
        )

        # Figure: KL over time
        figs.append(pfunk.plot.convergence(
            results,
            'iters',
            'klds',
            'Normal w. ' + self._method,
            'Iteration (sliding window)',
            'Kullback-Leibler divergence',
            0, 10)
        )

        # Figure: ESS per commit
        figs.append(pfunk.plot.variable(
            results,
            'ess',
            'Normal w. ' + self._method,
            'Effective sample size')
        )

        return figs
