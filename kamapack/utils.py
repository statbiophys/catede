'''
Common system commands.
'''

import os, sys
import operator
import functools


###############
#  FILESCOPE  #
###############

class fileScope:
    '''
    A class to extract all possible file informations from string .
    '''
    def __init__( self, fileName ):

        fileName=str(fileName)
        
        # check wheter compressed
        if fileName.endswith('.gz'): 
            self.compression = 'gzip'
            self.ext = ".gz"
        elif fileName.endswith('.zip'): 
            self.compression ='zip'
            self.ext = ".zip"
        else:
            self.compression = None
            self.ext = ""

        # check non-compressed file extension
        if fileName.endswith( '.tsv' + self.ext ):
            self.ext = '.tsv' + self.ext
            self.delimiter = '\t'
            self.header = 0
        elif fileName.endswith( '.csv' + self.ext ):  
            self.ext = '.csv' + self.ext
            self.delimiter = ','
            self.header = 0
        elif fileName.endswith( '.data' + self.ext ):  
            self.ext = '.data' + self.ext
            self.delimiter = ' '
            self.header = 0
        elif fileName.endswith( '.txt' + self.ext ):
            self.ext = '.txt' + self.ext
            self.delimiter = ';'
            self.header = None
        else :
            raise IOError("Input file extension not recognized: please provide a delimiter.")
###



################
#  REDUCELIST  #
################

def reduceList( ListOfLists ):
    '''
    To transform a list of sub-lists in a single list containing the elements of the non-empty sub-lists.
    e.g. 
    ----
    ListOfLists = [ [ 2, 4 ], [ ], [ "A", "G" ] ]
    returns : [ 2, 4, "A", "G" ]
    '''
    
    types = set(list(map(lambda x : type(x),  ListOfLists ) ) )
    if list not in types :
        # nothing to do in this case
        return ListOfLists
    elif types == {list} :
        return functools.reduce( operator.iconcat, ListOfLists, [] )
    else :
        raise TypeError('Impossible to reduce this kind of list.')
###



################
#  TRYMAKEDIR  #
################

def tryMakeDir( path_choice ):
    # create a directory
    if not os.path.exists( path_choice ):
        try: 
            os.makedirs( path_choice, mode=0o777, exist_ok=True ) 
        except OSError as error: 
            print(error)
    else :
        pass
        #print('The folder "' + path_choice + '" already exists: directory creation ignored.'  )
###

'''
Utils Module:
Francesco Camaglia, LPENS February 2020
'''

from itertools import groupby

####################
#  DICT_GENERATOR  #
####################

def dict_generator( sequences ):
    '''
    It reads the received list of sequences (or it cast it to a list) and returns
    the dictionary of recurrency per sequence. 
    '''
    
    sequences = reduceList(list( sequences ))
    sequences.sort()
    # counting repetitions through grupby
    seq_dict = { key : len( list( group ) ) for key, group in groupby( sequences ) }
    
    return seq_dict
###


####################
#  HIST_GENERATOR  #
####################

def hist_generator( sequences ):
    '''
    It reads the received list of sequences (or it cast it to a list) and returns
    the vector of recurrencies
    '''
     
    seq_dict = dict_generator( sequences )    
    # Note: this array's order is meaningless (sequences alphabetically ordered)
    observations = list( seq_dict.values() )
    
    return observations
###
