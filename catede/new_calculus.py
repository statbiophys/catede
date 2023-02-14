#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
    (in development)
    Copyright (C) February 2023 Francesco Camaglia, LPENS 
'''

import warnings
import numpy as np
from scipy import optimize 
from .beta_func_multivar import *

N_SIGMA = 1.5
MAX_ITER = 500
TOL = 1.0e-14
BOUND_DIR = (1.0e-5, 1.0e3)
METHOD='L-BFGS-B'
INIT_GUESS = 1.0
CUTOFFRATIO = 5 # FIXME this can be an option
# Warning : CUTOFFRATIO > 1 
USE_JAC_OPT = True
NUMERICAL_ZERO = 1.0e-14
NUMERICAL_INFTY = 1.0e12

# PRIORS ON THE (2D) DIVERGENCE ESTIMATORS #
_PRIOR_CHOICE = {
    "uniform" : {"use_phi" : True, "extra" : {} },
    "log-uniform" : {"use_phi" : True, "extra" : {"scaling"} },
    "scaled": {"use_phi" : False, "extra" : {"scaling"} },
    }
# FIXME : as it's written, "scaled" should be allowed only for DKL

########################################
#  CONCENTRATION PARAMETER Posterior  #
########################################

class BetaMultivariate_symmDir( ) :
    def __init__( self, a, K ) : 
        '''Multivariate Beta function normalization to symmetric Dirichlet distribution.'''
        self.K = K
        self.x = a
        self.X = K * a
    def log( self ) :
        return self.K * LogGmm( self.x ) - LogGmm( self.X )
    def log_jac( self ) :
        return self.K * diGmm( self.x ) - self.K * diGmm( self.X )
    def log_hess( self ) :
        return self.K * triGmm( self.x ) - np.power(self.K,2) * triGmm( self.X )

class Polya( ) :
    def __init__( self, var, *args ) : 
        '''Polya distribution or symmetric-Dirichlet-multinomial distribution.'''
        self.a = var
        compExp = args[0]
        self.K = compExp.K
        self.x = compExp.nn + self.a
        self.X = compExp.N + self.K * self.a
        self._ffsum = compExp._ffsum
    def log( self ) :
        '''logarithm'''
        def sumGens( x ) : yield LogGmm( x )
        output = self._ffsum( sumGens(self.x), dim=1 ) - LogGmm( self.X ) 
        output -= BetaMultivariate_symmDir( self.a, self.K ).log()                
        return output
    def log_jac( self ) :
        '''1st derivative of the logarithm'''
        def sumGens( x ) : yield diGmm( x )
        output = self._ffsum( sumGens(self.x), dim=1 ) - self.K * diGmm( self.X ) 
        output -= BetaMultivariate_symmDir( self.a, self.K ).log_jac()                   
        return output
    def log_hess( self ) :
        '''2nd derivative of the logarithm'''
        def sumGens( x ) : yield triGmm( x )
        output = self._ffsum( sumGens(self.x), dim=1 ) - np.power(self.K,2) * triGmm( self.X ) 
        output -= BetaMultivariate_symmDir( self.a, self.K ).log_hess()     
        return output

##########################
#  1DIM METAPRIOR TERMS  #
##########################

class _one_dim_metapr() :
    ''' Auxiliary class for transformation factor in determinant of the jacobian.'''
    def logMetapr( self ) :
        '''logarithm of the transformation factor.'''
        return np.log(self.Metapr())
    def logMetapr_jac( self ) :
        '''1st derivative of the logarithm of the transformation factor.'''
        return self.Metapr_jac() / self.Metapr()
    def logMetapr_hess( self ) :
        '''2nd derivative of the logarithm of the transformation factor.'''
        return self.Metapr_hess() / self.Metapr() - np.power(self.logMetapr_jac(),2)

class DirEntr( _one_dim_metapr ) :
    def __init__(self, var, *args) :
        '''Class for ``a priori`` expected Shannon entropy under symmetric Dirichlet prior.'''
        self.a = np.array(var)
        self.K = args[0] 
    def aPrioriExpec( self ) :
        '''``a priori`` expected Shannon entropy.'''
        return D_diGmm( self.K*self.a+1, self.a+1 )
    def Metapr( self ) :
        '''factor of transformation Jacobian determinant (i.e abs of 1st derivative, NSB Metaprior) '''
        return self.K * triGmm( self.K*self.a+1 ) - triGmm( self.a+1 )
    def Metapr_jac( self ) :
        '''1st derivative of the transformation factor.'''
        return np.power( self.K, 2 ) * quadriGmm( self.K*self.a+1 ) - quadriGmm( self.a+1 )
    def Metapr_hess( self ) :
        '''2nd derivative of the transformation factor.'''
        return np.power( self.K, 3 ) * quintiGmm( self.K*self.a+1 ) - quintiGmm( self.a+1 )

class DirSimps( _one_dim_metapr ) :
    def __init__(self, var, *args) :
        '''Class for ``a priori`` expected Simpson index under symmetric Dirichlet prior.'''
        self.a = np.array(var)
        self.K = args[0] 
    def aPrioriExpec( self ) :
        '''``a priori`` expected Simpson index.'''
        return (self.K-1) * np.power( self.K*self.a + 1, -2 )
    def Metapr( self ) :
        '''factor of transformation Jacobian determinant (i.e abs of 1st derivative, NSB Metaprior) '''
        return 2 * self.K * (self.K-1) * np.power( self.K*self.a + 1, -3 )
    def Metapr_jac( self ) :
        '''1st derivative of the transformation factor.'''
        return - 6 * np.power(self.K, 2) * (self.K-1) * np.power( self.K*self.a + 1, -4 )
    def Metapr_hess( self ) :
        '''2nd derivative of the transformation factor.'''
        return 24 * np.power(self.K, 3) * (self.K-1) * np.power( self.K*self.a + 1, -5 )

class equalDirKLdiv( _one_dim_metapr ) :
    def __init__(self, var, *args) :
        '''Class for ``a priori`` expected KL divergence under equal symmetric Dirichlet priors.'''
        self.a = np.array(var)
        self.K = args[0] 
        self._const = (self.K - 1) / self.K
    def aPrioriExpec( self ) :
        '''``a priori`` expected KL divergence.'''
        return self._const * np.power( self.a, -1 )
    def Metapr( self ) :
        '''factor of transformation Jacobian determinant (i.e abs of 1st derivative, NSB Metaprior) '''
        return self._const * np.power( self.a, -2 )
    def Metapr_jac( self ) :
        '''1st derivative of the transformation factor.'''
        return - 2 * self._const * np.power( self.a, -3 )
    def Metapr_hess( self ) :
        '''2nd derivative of the transformation factor.'''
        return 6 * self._const * np.power( self.a, -4 )

class DirCrossEntr( _one_dim_metapr ) :
    def __init__(self, var, *args) :
        '''Class for ``a priori`` expected cross-entropy under symmetric Dirichlet prior.'''
        self.b = np.array(var)
        self.K = args[0] 
    def aPrioriExpec( self ) :
        '''``a priori`` expected cross-entropy.'''
        return D_diGmm( self.K*self.b, self.b )
    def Metapr( self ) :
        '''factor of transformation Jacobian determinant (i.e abs of 1st derivative) '''
        return triGmm(self.b) - self.K * triGmm(self.K*self.b)
    def Metapr_jac( self ) :
        '''1st derivative of the transformation factor.'''
        return quadriGmm(self.b) - np.power(self.K, 2) * quadriGmm(self.K*self.b)
    def Metapr_hess( self ) :
        '''2nd derivative of the transformation factor.'''
        return quintiGmm(self.b) - np.power(self.K, 3) * quintiGmm(self.K*self.b)

###########################
#  2-DIM METAPRIOR TERMS  #
###########################

class _two_dim_metapr( ) :
    ''' Auxiliary class for two dimensional metapriors.'''
    def __init__(self, var, *args, **kwargs ) :
        # note : get around 0-dimensional numpy scalar arrays
        self.a = np.array(var[0]).reshape(-1)
        self.b = np.array(var[1]).reshape(-1)
        self.K, self.choice = args
        self._extra = {}

        if self.choice not in _PRIOR_CHOICE :
            raise IOError(f"unrecognized choice `{self.choice}`.\n Choose amongst: {list(_PRIOR_CHOICE.keys())}")
        else :
            for extra in _PRIOR_CHOICE[self.choice]["extra"] :
                self._extra[extra] = kwargs.get(extra, 1.)
            # Known controls
            if ("scaling" in kwargs) and ("scaling" in _PRIOR_CHOICE[self.choice]["extra"]) :    
                try :
                    self._extra["scaling"] = np.float64(kwargs["scaling"])
                    if self._extra["scaling"] <= 0. :
                        raise ValueError( "The parameter `scaling` should be >0." )
                except :
                    raise TypeError( "The parameter `scaling` should be a scalar." )

    def divPrior( self, output ) :
        '''It returns the prior on the (2dim) a priori expected divrgence, rho(D).'''
        if self.choice in ["scaled"] :
            output *= np.exp( - self._extra["scaling"] * ( self.D / self.class_A.aPrioriExpec() ) )
        elif self.choice in ["uniform"] :
            output[ self.D >= CUTOFFRATIO * np.log(self.K) ] = NUMERICAL_ZERO
            # NOTE : no point in adding the normalization 1. / (CUTOFFRATIO * np.log(self.K))
        elif self.choice in ["log-uniform"] :
            output *= np.power( self.D, - self._extra["scaling"] )    
        return output

    def log_divPrior( self, output ) :
        '''It returns the logarithm of the D prior, log rho(D).'''
        if self.choice in ["scaled"] :
            output += - self._extra["scaling"] * ( self.D / self.class_A.aPrioriExpec() )
        elif self.choice in ["uniform"] :
            output[ self.D >= CUTOFFRATIO * np.log(self.K) ] = - NUMERICAL_INFTY 
            # NOTE CUTOFFRATIO > 1.
        elif self.choice in ["log-uniform"] :
                output += - self._extra["scaling"] * np.log( self.D ) 
        return output

    def log_divPrior_jac( self, output ) :
        '''It returns the gradient of the logarithm of the D prior,.'''
        if self.choice in ["scaled"] :
            A = self.class_A.aPrioriExpec()
            B = self.class_B.aPrioriExpec()
            output[:,0] += self._extra["scaling"] * B * self.class_A.Metapr() * np.power(A, -2)
            output[:,1] += self._extra["scaling"] * self.class_B.Metapr() / A
        elif self.choice in ["uniform"] :
            mask = self.D < np.log(self.K)
            output[ ~mask,: ] = NUMERICAL_ZERO
            output[ self.D >= CUTOFFRATIO * np.log(self.K),: ] = - NUMERICAL_INFTY
        elif self.choice in ["log-uniform"] :
            output[:,0] += self._extra["scaling"] * self.class_A.Metapr() / self.D
            output[:,1] += self._extra["scaling"] * self.class_B.Metapr() / self.D
        return output

    def log_divPrior_hess( self, output ) :
        '''It returns the Hessian of the logarithm of the D prior,.'''
        if self.choice in ["scaled"] :
            A = self.class_A.aPrioriExpec()
            B = self.class_B.aPrioriExpec()
            output[:,0,0] += self._extra["scaling"] * B * ( self.class_A.Metapr_jac() * np.power(A, -2) - 2 * np.power(self.class_A.Metapr(),2) * np.power(A,-3) ) 
            aux_sym = - self._extra["scaling"] * self.class_B.Metapr() * self.class_A.Metapr() * np.power(A, -2)
            output[:,0,1] += aux_sym
            output[:,1,0] += aux_sym
            output[:,1,1] += self._extra["scaling"] * self.class_B.Metapr_jac() / A
        elif self.choice in ["uniform"] :
            mask = self.D < np.log(self.K)
            output[ ~mask,:,: ] = NUMERICAL_ZERO
            output[ self.D >= CUTOFFRATIO * np.log(self.K),:,: ] = - NUMERICAL_INFTY
        elif self.choice in ["log-uniform"] :
            output[:,0,0] += self._extra["scaling"] * self.class_A.Metapr_jac()/self.D + np.power(self.class_A.Metapr()/self.D,2)
            aux_sym = self._extra["scaling"] * self.class_A.Metapr() * self.class_B.Metapr() / np.power(self.D,2)
            output[:,0,1] += aux_sym
            output[:,1,0] += aux_sym
            output[:,1,1] += self._extra["scaling"] * self.class_B.Metapr_jac()/self.D + np.power(self.class_B.Metapr()/self.D,2)
        return output

    def Metapr( self ) :
        ''' Complete Metaprior '''
        output = self.marginaliz_phi( _PRIOR_CHOICE[self.choice]["use_phi"] )
        output = self.divPrior( output )
        output *= self.class_A.Metapr() * self.class_B.Metapr()
        return output

    def logMetapr( self ) :
        ''' logarithm of Metaprior '''
        output = self.log_marginaliz_phi( _PRIOR_CHOICE[self.choice]["use_phi"] )
        output = self.log_divPrior( output )
        output += self.class_A.logMetapr() + self.class_B.logMetapr()
        return output

    def logMetapr_jac( self ) :
        ''' Gradient of the logarihtm of Metaprior '''
        output = self.log_marginaliz_phi_jac( _PRIOR_CHOICE[self.choice]["use_phi"] )
        output = self.log_divPrior_jac( output )
        output[:,0] += self.class_A.logMetapr_jac()
        output[:,1] += self.class_B.logMetapr_jac()
        return output

    def logMetapr_hess( self ) :
        ''' Hessian of the logarihtm of Metaprior '''
        output = self.log_marginaliz_phi_hess( _PRIOR_CHOICE[self.choice]["use_phi"] )
        output = self.log_divPrior_hess( output )
        output[:,0,0] += self.class_A.logMetapr_hess()
        output[:,1,1] += self.class_B.logMetapr_hess()
        return output

#############################
#  KL DIVERGEMCE METAPRIOR  #
#############################

class DirKLdiv( _two_dim_metapr ) :
    def __init__(self, var, *args, **kwargs ) :
        _two_dim_metapr.__init__(self, var, *args, **kwargs)
        self.class_A = DirEntr(self.a, self.K)
        self.class_B = DirCrossEntr(self.b, self.K)
        self.D = self.class_B.aPrioriExpec() - self.class_A.aPrioriExpec()

    def marginaliz_phi( self, use_phi ) :
        output = np.ones( shape = (self.D.size,) )
        if use_phi is True :
            mask = self.D < np.log(self.K)
            output[ mask ] /= self.D[ mask ]
            output[ ~mask ] /= np.log(self.K)
        return output

    def log_marginaliz_phi( self, use_phi ) :
        output = np.zeros( shape = (self.D.size,) )
        if use_phi is True :
            mask = self.D < np.log(self.K) 
            output[ mask ] = - np.log( self.D[mask] )
            output[ ~mask ] = - np.log( np.log(self.K ))
        return output

    def log_marginaliz_phi_jac( self, use_phi ) : 
        output = np.zeros( shape = (self.D.size, 2,) )
        if use_phi is True :
            mask = self.D < np.log(self.K)
            output[mask,0] = self.class_A.Metapr() / self.D[mask]
            output[mask,1] = self.class_B.Metapr() / self.D[mask]
        return output

    def log_marginaliz_phi_hess( self, use_phi ) : 
        output = np.zeros( shape = (self.D.size, 2, 2,) )
        if use_phi is True :
            mask = self.D < np.log(self.K)
            output[mask,0,0] = self.class_A.Metapr_jac() / self.D[mask] + np.power( self.class_A.Metapr() / self.D[mask], 2 )
            output[mask,0,1] = self.class_A.Metapr() * self.class_B.Metapr() / np.power( self.D[mask], 2 )
            output[mask,1,0] = output[mask,0,1]
            output[mask,1,1] = self.class_B.Metapr_jac() / self.D[mask] + np.power( self.class_B.Metapr() / self.D[mask], 2 )
        return output

####################################
#  HELLINGER DIVERGENCE METAPRIOR  #
####################################

class DirHelldiv( _two_dim_metapr ) :
    def __init__(self, var, *args, **kwargs ) :
        _two_dim_metapr.__init__(self, var, *args, **kwargs)
        self.class_A = DirEntr(self.a, self.K)
        self.class_B = DirCrossEntr(self.b, self.K)
        self.D = self.K * self.class_B.aPrioriExpec() * self.class_A.aPrioriExpec()

        # FIXME
        raise SystemError("this object needs to be coded.")

    def marginaliz_phi( self, use_phi ) :
        output = np.ones( shape = (self.D.size,) )
        if use_phi is True :
            mask = self.D < np.log(self.K)
            output[ mask ] /= self.D[ mask ]
            output[ ~mask ] /= np.log(self.K)
        return output

    def log_marginaliz_phi( self, use_phi ) :
        output = np.zeros( shape = (self.D.size,) )
        if use_phi is True :
            mask = self.D < np.log(self.K) 
            output[ mask ] = - np.log( self.D[mask] )
            output[ ~mask ] = - np.log( np.log(self.K ))
        return output

    def log_marginaliz_phi_jac( self, use_phi ) : 
        output = np.zeros( shape = (self.D.size, 2,) )
        if use_phi is True :
            mask = self.D < np.log(self.K)
            output[mask,0] = self.class_A.Metapr() / self.D[mask]
            output[mask,1] = self.class_B.Metapr() / self.D[mask]
        return output

    def log_marginaliz_phi_hess( self, use_phi ) : 
        output = np.zeros( shape = (self.D.size, 2, 2,) )
        if use_phi is True :
            mask = self.D < np.log(self.K)
            output[mask,0,0] = self.class_A.Metapr_jac() / self.D[mask] + np.power( self.class_A.Metapr() / self.D[mask], 2 )
            output[mask,0,1] = self.class_A.Metapr() * self.class_B.Metapr() / np.power( self.D[mask], 2 )
            output[mask,1,0] = output[mask,0,1]
            output[mask,1,1] = self.class_B.Metapr_jac() / self.D[mask] + np.power( self.class_B.Metapr() / self.D[mask], 2 )
        return output

# <<<<<<<<<<<<<<<<<<<<<<
#  MAXIMUM POSTERIOIR  #
# >>>>>>>>>>>>>>>>>>>>>> 

def myMinimizer( myfunc, var, args, jac=None ) :
    '''General minimization wrapper for `myfunc`.'''
    
    if USE_JAC_OPT is False : jac = None
    results = optimize.minimize(
        myfunc,
        x0=var, args=args,
        jac=jac,
        method=METHOD, bounds=(BOUND_DIR,)*len(var), 
        options={'maxiter': MAX_ITER}, tol=TOL
        )
    if np.any( [ np.any( np.isclose( x, BOUND_DIR, atol=TOL )) for x in results.x ] ) :
        warnings.warn("The optimal parameter(s) saturated to the boundary.")
    return results.x

# one dim

def optimal_dirichlet_param( compExp ) :
    '''.'''
    def myfunc( var, *args ) :
        LogLike = Polya(var, *args).log()
        return - LogLike
    def myjac(var, *args) :
        jac_LogLike = Polya(var, *args).log_jac()
        return - jac_LogLike 
    return myMinimizer( myfunc, [INIT_GUESS], (compExp,), jac=myjac )

def optimal_entropy_param( compExp ) :
    '''.'''
    def myfunc(var, *args) :
        LogLike = DirEntr(var, args[0].K).logMetapr()
        LogLike += Polya(var, *args).log()
        return - LogLike
    def myjac(var, *args) :
        jac_LogLike = DirEntr(var, args[0].K).logMetapr_jac()
        jac_LogLike += Polya(var, *args).log_jac()
        return - jac_LogLike
    return myMinimizer( myfunc, [INIT_GUESS], (compExp,), jac=myjac )

def optimal_crossentropy_param( compExp ) :
    '''(obsolete)''' 
    def myfunc(var, *args) :
        LogLike = DirCrossEntr(var, args[0].K).logMetapr()
        LogLike += Polya(var, *args).log()
        return - LogLike
    def myjac(var, *args) :
        jac_LogLike = DirCrossEntr(var, args[0].K).logMetapr_jac()
        jac_LogLike += Polya(var, *args).log_jac()
        return - jac_LogLike
    return myMinimizer( myfunc, [INIT_GUESS], (compExp,), jac=myjac )

def optimal_simpson_param( compExp ) :
    '''.'''
    def myfunc(var, *args) :
        LogLike = DirSimps(var, args[0].K).logMetapr()
        LogLike += Polya(var, *args).log()
        return - LogLike
    def myjac(var, *args) :
        jac_LogLike = DirSimps(var, args[0].K).logMetapr_jac()
        jac_LogLike += Polya(var, *args).log_jac()
        return - jac_LogLike
    return myMinimizer( myfunc, [INIT_GUESS], (compExp,), jac=myjac )

def optimal_equal_KLdiv_param( compDiv ) :
    '''.''' 
    def myfunc(var, *args) :
        LogLike = equalDirKLdiv(var, args[0].K).logMetapr()
        LogLike += Polya(var, args[0].compact_1).log()
        LogLike += Polya(var, args[0].compact_2).log()
        return - LogLike
    def myjac(var, *args) :
        jac_LogLike = equalDirKLdiv(var, args[0].K).logMetapr_jac()
        jac_LogLike += Polya(var, args[0].compact_1).log_jac()
        jac_LogLike += Polya(var, args[0].compact_2).log_jac()
        return - jac_LogLike
    return myMinimizer( myfunc, [INIT_GUESS], (compDiv,), jac=myjac )

# two dim

def optimal_KL_divergence_params( compDiv, choice="log-uniform", **kwargs ) :
    '''.'''
    def myfunc(var, *args) :
        LogLike = DirKLdiv(var, args[0].K, args[1], ** args[2] ).logMetapr()
        LogLike += Polya(var[0], args[0].compact_1).log()
        LogLike += Polya(var[1], args[0].compact_2).log()
        return - LogLike
    def myjac(var, *args) :
        jac_LogLike = DirKLdiv(var, args[0].K, args[1], ** args[2]).logMetapr_jac()
        jac_LogLike[:,0] += Polya(var[0], args[0].compact_1).log_jac()
        jac_LogLike[:,1] += Polya(var[1], args[0].compact_2).log_jac()
        return - jac_LogLike
    return myMinimizer( myfunc, [INIT_GUESS,INIT_GUESS], (compDiv, choice, kwargs), jac=myjac )

def optimal_Hellinger_params( compDiv, choice="log-uniform", **kwargs ) :
    '''.'''
    def myfunc(var, *args) :
        LogLike = DirHelldiv(var, args[0].K, args[1], ** args[2] ).logMetapr()
        LogLike += Polya(var[0], args[0].compact_1).log()
        LogLike += Polya(var[1], args[0].compact_2).log()
        return - LogLike
    def myjac(var, *args) :
        jac_LogLike = DirHelldiv(var, args[0].K, args[1], ** args[2]).logMetapr_jac()
        jac_LogLike[:,0] += Polya(var[0], args[0].compact_1).log_jac()
        jac_LogLike[:,1] += Polya(var[1], args[0].compact_2).log_jac()
        return - jac_LogLike
    return myMinimizer( myfunc, [INIT_GUESS,INIT_GUESS], (compDiv, choice, kwargs), jac=myjac )

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
#   POSTERIOR STANDARD DEVIATION  #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

def empirical_n_bins( size, categories ) :
    '''Empirical choice for the number of bins.'''
    n_bins = max( 1, np.round(10 * np.power(categories / size, 2)) )
    n_bins = min( int(n_bins), 200 ) 
    return n_bins

def centered_logspaced_binning( loc, std, n_bins ) :
    '''.'''
    output = np.append(
        np.logspace( min(BOUND_DIR[0], np.log10(loc-N_SIGMA*std)), np.log10(loc), n_bins//2 )[:-1],
        np.logspace( np.log10(loc), np.log10(loc+N_SIGMA*std), n_bins//2+1 )
        )
    return output

def log_equal_KLdiv_meta_posterior_hess( var, *args ) :
    '''.'''
    hess_LogLike = equalDirKLdiv(var, args[0].K).logMetapr_hess()
    hess_LogLike += Polya(var, args[0].compact_1).log_hess() 
    hess_LogLike += Polya(var, args[0].compact_2).log_hess() 
    return hess_LogLike

def log_KL_divergence_meta_posterior_hess( var, *args ) :
    '''.'''
    hess_LogLike = DirKLdiv(var, args[0].K, args[1], ** args[2] ).logMetapr_hess()
    hess_LogLike[:,0,0] += Polya(var[0], args[0].compact_1).log_hess()
    hess_LogLike[:,1,1] += Polya(var[1], args[0].compact_2).log_hess() 
    return hess_LogLike
    

# -----------------------------------   

# IN DEVELOPMENT
# SIMPSON, EQUAL PRIOR

# -----------------------------------

'''

def prior_simpson_vs_alpha_( alpha, K ):
    Expected Simpson for Dirichlet distribution.
    return (alpha + 1) / (K * alpha + 1)

def prior_bhattacharrya_( alpha, beta, K ) :
    A priori expected Bhattacharrya under symmetricDirichlet Mixture.
    return K * (beta_func(0.5,K*alpha)/beta_func(0.5,alpha)) * (beta_func(0.5,K*beta)/beta_func(0.5,beta))

def optimal_simpson_param_( compExp ) :
    def myfunc(var, *args) :
        alpha = var
        compExp = args[0]
        K = compExp.K
        metaprior = (K-1) / np.power( K*alpha + 1, 2 )
        Like = log_alphaPosterior(var, *args) + np.log(metaprior)
        return - Like
    return myMinimizer( myfunc, [INIT_GUESS], (compExp,) )

def optimal_dirichlet_EP_param_( compDiv ) :
    def myfunc( var, *args ) :
        compExp_1, compExp_2, = args[0].compact_1,  args[0].compact_2
        Like = log_alphaPosterior(var, (compExp_1,)) + log_alphaPosterior(var, (compExp_2,))
        return - Like
    return myMinimizer( myfunc, [INIT_GUESS], (compDiv,) )

def optimal_divergence_EP_param_( compDiv ) :
    def myfunc( var, *args ) :
        compExp_1, compExp_2, = args[0].compact_1,  args[0].compact_2
        K = args[0].K
        logMetaprior = np.log( ( 1. - 1. / K ) / var**2 )
        Like = log_alphaPosterior(var, (compExp_1,)) + log_alphaPosterior(var, (compExp_2,)) + logMetaprior
        return - Like
    return myMinimizer( myfunc, [INIT_GUESS], (compDiv,) )
'''