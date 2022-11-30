#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
    *** Default Divergence ***
    Copyright (C) October 2022 Francesco Camaglia, LPENS 
'''

import warnings
import numpy as np 
from .cmw_KullbackLeibler import Kullback_Leibler_CMW
from .default_entropy import _unit_Dict_, Shannon_oper
from .new_calculus import optimal_dirichlet_param_
from scipy.special import rel_entr

_method_List_ = [
    "naive", "maximum-likelihood",
    "CMW", "Camaglia-Mora-Walczak",
    "D", "Dirichlet", 
    "J", "Jeffreys", "Krichevsky-Trofimov", 
    "L", "Laplace", 
    "mm", "minimax", "Trybula", 
    "SG", "Schurmann-Grassberger",
]

_which_List_ = ["Hellinger", "Jensen-Shannon", "Kullback-Leibler"]

#############
#  ALIASES  #
#############

def KullbackLeibler_oper( x, y ) :
    ''' x * log(x/y) '''
    return rel_entr(x,y)

def JensenShannon_oper( x, y ) :
    ''' '''
    mm = 0.5 * ( x + y )
    return 0.5 * ( KullbackLeibler_oper( x, mm ) + KullbackLeibler_oper( y, mm ) )

def Bhattacharyya_oper( x, y ) :
    ''' sqrt( x * y ) '''
    return np.sqrt( np.multiply( x, y ) ) 

#################
#  SWITCHBOARD  #
#################

def switchboard( compACT, method="naive", which="Kullback-Leibler", unit="default", **kwargs ):

    # check which 
    if which not in _which_List_ :
        raise IOError("Unkown divergence. Please choose `which` amongst :", _which_List_ )
    
    # loading units
    if which in ["Jensen-Shannon", "Kullback-Leibler"] :
        if unit not in _unit_Dict_.keys( ) :
            warnings.warn( "Please choose `unit` amongst :", _unit_Dict_.keys( ), ". Falling back to default." )
        unit_conv = _unit_Dict_.get( unit, _unit_Dict_["default"] )
    else :
        unit_conv = 1
        
    # choosing entropy estimation method
    if method in ["naive", "maximum-likelihood"] :  
        dkl_estimate = Naive( compACT, which=which, **kwargs )
    
    elif method in ["CMW", "Camaglia-Mora-Walczak"] :       
        if which in ["Jensen-Shannon"] :
            raise IOError("Unknown method `CMW` for the chosen divergence.")
        elif which == "Kullback-Leibler" :
            dkl_estimate = Kullback_Leibler_CMW( compACT, **kwargs )
        elif which == "Hellinger" :
            raise IOError("FIXME: place holder.")

    elif method in ["D", "Dirichlet"] :
        a = kwargs.get("a", None)
        b = kwargs.get("b", None)
        
        if a is None :
            a = "optimal"
            #warnings.warn("Dirichlet parameter `a` falling back to `optimal`.")
        if b is None :
            b = "optimal"
            #warnings.warn("Dirichlet parameter `b` falling back to `optimal`.")

        dkl_estimate = Dirichlet( compACT, a, b, which=which )       
    
    elif method in ["J", "Jeffreys", "Krichevsky-Trofimov"] :
        a = 0.5
        b = 0.5
        dkl_estimate = Dirichlet( compACT, a, b, which=which )
    
    elif method in ["L", "Laplace", "Bayesian-Laplace"] :
        a = 1.
        b = 1.
        dkl_estimate = Dirichlet( compACT, a, b, which=which )
        
    elif method in ["mm", "minimax", "Trybula"]:  
        a = np.sqrt( compACT.N_1 ) / compACT.compact_1.K
        b = np.sqrt( compACT.N_2 ) / compACT.compact_2.K
        dkl_estimate = Dirichlet( compACT, a, b, which=which )
     
    elif method in ["SG", "Schurmann-Grassberger"]:
        a = 1. / compACT.compact_1.Kobs
        b = 1. / compACT.compact_2.Kobs
        dkl_estimate = Dirichlet( compACT, a, b, which=which )

    else:
        raise IOError("Unkown method. Please choose `method` amongst :", _method_List_ )

    return unit_conv * dkl_estimate
###

###########
#  NAIVE  #
###########

def Naive( compACT, which="Kullback-Leibler", **kwargs) :
    '''Estimation of divergence with frequencies of observed categories.'''
    
    # loading parameters from compACT 
    N_1, N_2 = compACT.N_1, compACT.N_2
    # delete 0 counts
    gtr0mask = np.logical_and( compACT.nn_1 > 0, compACT.nn_2 > 0 )
    nn_1, nn_2, ff = compACT.nn_1[gtr0mask], compACT.nn_2[gtr0mask], compACT.ff[gtr0mask]
    
    hh_1 = nn_1 / N_1                  # frequencies
    hh_2 = nn_2 / N_2                  # frequencies
    
    if which == "Jensen-Shannon" :
        output = np.dot( ff, JensenShannon_oper( hh_1, hh_2 ) )

    elif which == "Kullback-Leibler" :                       
        output = np.dot( ff, KullbackLeibler_oper( hh_1, hh_2 ) )

    elif which == "Hellinger" :  
        output = np.sqrt( 1 - np.dot( ff, Bhattacharyya_oper( hh_1, hh_2 ) ) )

    else :
        raise IOError("Unknown method `Naive` for the chosen divergence.")

    return np.array( output )

##########################
#  DIRICHELET ESTIMATOR  #
##########################

def Dirichlet( compACT, a, b, which="Kullback-Leibler", **kwargs ):
    '''Estimation of divergence with Dirichlet-multinomial pseudocount model.
    '''
    # check options
    if a == "optimal" :
        a = optimal_dirichlet_param_(compACT.compact_1)
    else :
        try:
            a = np.float64(a)
        except :
            raise IOError('The concentration parameter `a` must be a scalar.')
        if a < 0 :
            raise IOError('The concentration parameter `a` must greater than 0.')

    if b == "optimal" :
        b = optimal_dirichlet_param_(compACT.compact_2)
    else :
        try:
            b = np.float64(b)
        except :
            raise IOError('The concentration parameter `b` must be a scalar.')
        if b < 0 :
            raise IOError('The concentration parameter `b` must greater than 0.')

    # loading parameters from compACT 
    N_1, N_2, K = compACT.N_1, compACT.N_2, compACT.K
    nn_1, nn_2, ff = compACT.nn_1, compACT.nn_2, compACT.ff

    hh_1_a = ( nn_1 + a ) / ( N_1 + K*a )     # frequencies with pseudocounts
    hh_2_b = ( nn_2 + b ) / ( N_2 + K*b )     # frequencies with pseudocounts

    if which == "Jensen-Shannon" :
        output = np.dot( ff, JensenShannon_oper( hh_1_a, hh_2_b ) )

    elif which == "Kullback-Leibler" :                               
        output = np.dot( ff, KullbackLeibler_oper( hh_1_a, hh_2_b ) )

    elif which == "Hellinger" :  
        output = np.sqrt( 1 - np.dot( ff, Bhattacharyya_oper( hh_1_a, hh_2_b ) ) )

    else :
        raise IOError("Unknown method `Dirichlet` for the chosen quantity.")

    return np.array( output )
###
