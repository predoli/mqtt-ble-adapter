import yaml
from Devices.device_factory import *
import paho.mqtt.client as mqtt
import logging
from Interfaces.hci0 import Hci0Manager


class MqttWrapper:
    def __init__(self, mqtt_settings : dict):
        self.hostname = mqtt_settings['hostname']
        self.port = mqtt_settings['port']
        self.timeout = mqtt_settings['timeout']
        self.subscribe_rules = dict()
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_message = self.on_message

    def start(self,subscribe_rules: dict):
        self.subscribe_rules = subscribe_rules
        self.mqtt_client.connect(self.hostname, self.port, self.timeout)
        for topic in self.subscribe_rules:
            self.mqtt_client.subscribe(topic)
        self.mqtt_client.loop_start()

    def stop(self):
        self.mqtt_client.loop_stop()        

    def send(self, topic: str, payload: bytes):
        self.mqtt_client.publish(topic, payload)

    def on_message(self, client, userdata, msg):
        sub_rule = self.subscribe_rules[msg.topic]
        sub_rule.update_value(msg.payload)


class MainController:
    def __init__(self, device_conf, mqtt_conf):
        
        self.interface_name_map = {}
        self.interface_name_map['ble'] = Hci0Manager

        self.mqtt_settings = self.read_config(mqtt_conf)
        self.client = MqttWrapper(self.mqtt_settings)

        self.device_settings = self.read_config(device_conf)
        self.decive_factory = DeviceProvider()
        self.devices = self.create_devices(self.device_settings)

        self.interfaces = []
        self.interfaces_map = dict()
        self.create_interfaces()

        for device in self.devices:
            device.register_interface(self.interfaces_map[device])
            device.register_send_method(self.client.mqtt_client.publish)

    def start(self):
        self.client.start(self.parse_subscribe_rules())
        for interface in self.interfaces:
            interface.start()
        for device in self.devices:
            device.start()

    def parse_subscribe_rules(self):
        rule = dict()
        for device in self.devices:
            device_rules = device.get_subscribe_rules()
            rule.update(device_rules)
        return rule

    def create_devices(self, device_settings : dict):
        devices = []
        for device_name in device_settings:
                device_settings = device_settings[device_name]
                temp_device = self.decive_factory.get(device_settings['type'], **device_settings)
                devices.append(temp_device)
        return devices

    def create_interfaces(self):
        #create uniqe list of interfaces and map to device
        interface_classes= []
        interface_classes_map= {}
        interfaces = []
        interfaces_map ={}
        for device in self.devices:
            interface_class = self.interface_name_map[device.interface_name]
            if interface_class not in interface_classes:
                interface_classes.append(interface_class)
            interface_classes_map[device] = interface_class

        for interface_class in interface_classes:
            interfaces.append(interface_class())

        for device in self.devices:
            for interface in interfaces:
                if interface.__class__ == interface_classes_map[device]:
                    interfaces_map[device] = interface
                    break
        self.interfaces_map = interfaces_map
        self.interfaces = interfaces

    @staticmethod
    def read_config(file):
        with open(file, 'r') as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                logging.error(exc)


