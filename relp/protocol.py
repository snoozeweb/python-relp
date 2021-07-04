'''Module for parsing and producing RELP frames'''

import logging
import re
import sys

from collections import namedtuple
from enum import Enum

from relp.exceptions import *

default_logger = logging.getLogger('relp-protocol')
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

VERSION = '0'
SOFTWARE = 'python-relp'
COMMANDS = ['syslog']

class Frame:
    '''Define a RELP frame'''
    logger = default_logger

    def __init__(self, txnr: int, command: str, message: str):
        self.txnr = txnr
        self.command = command
        self.message = message

    def encode(self):
        '''Create a RELP message frame'''
        return f"{self.txnr} {self.command} {len(self.message)} {self.message}\n"

    def __repr__(self):
        return 'Frame[' + repr(self.encode()).strip("'") + ']'

    @classmethod
    def decode(cls, data: str):
        '''
        Parse a frame to extract the information.
        Return a tuple with the frame and a remaining.
        '''
        txnr, command, length, message = data.split(' ', 3)
        validate_frame(txnr, command, length, message)
        txnr = int(txnr)
        message = message.rstrip('\n')
        return Frame(txnr, command, message)

    @classmethod
    def decode_batch(cls, data: str):
        '''
        Parse a batch of RELP frames
        '''
        frames = []
        while data:
            cls.logger.debug("Working on data: %s", repr(data))
            try:
                txnr, command, length, remain = data.split(' ', 3)
                txnr = int(txnr)
                length = int(length)

                if len(remain) >= length:
                    data = remain
                    message, data = data[:length], data[length:]
                    frame = Frame(txnr, command, message)
                    cls.logger.debug("Unpacked %s", frame)
                    frames.append(frame)
                else:
                    return frames, data

                if data[0] == '\n':
                    data = data[1:]
                    continue
                else:
                    raise RelpProtocolError(f"Message should be terminated with \\n, received: {data[0]}")
            except Exception as err:
                raise err
        return frames, ''

class RspCode(Enum):
    '''Enum for rsp message code'''
    ACK = 200
    NACK = 500

class Ack:
    '''Ack message in RELP'''
    def __init__(self, txnr: int, code: RspCode = RspCode.ACK, message: str = 'OK'):
        self.txnr = txnr
        self.code = code
        self.message = message

    def to_frame(self):
        '''Create a Frame object from an Ack'''
        return Frame(self.txnr, 'rsp', f"{self.code.value} {self.message}")

    @staticmethod
    def from_frame(frame):
        '''Create an ACK object from a Frame object'''
        code, message = frame.message.split(' ', 2)
        code = int(code)
        return Ack(frame.txnr, code, message)

class Offer:
    '''RELP offer'''
    def __init__(self, version=VERSION, software=SOFTWARE, commands=','.join(COMMANDS)):
        self.version = version
        self.software = software
        self.commands = commands

    def message(self):
        message = '\n'.join([
            f"relp_version={self.version}",
            f"relp_software={self.software}",
            f"commands={self.commands}",
        ])
        return message

    def to_frame(self, txnr):
        '''Transform the generic offer into a Frame'''
        return Frame(txnr, 'open', self.message())

    @staticmethod
    def from_frame(frame):
        '''Create an Offer object from a Frame'''
        header_dict = {}
        _, *headers = frame.message.split('\n')
        for header in headers:
            key, value = header.split('=', 2)
            header_dict[key] = value
        return Offer(
            header_dict.get('relp_version'),
            header_dict.get('relp_software'),
            header_dict.get('commands').split(','),
        )

def parse_frame(data):
    '''
    Parse a frame to extract the information.
    Return a tuple with the frame and a remaining.
    '''
    txnr, command, length, message = data.split(' ', 4)

    if command == 'rsp':
        code, ack_msg = message.split(' ', 2)
        if code == '200':
            return Ack(txnr)
        elif code == '500':
            return NAck(txnr, ack_msg)
        else:
            raise RelpProtocolError(f"Unsupported rsp code: '{code}'.")
    else:
        validate_frame(txnr, command, length, message)
        return Frame(txnr, command, message)

def validate_frame(txnr, command, length, message):
    '''Validate the RELP frame is matching the protocol'''
    try:
        txnr = int(txnr)
    except ValueError:
        raise RelpProtocolError(f"TXNR is not an integer: '{txnr}'")
    try:
        length = int(length)
    except ValueError:
        raise RelpProtocolError(f"Length of message is not an integer: '{txnr}'")
    if not re.fullmatch(r"[a-zA-Z]{1,32}", command):
        raise RelpProtocolError(f"Command only support alphanumerics, received: `{command}`")
    if length != len(message):
        raise RelpProtocolError(f"Got {len(message)} bytes of data, expected {length}")

def encode_frame(frame):
    '''
    Create a RELP message frame
    '''
    return f"{frame.txnr} {frame.command} {len(frame.message)} {frame.message}"

def ack_frame(txnr):
    '''
    Create a RELP ACK frame
    '''
    return Frame(txnr, 'rsp', '200 OK')

def nack_frame(txnr, message):
    '''
    Create a RELP NACK frame
    '''
    return Frame(txnr, 'rsp', f"500 {message}")

def ack_offer_frame(txnr):
    '''ACK an offer command'''
    message = '200 OK\n' + offer_header()
    return Ack(txnr, message)
