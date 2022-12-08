'''Exceptions raised by antAPI client code'''

class AntAPIClientError(BaseException):
    '''Base class for all antAPI client errors'''

class AntAPIClientAuthError(AntAPIClientError):
    '''Authentication failed'''

class AntAPIClientTracError(AntAPIClientError):
    '''Trac call failed'''
