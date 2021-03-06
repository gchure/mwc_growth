"""
A module for computing properties of various transcriptional
regulatory architectures.
"""

import numpy as np
import scipy.optimize

def load_constants():
    """ Returns literature constants for wild-type repressor"""
    return {'O1':-15.3, 'O2':-13.9, 'O3':-9.7, 'Oid':-17.0,
           'ka':139, 'ki':0.53, 'n_sites':2, 'n_ns':4.6e6,
           'ep_ai':4.5}

class MWC(object):
    R"""
    A base class for the Monod - Wyman - Changeux model for
    allostery.
    """

    def __init__(self, effector_conc=None, ka=None, ki=None, ep_ai=None,
                 n_sites=2, log_transform=False):
        """
        Parameters
        ----------
        ep_ai : int, float, or array
            Difference in energy between the active and inactive allosteric
            states of the repressor. This should be in units of k_BT.
        ka, ki : ints, floats, or arrays
            The effector dissociation constants for the acitve and inactive
            state of the repressor.
        log_transform:  bool
            If True, the provided ka and ki are the log transform and will be
            exponentiated in the calculation of pact.
        effector_conc: int, float, or array
            Concentration of the allosteric effector molecule.
        n_sites : int, float or array
            Number of cooperative effector binding sites on the repressor.
            Default value is 2.
        """
        kwargs = dict(effector_conc=effector_conc, ka=ka, ki=ki,
                      ep_ai=ep_ai, n_sites=n_sites)

        # Ensure values are provided.
        for k in kwargs.keys():
            if type(kwargs[k]) is None:
                raise RuntimeError(
                    "{0} is NoneType and must be defined.".format(k))

        # Assign the variables.
        self.c = effector_conc
        self.ep_ai = ep_ai
        self.n = n_sites
        if log_transform is True:
            self.ka = np.exp(ka)
            self.ki = np.exp(ki)
        else:
            self.ka = ka
            self.ki = ki

        # Ensure ka and ki are not zero.
        if type(ka) is float or int:
            _ka = np.array([ka])
        if type(ki) is float or int:
            _ki = np.array([ki])

        if (_ka == 0).any() or (_ki == 0).any():
            raise ValueError('ka and/or ki cannot be zero.')

        # Ensure positivity of values.
        positive_kwargs = dict(effector_conc=self.c,
                               ka=self.ka, ki=self.ki, n_sites=self.n)
        for k in positive_kwargs.keys():
            val = positive_kwargs[k]
            if type(val) is float or int:
                val = np.array([val])
            if (val < 0).any():
                raise RuntimeError('{0} must be positive.'.format(k))

    def pact(self):
        R"""
        Compute the probability of the active state at each provided parameter
        value

        Returns
        -------
        p_active : float or nd-array
            The probability of the active state evaluated at each value of
            effector_conc, ka, ki, and n_sites
        """
        c = self.c
        n = self.n
        ka = self.ka
        ki = self.ki
        numer = (1 + c / ka)**n
        denom = numer + np.exp(-self.ep_ai) * (1 + c / ki)**n
        return numer / denom

    def saturation(self):
        R"""
        Computes the probability of the active state in the limit of
        saturating effector concentration.

        Returns
        -------
        saturation : float or nd-array
            Saturation value at each provided value of ka, ki, ep_ai, and
            n_sites.
        """
        ka = self.ka
        ki = self.ki
        ep_ai = self.ep_ai
        n = self.n
        return (1 + np.exp(-ep_ai) * (ka / ki)**n)**-1

    def leakiness(self):
        R"""
        COmputes the probability of the active state in the limit of zero effector.
        """
        return (1 + np.exp(-self.ep_ai))**-1


class SimpleRepression(object):
    R"""
    A base class for simple repression with an allosteric
    repressor.
    """

    def __init__(self, R, ep_r, n_ns=4.6e6, **kwargs):
        R"""
        Instantiate the SimpleRepression object.

        Parameters
        ----------
        R : int, float, or array
            Number of repressors in the system (per cell).
        ep_r : int, float or array
            Repressor-DNA binding energy in units of k_BT.
        n_ns : int or float
            Number of nonspecific DNA binding sites for the
            repressor molecule.
            Default value is the approximate length of the *E.
            coli* genome, 4.6e6 bp.
        **kwargs : dict or tuple
            kwargs for allosteric transcription factors see `MWC`
            documentation for more information.
        """
        # Define the variables.
        self.R = R
        self.ep_r = ep_r
        self.n_ns = n_ns

        # Ensure values make sense.
        positive_args = dict(R=R, n_ns=n_ns)
        for p in positive_args.keys():
            val = positive_args[p]
            if type(val) is float or int:
                val = np.array([val])
            if (val < 0).any():
                raise RuntimeError("{0} must be positive.".format(p))

        # Determine if transcription factor is allosteric
        if kwargs:
            self.allo = True
            self.mwc = MWC(**kwargs)
        else:
            self.allo = False

    def fold_change(self, wpa=True, num_pol=None, ep_pol=None,
                    pact=1):
        R"""
        fold - change for simple repression.

        Parameters
        ----------
        wpa: bool
            If True, the weak promoter approximation is made and the state of
            polymerase being bound to the promoter is ignored.
        num_pol: int, float, or array
            Number of RNA Polymerase units per cell. This is required if
            `wpa == True`.
        ep_pol: int, float, or array
            RNAP - DNA binding energy in units of k_BT. This required if
            `wpa == True`.
        pact : float or array
            The probability of having an active repressor. If None is
            provided, the probability will be computed given effector_conc.

        Returns
        -------
        fold_change: float or nd - array
            Fold - change in gene expression evaluated at each value of c.
        """
        if wpa is not True:
            raise RuntimeError('not yet implemented')

        if self.allo is True:
            pact = self.mwc.pact()
        else:
            if (pact < 0) or (pact > 1):
                raise TypeError('pact must be on the range [0, 1].')
            pact = pact

        # Compute repression and return inverse.
        repression = (1 + pact * self.R / self.n_ns * np.exp(-self.ep_r))
        return repression**-1

    def saturation(self, wpa=True, num_pol=None, ep_pol=0):
        R"""
        Computes the fold - change in gene expression under saturating
        concentrations of effector. This function  is only defined for
        allosteric repressors.

        Parameters
        ----------
        wpa : bool
            If True, the weak promoter approximation will be applied.
        num_pol : int, float, or array
            The number of RNA Polymerase molecules per cell. This is required
            if `wpa == False`.
        ep_pol : int, float, or array
            The RNAP-DNA binding energy in units of k_BT. This is required if
            `wpa == False`
        Returns
        -------
        saturation: float or array
            The leakiness of the simple repression architecture.

        """
        if self.allo is False:
            raise RuntimeError(
                """Saturation is only defined for allosteric molecules. (`allosteric = True`)""")
        pact = self.mwc.saturation()
        return
        # Determine the user provided inputs.
        R = self.R
        n_ns = self.n_ns
        n = self.n
        ep_r = self.ep_r
        ep_ai = ep_ai

        # Compute the pact in limit of c -> inf.
        pact = self.mwc.saturation()
        return fold_change(wpa, num_pol, ep_pol, pact)

    def leakiness(self, wpa=True, num_pol=None, ep_pol=0):
        R"""
        Computes the fold-change in gene expression under a zero concentration
        of effector.

        Parameters
        ----------
        wpa : bool
            If True, the weak promoter approximation will be applied.
        num_pol : int, float, or array
            The number of RNA Polymerase molecules per cell. This is required
            if `wpa == False`.
        ep_pol : int, float, or array
            The RNAP-DNA binding energy in units of k_BT. This is required if
            `wpa == False`
        Returns
        -------
        leakiness: float or array
            The leakiness of the simple repression architecture.
        """
        # Compute the pact in the limit of c -> 0.
        if self.allo is True:
            pact = self.mwc.leakiness()
        else:
            pact = 1
        return fold_change(wpa, num_pol, ep_pol, pact)

    def dynamic_range(self, wpa=True, num_pol=None, ep_pol=0):
        R"""
        The dynamic range of the fold - change in response to an effector
        molecule. This property is only defined for allosteric molecules.

        Parameters
        ----------
        wpa : bool
            If True, the weak promoter approximation will be applied.
        num_pol : int, float, or array
            The number of RNA Polymerase molecules per cell. This is required
            if `wpa == False`.
        ep_pol : int, float, or array
            The RNAP-DNA binding energy in units of k_BT. This is required if
            `wpa == False`
        Returns
        -------
        dynamic_range: float or array
            The leakiness of the simple repression architecture.
        """
        # Compute the saturation and leakiness.
        sat = saturation(wpa, num_pol, ep_pol)
        leak = leakiness(wpa, num_pol, ep_pol)
        return sat - leak

    def ec50(self):

        raise RuntimeError('Not yet implemented.')

    def effective_hill(self):
        raise RuntimeError('Not yet implemented.')

    def bohr_parameter(self):
        R"""
        Computes the Bohr parameter of the form

        bohr = k_BT(log(pact) + log(R / N_ns) + ep_r / k_BT)
        """
        # Compute pact
        if self.allo is True:
            pact = self.mwc.pact()
        else:
            pact = 1
        # Compute and return the Bohr.
        bohr = np.log(pact) + np.log(self.R / self.n_ns) - self.ep_r
        return bohr
