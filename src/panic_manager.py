import threading
import sys
import time


class PanicManager:
    def __init__(self, logger=None):
        self.monitors = {}
        self.logger = logger
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    def register(self, tag=None, start_time=None, interval=None):
        self.logger.debug('panic_manager register tag {} start_time {} sec interval {} sec'.format(tag, start_time, interval))
        with self.lock:
            self.monitors[tag] = {
                'start_at': time.time(),
                'ping_at': None,
                'start_time': start_time,
                'interval': interval
            }

    def ping(self, tag=None):
        with self.lock:
            self.monitors[tag]['ping_at'] = time.time()

    def panic(self):
        sys.exit(1)

    def run(self):
        while True:
            # self.logger.debug('panic_manager loop')
            now = time.time()
            with self.lock:
                for tag in self.monitors:
                    monitor = self.monitors[tag]
                    if monitor['ping_at']:
                        if now - monitor['ping_at'] > monitor['interval']:
                            self.logger.error('{} ping delayed. exit'.format(tag))
                            self.panic()
                    else:
                        if now - monitor['start_at'] > monitor['start_time']:
                            self.logger.error('{} start delayed. exit'.format(tag))
                            self.panic()
            time.sleep(5)
