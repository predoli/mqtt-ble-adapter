from MainController.MainController import MainController
import argparse

parser = argparse.ArgumentParser(description='MQTT-BLE ADAPTER FRAMEWORK')
parser.add_argument('devices', help='Device .yaml file')
parser.add_argument('mqtt', help='Mqtt devices')

args = parser.parse_args()
m = MainController(args.devices, args.mqtt)
m.start()