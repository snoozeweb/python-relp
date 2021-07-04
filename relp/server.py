'''A RELP TCP server'''

import logging
import ssl
import sys

from socketserver import TCPServer, StreamRequestHandler
from socket import socket, AF_INET, SOCK_STREAM

from concurrent.futures import ThreadPoolExecutor
from threading import Thread

from relp.protocol import *
from relp.session import RelpSession

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
default_logger = logging.getLogger('relp-server')

def handle_client(clientsocket, address, handler, logger):
    '''Handler for RELP session for server'''
    logger.debug("Handling client connection")
    logger.info("Starting RELP session with %s", address)
    with RelpSession(clientsocket, 'server', logger) as session:
        try:
            while True:
                logger.debug("Waiting for messages")
                frame = session.recv()
                if frame.command == 'syslog':
                    logger.debug("Handling frame: %s", frame)
                    handler(frame.message)
                elif frame.command == 'open':
                    logger.info("Offered received and processed")
                elif frame.command == 'close':
                    logger.info("Received `close` from client. Stopping the server")
                    break
                else:
                    raise RelpSessionError(f"Unexpected RELP command: {frame.command}")
        except Exception as err:
            raise err
        finally:
            # Hint for client to close the RELP socket
            frame = Frame(0, 'serverclose', '')
            session.send_frame(frame)
    logger.debug('Stopping client handler for %s', address)

class RelpServer:
    '''RELP server'''
    def __init__(self, listen_addr, port, handler, logger=default_logger):
        self.handler = handler
        self.logger = logger

        self.client_threads = []

        # Starting socket
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.bind((listen_addr, port))
        self.socket.listen()

        self.main_thread = Thread(target=self._listener)

    def start(self):
        '''Start the RELP server in a different thread and return'''
        self.main_thread.start()

    def stop(self):
        '''Stop the RELP server'''
        pass

    def _listener(self):
        self.logger.info("Starting listening for client connections")
        try:
            with ThreadPoolExecutor() as threadpool:
                while True:
                    clientsocket, address = self.socket.accept()
                    self.logger.debug("New connection from %s", address)
                    threadpool.submit(handle_client, clientsocket, address, self.handler, self.logger)
        except Exception as e:
            raise e

    def serve_forever(self):
        '''Accept and serve RELP connections forever'''
        self.start()
        self.main_thread.join()
