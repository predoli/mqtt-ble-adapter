# MQTT ble adapter
## description
This repository implements a mqtt node. The idea is that it runs on a device which is connected to a ip network and acts as a bridge to different communication technologies.

BLE example inspired from [this hack](https://www.torsten-traenkner.de/wissen/smarthome/heizung.php).

## installation
Currently only tested on a raspberry pi with one BLE device.
For the BLE interface the [gatt](https://github.com/getsenic/gatt-python) library is used which has to be executed with sudo privileges.
Assuming Bluez is running:

``sudo pip3 install gatt``

``sudo apt-get install python3-dbus``

``sudo pip3 install src/setup.py install``

``sudo runMainController yourdevices.yaml yourmqttsettings.yaml``
## open topics/next steps
 - test different devices (different and same phys. interface)
 - endurance run
