from Devices.sygonix_ht_100 import *


class DeviceFactory:
    def __init__(self):
        self._builders = {}

    def register_builder(self, key, builder):
        self._builders[key] = builder

    def create(self, key, **kwargs):
        builder = self._builders.get(key)
        if not builder:
            raise ValueError(key)
        return builder(**kwargs)


class DeviceProvider(DeviceFactory):
    def __init__(self):
        super(DeviceProvider, self).__init__()
        self.register_builder('sygonix_ht_100', SygonixHt100Builder())

    def get(self, service_id, **kwargs):
        return self.create(service_id, **kwargs)




