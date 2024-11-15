import time
import threading


class Snowflake:
    def __init__(self, worker_id: int = 0, datacenter_id: int = 0):
        self.worker_id = worker_id
        self.datacenter_id = datacenter_id

        self.sequence = 0
        self.last_timestamp = -1

        self.worker_id_bits = 5
        self.datacenter_id_bits = 5
        self.sequence_bits = 12

        self.max_worker_id = -1 ^ (-1 << self.worker_id_bits)
        self.max_datacenter_id = -1 ^ (-1 << self.datacenter_id_bits)

        self.worker_id_shift = self.sequence_bits
        self.datacenter_id_shift = self.sequence_bits + self.worker_id_bits
        self.timestamp_shift = self.sequence_bits + self.worker_id_bits + self.datacenter_id_bits

        self.lock = threading.Lock()

    @staticmethod
    def _current_millis():
        return int(time.time() * 1000)

    def _next_timestamp(self, last_timestamp):
        timestamp = self._current_millis()
        while timestamp <= last_timestamp:
            timestamp = self._current_millis()
        return timestamp

    def generate_id(self):
        with self.lock:
            timestamp = self._current_millis()

            if timestamp < self.last_timestamp:
                raise Exception("Clock is moving backwards. Rejecting requests until {}.".format(self.last_timestamp))

            if self.last_timestamp == timestamp:
                self.sequence = (self.sequence + 1) & self.max_worker_id
            else:
                self.sequence = 0

            self.last_timestamp = timestamp

            snowflake_id = ((timestamp << self.timestamp_shift) |
                            (self.datacenter_id << self.datacenter_id_shift) |
                            (self.worker_id << self.worker_id_shift) |
                            self.sequence)

            return snowflake_id


snowflake_generator = Snowflake(worker_id=0, datacenter_id=0)
