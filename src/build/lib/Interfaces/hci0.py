import gatt
import threading


class Hci0Manager(threading.Thread):
    def __init__(self, autorestart = True):
        threading.Thread.__init__(self)
        self.manager = gatt.DeviceManager(adapter_name='hci0')
        self.autorestart = autorestart
    def run(self):
        while self.autorestart:
            self.manager.run()

    