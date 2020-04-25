from abc import ABC, abstractmethod
import threading

class WriteValue:
    def __init__(self):
        self.lock = threading.Lock()
        self.value = bytes
        self.is_new = False

    def update_value(self, value: bytes):
        with self.lock:
            self.is_new = True
            self.value = value

    def check_new(self):
        with self.lock:
            return self.is_new
    
    def read_value(self):
        with self.lock:
            self.is_new = False
            return self.value


class Device(ABC):
    def __init__(self),name):
        self.name = name
        self.send_method = None
        self.interface = None
        self.interface_name = None

    def register_send_method(self, send_method):
        self.send_method = send_method

    def register_interface(self, interface):
        self.interface = interface
    
    @abstractmethod
    def get_subscribe_rules(self):
        pass


