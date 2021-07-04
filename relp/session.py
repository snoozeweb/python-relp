'''Manage a RELP session'''

import logging
import sys

from threading import Event, Thread
from queue import Queue

from relp.protocol import *
from relp.exceptions import *

from socket import SHUT_RD, SHUT_RDWR

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
default_logger = logging.getLogger('relp-session')

class AckManager():
    '''
    Manage ACK between threads and allow to wait
    for a specific ACK number to arrive.
    '''
    default_logger = logging.getLogger('AckManager')

    def __init__(self, logger=default_logger):
        self.events = {}
        self.values = {}
        self.logger = logger
        self.logger.debug("Created AckManager object")

    def prepare(self, key):
        '''
        Prepare a future get
        '''
        if key in self.events:
            raise Exception(f"Another process is already waiting for ACK {key}")
        event = Event()
        self.events[key] = event
        return event

    def get(self, key, timeout=None):
        '''
        Wait for an ACK to be received.
        '''
        event = self.events.get(key) or self.prepare(key)
        self.logger.debug("[get/%s] Waiting for event to be triggered", key)
        event.wait(timeout)
        value = self.values.pop(key)
        return value

    def put(self, key, value):
        '''
        Insert a new key in the ACK manager.
        '''
        self.values[key] = value
        self.logger.debug("[put/%s] Put value %s", key, value)
        event = self.events.get(key)
        if not event:
            self.logger.error("Could not find event for key %s, (%s)", key, type(key))
            raise Exception(f"Could not find event for key {key}")

        self.logger.debug("[put/%s] Triggering event", key)
        event.set()
        self.logger.debug("[put/%s] Set the event to trigger `get`", key)

    def size(self):
        '''Return the number of ACK that are expected'''
        return len(self.events)

class RelpSession:
    '''
    A RELP session object that uses a socket to communicate with a client.
    Expose `send` and `recv` methods for communications, while the acknowledgments
    and session setup are handled by this class.
    '''
    def __init__(self, socket, mode, logger=default_logger):
        self.socket = socket
        self.logger = logger
        self.mode = mode
        self.txnr = 1
        self.running = False
        self.send_queue = Queue()
        self.recv_queue = Queue()
        self.ackmanager = AckManager()
        self.send_thread = Thread(target=self._sender, daemon=True)
        self.recv_thread = Thread(target=self._receiver, daemon=True)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, etype, evalue, traceback):
        self.logger.debug("Exiting RELP session from `with`")
        self.logger.debug("%s|%s|%s", etype, evalue, traceback)
        self.stop()

    def start(self):
        '''Start the RELP session'''
        self.logger.info("Starting RELP session")
        self.running = True
        self.send_thread.start()
        self.recv_thread.start()

    def stop(self):
        '''Stop the session'''
        self.logger.info("Stopping RELP session")

        if self.mode == 'server':
            self.send('close')
        elif self.mode == 'client':
            serverclose = Frame(0, 'serverclose', '')
            self.send_frame(serverclose)

        self.running = False
        self.logger.debug("Shutting down the socket")
        self.socket.shutdown(SHUT_RDWR)

        self.logger.debug("Waiting for receiver to stop")
        self.recv_thread.join()
        self.logger.debug("Waiting for sender to stop")
        self.send_queue.put(None)
        self.send_thread.join()

        self.logger.debug("Closing the socket")
        self.socket.close()

    def offer(self):
        '''Do the RELP offer at the start and parse the response'''
        self.logger.info("Executing RELP OFFER")
        offer = Offer()
        self.logger.debug("Offer sent: %s", offer)
        frame = offer.to_frame(self.txnr)
        try:
            self.logger.debug("Sending offer, waiting for reply...")
            self.send('open', frame.message)
        except Exception as err:
            raise Exception(f"Error during RELP offer: {err}")
        self.logger.debug("Received offer reply. Offer successful")

    def _handle_frame(self, frame):
        self.logger.debug("Received frame: %s", frame)

        # ACK and NACK
        if frame.command == 'rsp':
            ack = Ack.from_frame(frame)
            self.ackmanager.put(ack.txnr, ack)

        # Supported commands
        elif frame.command in ['close'] + COMMANDS:
            self._ack(frame.txnr)
            self.recv_queue.put(frame)

        elif frame.command == 'open':
            self._ack_offer(frame.txnr)
            self.recv_queue.put(frame)

        elif frame.command == 'close':
            if self.mode == 'server':
                self._ack(frame.txnr)
                self.stop()
            else:
                raise NotImplementedError(f"Received `close` command while running session in {self.mode} mode")

        elif frame.command == 'serverclose':
            if self.mode == 'client':
                self.stop()
            else:
                raise NotImplementedError(f"Received `serverclose` command while running session in {self.mode} mode")

        else:
            raise RelpProtocolError(f"Unsupported command received: `{frame.command}`")

    def _receiver(self):
        self.logger.info("Starting receiver thread")
        frame_buffer = ''
        while self.running:
            data = self.socket.recv(4096)
            self.logger.debug("Received data: %s", data)
            frame_buffer += data.decode()
            if data == '':
                self.logger.warning("Client disconnect")
                self.stop()
                break

            try:
                frames , frame_buffer = Frame.decode_batch(frame_buffer)
            except Exception as e:
                self.logger.warning("Error unpacking message: %s. Will ignore", e)
                continue
            for frame in frames:
                self._handle_frame(frame)
        self.logger.info("Stopping receiver thread")

    def _sender(self):
        self.logger.info("Starting sender thread")
        while self.running:
            frame = self.send_queue.get()
            if frame is None:
                break
            self._send_frame(frame)
        self.logger.info("Stopping sender thread")

    def _ack(self, txnr):
        self.logger.debug("Sending ACK for: %s", txnr)
        ack = Ack(txnr)
        self._send_frame(ack.to_frame())

    def _ack_offer(self, txnr):
        offer = Offer()
        ack = Ack(txnr, message=offer.message())
        self._send_frame(ack.to_frame())

    def _send_frame(self, frame):
        self.logger.debug("Sending frame: %s", frame)
        data = frame.encode().encode('utf-8')
        self.socket.send(data)

    def send(self, command, message=''):
        '''Send a RELP message and wait for the ack'''
        txnr = self.txnr
        frame = Frame(txnr, command, message)

        self.ackmanager.prepare(txnr)

        self.logger.debug("Sending frame to send queue: %s", frame)
        self.send_frame(frame)
        self.txnr += 1

        self.logger.debug("Waiting for ACK for TXNR=%i", txnr)
        ack = self.ackmanager.get(txnr)
        self.logger.debug("Received ACK TXNR = %i", txnr)
        if ack.code == 200:
            pass
        elif ack.code == 500:
            raise Exception(f"NACK received: {ack.message}")

    def send_frame(self, frame):
        '''Send an exact RELP frame'''
        self.send_queue.put(frame)

    def recv(self):
        '''Receive a message in RELP'''
        frame = self.recv_queue.get()
        return frame
