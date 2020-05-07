from Devices.device_parents import Device, WriteValue
import threading
import logging
import gatt
import time
from datetime import datetime
import queue
from enum import Enum
from Interfaces.hci0 import Hci0Manager
import typing


class auth_state(Enum):
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    LOGGING_IN = 3
    LOGGED_IN = 4
    LOGGING_IN_FAILED = 5
    CONNECTING_FAILED = 6
    DISCONNECING = 7
    DISCONNCTING_FAILED = 8


class com_state(Enum):
    PENDING = 1
    SUCCESS = 2
    FAILED = 3


class SygonixHt100BTCOM(gatt.Device):
    def __init__(self, mac_address:str, manager:gatt.DeviceManager, pw):
        gatt.Device.__init__(self,mac_address,manager)
        self.login_timout = 15.0
        self.logout_timeout = 15.0
        self.temp_characteristic = None
        self.pw_characterisitc = None
        self.battery_characteristic = None
        self.temp = (0,com_state.PENDING)
        self.battery_state = (0,com_state.PENDING)
        self.logged_in = auth_state.DISCONNECTED
        self.write_sucessful = com_state.PENDING
        self.lock = threading.Lock() 
        self.lock_auth_state = threading.Lock()
        self.lock_battery_state = threading.Lock()
        self.lock_temp_state = threading.Lock()
        self.lock_write_state = threading.Lock()
        self.pw = pw

    def connect_succeeded(self):
        print("connected")
        with self.lock_auth_state:
            if self.logged_in is not auth_state.LOGGED_IN and self.logged_in is not auth_state.LOGGING_IN and self.pw_characterisitc is not None:
                self.logged_in = auth_state.CONNECTED
                self.pw_characterisitc.write_value(self.pw.to_bytes(4,byteorder='little'))
                self.logged_in = auth_state.LOGGING_IN            

    def connect(self):
        if self.get_auth_state() is not auth_state.DISCONNECTED:
            return
        with self.lock_auth_state:
            self.logged_in = auth_state.CONNECTING
        self.lock.acquire()
        self._connect_retry_attempt = 0
        self._connect_signals()
        self._connect()
    
    def login(self):
        t1 = time.time()
        if self.get_auth_state() is auth_state.DISCONNECTED:
            self.connect()
        else:
            print("device not disconnected")
            return False    
        while self.get_auth_state() is not auth_state.LOGGED_IN:
            time.sleep(0.1)
            if time.time()-t1 > self.login_timout:
                print("login timeout")
                return False
        return self.get_auth_state() is auth_state.LOGGED_IN

    def logout(self):
        t1 = time.time()
        if self.get_auth_state() is not auth_state.DISCONNECTED:  
            self.disconnect()
            while self.get_auth_state() is not auth_state.DISCONNECTED:            
                time.sleep(0.1)   
                if time.time()- t1 > self.logout_timeout:
                    print("logout timout")
                    return False
        return self.get_auth_state() is auth_state.DISCONNECTED

    def get_auth_state(self):
        with self.lock_auth_state:
            state = self.logged_in
        return state

    def disconnect_succeeded(self):
        print("disconnected")
        with self.lock_auth_state:
            self.logged_in = auth_state.DISCONNECTED
        self.lock.release()

    def services_resolved(self):
        super().services_resolved()
        device_information_service = next(
            s for s in self.services
            if s.uuid == '47e9ee00-47e9-11e4-8939-164230d1df67')
        self.temp_characteristic = next(
            c for c in device_information_service.characteristics
            if c.uuid == '47e9ee2b-47e9-11e4-8939-164230d1df67')
        self.temp_characteristic.enable_notifications()
        self.battery_characteristic = next(
            c for c in device_information_service.characteristics
            if c.uuid == '47e9ee2c-47e9-11e4-8939-164230d1df67')
        self.pw_characterisitc = next(
            c for c in device_information_service.characteristics
            if c.uuid == '47e9ee30-47e9-11e4-8939-164230d1df67')
        
        if self.get_auth_state() is not auth_state.LOGGED_IN:
            self.pw_characterisitc.write_value(self.pw.to_bytes(4,byteorder='little'))

    def characteristic_value_updated(self, characteristic, value):
        if characteristic is self.temp_characteristic:
            print("received temp charactersitic")
            with self.lock_temp_state:
                self.temp = (self.byte_to_temp(value),com_state.SUCCESS)
        if characteristic is self.battery_characteristic:
            print("received battery characterisic")
            with self.lock_battery_state:
                self.battery_state = (self.byte_to_battery_state(value), com_state.SUCCESS)
            

    def characteristic_read_value_failed(self, characteristic, error):
        if characteristic is self.temp_characteristic:
            with self.lock_temp_state:
                self.temp = (self.temp[0], com_state.FAILED)
            print("read error:" + str(error))
        elif characteristic is self.battery_characteristic:
            with self.lock_battery_state:
                self.battery_state = (self.battery_state[0],com_state.FAILED)
            print("read error:" + str(error))
        self.disconnect()

    def characteristic_write_value_succeeded(self, characteristic):
        if characteristic is self.pw_characterisitc:
            print("logged in")
            with self.lock_auth_state:
                self.logged_in = auth_state.LOGGED_IN
        elif characteristic is self.temp_characteristic:
            with self.lock_write_state:
                self.write_sucessful = com_state.SUCCESS

    def byte_to_battery_state(self,value:bytes):
        return round(100*float(value[0])/float(0xff))

    def byte_to_temp(self,value:bytes):
        value_int_raw = int(value[0])
        return float(value_int_raw)/2

    def temp_to_byte(self,value:float):
        high = value + 2
        low = value -1
        value_int_high = int(high*2)
        value_int_low = int(low*2)
        value_int_target = int(value*2)
        return bytes([0x80, value_int_target, value_int_low, value_int_high, 0x00, 0x80, 0x80])
    
    def get_everything(self)->tuple:
        temp_local = (-1,com_state.FAILED)
        battery_state_local = (-1,com_state.FAILED)
        if self.login():
            temp_local = (-1,com_state.PENDING)
            battery_state_local = (-1,com_state.PENDING)
            with self.lock_temp_state:
                self.temp = (self.temp[0], temp_local[1])
            self.temp_characteristic.read_value()
            while temp_local[1] is com_state.PENDING:
                with self.lock_temp_state:
                    temp_local = self.temp
                time.sleep(0.1)
            with self.lock_battery_state:
                self.battery_state = (self.battery_state[0],battery_state_local[1])
            self.battery_characteristic.read_value()
            while battery_state_local[1] is com_state.PENDING:
                with self.lock_battery_state:
                    battery_state_local = self.battery_state
                time.sleep
        if self.logout():
            return  {'temp':temp_local,'battery_state':battery_state_local}
        else:
            return {'temp':(temp_local[0],com_state.FAILED),'battery_state':(battery_state_local[0],com_state.FAILED)}

    def get_temp(self)->tuple:
        temp_local = (-1,com_state.FAILED)
        if self.login():
            temp_local = (-1,com_state.PENDING)
            with self.lock_temp_state:
                self.temp = (self.temp[0], temp_local[1])
            self.temp_characteristic.read_value()
            while temp_local[1] is com_state.PENDING:
                with self.lock_temp_state:
                    temp_local = self.temp
                time.sleep(0.1)
        if self.logout():
            return temp_local
        else:
            return (temp_local[0],com_state.FAILED)

    def get_battery_state(self)->tuple:
        battery_state_local = (-1,com_state.FAILED)
        if self.login():
            battery_state_local = (-1,com_state.PENDING)
            with self.lock_battery_state:
                self.battery_state = (self.battery_state[0], battery_state_local[1])
            self.battery_characteristic.read_value()
            while battery_state_local[1] is com_state.PENDING:
                with self.lock_battery_state:
                    battery_state_local = self.battery_state
                time.sleep(0.1)
        if self.logout():
            return battery_state_local
        else:
            return (battery_state_local[0],com_state.FAILED)        

    def send_temp(self,value:float)->bool:
        write_success_local = com_state.PENDING
        if self.login():
            with self.lock_write_state:
                self.write_success_local = write_success_local        
            self.temp_characteristic.write_value(self.temp_to_byte(value))        
            while write_success_local is com_state.PENDING:
                with self.lock_write_state:
                    write_success_local = self.write_sucessful
                time.sleep(0.1)        
        return write_success_local is com_state.SUCCESS and self.logout()

    def characteristic_write_value_failed(self, characteristic, error):
        if characteristic is self.temp_characteristic:
            print("write temp error:" + str(error))
            with self.lock_write_state:
                self.write_sucessful = com_state.FAILED
        elif characteristic is self.pw_characterisitc:
            print("write temp error:" + str(error))
            with self.lock_auth_state:
                self.logged_in = auth_state.LOGGING_IN_FAILED
        self.disconnect()


class SygonixHt100(Device, threading.Thread):
    def __init__(self, address:str, pw, set_temp_topic_name:str, get_temp_topic_name:str, get_battery_topic_name:str, debug_topic_name:str , send_interval:int, name:str):
        threading.Thread.__init__(self)
        Device.__init__(self,name)
        self.pw = pw
        self.set_temp_topic_name = set_temp_topic_name
        self.get_temp_topic_name = get_temp_topic_name
        self.debug_topic_name = debug_topic_name
        self.get_battery_topic_name = get_battery_topic_name
        self.cycle_fundamental = 5.0
        self.cycle_time_send_temp = send_interval
        self.bt_handle = None
        self.interface_name = 'ble'
        self.inital_started = False
        self.address = address
        self.temp_write = WriteValue()

        self.state_lock = threading.Lock()
        self.set_running = True

    def reset_bt_handle(self):
        self.send_method(self.debug_topic_name,'Reset Device')
        self.interface.manager.stop()
        self.bt_handle = SygonixHt100BTCOM(mac_address=self.address, manager=self.interface.manager,pw = self.pw)

    def run(self):
        self.bt_handle = SygonixHt100BTCOM(mac_address=self.address, manager=self.interface.manager,pw = self.pw)
        with self.state_lock:
            running = self.set_running
        start_send_time = time.time()
        while running:
            start = time.time()
            if time.time() - start_send_time > self.cycle_time_send_temp:
                data = self.bt_handle.get_everything()
                if data['temp'][1] is com_state.SUCCESS and data['battery_state'][1]:
                    self.send_method(self.get_temp_topic_name,data['temp'][0])
                    self.send_method(self.get_battery_topic_name,data['battery_state'][0])
                    start_send_time = time.time()
                else:
                    self.reset_bt_handle()
                    continue

            if self.temp_write.check_new():
                if not self.bt_handle.send_temp(float(self.temp_write.read_value())):
                    self.temp_write.update_value(self.temp_write.read_value())
                    self.reset_bt_handle()
                    continue
                self.send_method(self.debug_topic_name,'send new temp')

            dt = time.time()-start
            if self.cycle_fundamental-dt > 0.0:
                time.sleep(self.cycle_fundamental-dt)

    def stop(self):
        with self.state_lock:
            self.set_running = False

    
    def get_subscribe_rules(self):
        subscribe_rules = dict()
        subscribe_rules[self.set_temp_topic_name] = self.temp_write
        return subscribe_rules


class SygonixHt100Builder:
    def __init__(self):
        self._instance = None

    def __call__(self, address:str, pw, set_temp_topic_name:str, get_temp_topic_name:str, get_battery_topic_name:str, debug_topic_name:str, send_interval:int, name:str, **_ignored):
        if not self._instance:
            self._instance = SygonixHt100(address, pw, set_temp_topic_name, get_temp_topic_name, get_battery_topic_name, debug_topic_name, send_interval, name)
        return self._instance




