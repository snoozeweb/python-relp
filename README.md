# Python RELP library

A pure python implementation of the RELP protocol (Reliable Event Logging Protocol),
client and server side.

# Installation

```bash
pip install git+git://github.com/rudexi/python-relp.git#egg=relp
```

# Usage

## Client

Using a compound statement (`with` statement):

```python
from relp.client import RelpClient

messages = [
    "My log message",
    "My second log message",
]

with RelpClient('myexample.com', 2514) as client:
    print("Starting RELP connection")
    for message in messages:
        client.syslog(message)
    print("Stopping client...")

print("Everything was transfered without error")
```

Without compound statement:
```python

client = RelpClient('myexample.com', 2514)
client.start()

client.syslog("My log message")
client.syslog("My second log message")

client.stop()
print("Everything was transfered without error")
```

> Note: Each `syslog` invocation will be sync and wait for the
> acknowledgement to return. It is possible to make the client
> multi-threaded and send multiple syslogs, this is not supported
> by the library yet.

## Server

```python
from relp.server import RelpServer

def handler(message):
    '''Handler for RELP server'''
    print(f"Received: {message}")

server = RelpServer('0.0.0.0', 2514, handler)

server.serve_forever()
```

> Note: The server will wait for the handler to be finished before sending
> the acknowledgement. So it's possible to write to disk, database, forward
> to another RELP server, or use any protocol that has application level
> acknowledgement (like HTTP return code for instance). The acknowledgement
> will be sent to the client only after the handler terminates.

# Contribute

Read [CONTRIBUTE.md](./CONTRIBUTE.md)
