'''RELP client library'''

from socket import socket, AF_INET, SOCK_STREAM
from queue import Queue

from relp.session import *

class RelpClient:
    '''Object to manage a client connection'''
    def __init__(self, address, port, logger=None):
        sock = socket(AF_INET, SOCK_STREAM)
        sock.connect((address, port))

        self.recv_queue = Queue()
        self.send_queue = Queue()

        self.session = RelpSession(sock)

        self.running = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    def start(self):
        '''Start the client'''
        self.running = True
        self.session.start()
        self.session.offer()

        while self.running:
            frame = self.session.recv()
            if frame.command == 'serverclose':
                self.stop()
                break
            else:
                raise NotImplementedError(f"Client does not implement command `{frame.command}`")

    def stop(self):
        '''Stop the client'''
        self.running = False
        self.session.stop()

    def syslog(self, message: str):
        '''Send a syslog message in RELP'''
        if self.running:
            self.session.send('syslog', message)
        else:
            Exception("Cannot send message while RELP session is closing")
