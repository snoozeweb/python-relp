#!/usr/bin/env python3
'''Minimal RELP client'''

from relp.client import RelpClient

with RelpClient('127.0.0.1', 2514) as client:
    print("Start sending")
    for index in range(1, 50):
        message = f"message #{index}"
        print(f"Sending: {message}")
        client.syslog(message)
    print("Done sending")
