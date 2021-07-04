'''Module containing the custom exceptions'''

class RelpProtocolError(RuntimeError):
    '''
    Exceptions due to the RELP protocol related to parsing and packing
    '''

class RelpSessionError(RuntimeError):
    '''
    Raised when there is an issue with messages
    that are received but unexpected.
    '''

class AckError(RuntimeError):
    '''
    Raised when an message sent received a NACK.
    '''
