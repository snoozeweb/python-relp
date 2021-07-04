#!/usr/bin/env python3
'''Minimal RELP server'''

from relp.server import RelpServer

def handler(message):
    '''Handler for RELP server'''
    print(f"Received: {message}")

server = RelpServer('0.0.0.0', 2514, handler)

server.serve_forever()
