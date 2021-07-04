import pytest

import time

from threading import Thread
from logging import getLogger
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Process, Pool, Queue

from relp.session import AckManager

log = getLogger('test-ack-manager')

class TestAckManager:
    def test_process(self):
        ackmanager = AckManager()

        #assert ackmanager.size() == 1
        log.debug("AckManager.events = %s", ackmanager.events)
        log.debug("AckManager.values = %s", ackmanager.values)

        def get_handler(key):
            log.debug("[get] Waiting for data")
            result = ackmanager.get('test')
            log.debug("[get] Got data")
            return result

        def put_handler(key, value):
            log.debug("[put] Started put")
            ackmanager.put(key, value)
            log.debug("[put] Finished putting data")

        with ThreadPoolExecutor() as threadpool:
            future = threadpool.submit(get_handler, 'test')
            threadpool.submit(put_handler, 'test', 123)
            assert future.result() == 123
