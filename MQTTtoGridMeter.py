#!/usr/bin/env python

"""
Changed a lot of a Script originall created by Ralf Zimmermann (mail@ralfzimmermann.de) in 2020.
The orginal code and its documentation can be found on: https://github.com/RalfZim/venus.dbus-fronius-smartmeter
Used https://github.com/victronenergy/velib_python/blob/master/dbusdummyservice.py as basis for this service.
"""

"""
/data/Pathtothisscript/vedbus.py
/data/Pathtothisscript/ve_utils.py
python -m ensurepip --upgrade
pip install paho-mqtt
"""
try:
  import gobject  # Python 2.x
except:
  from gi.repository import GLib as gobject # Python 3.x
import platform
import logging
import time
import sys
import json
import os
import paho.mqtt.client as mqtt
try:
  import thread   # for daemon = True  / Python 2.x
except:
  import _thread as thread   # for daemon = True  / Python 3.x

# our own packages
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../ext/velib_python'))
from vedbus import VeDbusService

path_UpdateIndex = '/UpdateIndex'

# MQTT Setup
broker_address = "mosquitto.allesina"
MQTTNAME = "MQTTtoMeter"
Zaehlersensorpfad = "counter/victron"


# Variblen setzen
verbunden = 0
total_power_L1 = 0
total_power_L2 = 0
total_power_L3 = 0
total_power = 0
total_voltage_L1 = 0
total_voltage_L2 = 0
total_voltage_L3 = 0
total_current_L1 = 0
total_current_L2 = 0
total_current_L3 = 0
total_energy_feed = 0
total_energy_need = 0

# MQTT Abfragen:

def on_disconnect(client, userdata, rc):
    global verbunden
    print("Client Got Disconnected")
    if rc != 0:
        print('Unexpected MQTT disconnection. Will auto-reconnect')

    else:
        print('rc value:' + str(rc))

    try:
        print("Trying to Reconnect")
        client.connect(broker_address)
        verbunden = 1
    except Exception as e:
        logging.exception("Fehler beim reconnecten mit Broker")
        print("Error in Retrying to Connect with Broker")
        verbunden = 0
        print(e)

def on_connect(client, userdata, flags, rc):
        global verbunden
        if rc == 0:
            print("Connected to MQTT Broker!")
            verbunden = 1   
        client.subscribe("counter/victron/total_power_L1")
        client.subscribe("counter/victron/total_power_L2")
        client.subscribe("counter/victron/total_power_L3")
        client.subscribe("counter/victron/total_power")
        client.subscribe("counter/victron/total_voltage_L1")
        client.subscribe("counter/victron/total_voltage_L2")
        client.subscribe("counter/victron/total_voltage_L3")
        client.subscribe("counter/victron/total_current_L1")
        client.subscribe("counter/victron/total_current_L2")
        client.subscribe("counter/victron/total_current_L3")
        client.subscribe("counter/victron/total_energy_feed")
        client.subscribe("counter/victron/total_energy_need")

print("connected to Zaehlersensorpfad", rc)

        else:
            print("Failed to connect, return code %d\n", rc)


def on_message(client, userdata, msg):
    try:
        global total_power_L1
        global total_power_L2 
        global total_power_L3
        global total_power
        global total_voltage_L1
        global total_voltage_L2
        global total_voltage_L3
        global total_current_L1
        global total_current_L2
        global total_current_L3
        global total_energy_feed
        global total_energy_need

        if msg.topic == "counter/victron/total_power":
            total_power = float(msg.payload)
        elif msg.topic == "counter/victron/total_power_L1":
            total_power_L1 = float(msg.payload)
        elif msg.topic == "counter/victron/total_power_L2":
            total_power_L2 = float(msg.payload)
        elif msg.topic == "counter/victron/total_power_L3":
            total_power_L3 = float(msg.payload)
        elif msg.topic == "counter/victron/total_voltage_L1":
            total_voltage_L1 = float(msg.payload)
        elif msg.topic == "counter/victron/total_voltage_L2":
            total_voltage_L2 = float(msg.payload)
        elif msg.topic == "counter/victron/total_voltage_L3":
            total_voltage_L3 = float(msg.payload)
        elif msg.topic == "counter/victron/total_current_L1":
            total_current_L1 = float(msg.payload)
        elif msg.topic == "counter/victron/total_current_L2":
            total_current_L2 = float(msg.payload)
        elif msg.topic == "counter/victron/total_current_L3":
            total_current_L3 = float(msg.payload)
        elif msg.topic == "counter/victron/total_energy_feed":
            total_energy_feed = float(msg.payload)
        elif msg.topic == "counter/victron/total_energy_need":
            total_energy_need = float(msg.payload)
        else:
            print("Unbekanntes Topic: " + msg.topic)

    except Exception as e:
        logging.exception("Programm MQTTtoMeter ist abgestuerzt. (on message Funkion)")
        print(e)
        print("Im MQTTtoMeter Programm ist etwas beim auslesen der Nachrichten schief gegangen")




class DbusDummyService:
  def __init__(self, servicename, deviceinstance, paths, productname='MQTTMeter', connection='MQTT'):
    self._dbusservice = VeDbusService(servicename)
    self._paths = paths

    logging.debug("%s /DeviceInstance = %d" % (servicename, deviceinstance))

    # Create the management objects, as specified in the ccgx dbus-api document
    self._dbusservice.add_path('/Mgmt/ProcessName', __file__)
    self._dbusservice.add_path('/Mgmt/ProcessVersion', 'Unkown version, and running on Python ' + platform.python_version())
    self._dbusservice.add_path('/Mgmt/Connection', connection)

    # Create the mandatory objects
    self._dbusservice.add_path('/DeviceInstance', deviceinstance)
    self._dbusservice.add_path('/ProductId', 45069) # value used in ac_sensor_bridge.cpp of dbus-cgwacs
    self._dbusservice.add_path('/ProductName', productname)
    self._dbusservice.add_path('/FirmwareVersion', 0.1)
    self._dbusservice.add_path('/HardwareVersion', 0)
    self._dbusservice.add_path('/Connected', 1)

    for path, settings in self._paths.items():
      self._dbusservice.add_path(
        path, settings['initial'], writeable=True, onchangecallback=self._handlechangedvalue)

    gobject.timeout_add(1000, self._update) # pause 1000ms before the next request

  
  
  
  def _update(self):
    self._dbusservice['/Ac/Power'] =  total_power # positive: consumption, negative: feed into grid
    self._dbusservice['/Ac/L1/Voltage'] = round(total_voltage_L1 ,2)
    self._dbusservice['/Ac/L2/Voltage'] = round(total_voltage_L2 ,2)
    self._dbusservice['/Ac/L3/Voltage'] = round(total_voltage_L3 ,2)
    self._dbusservice['/Ac/L1/Current'] = round(total_current_L1 ,2)
    self._dbusservice['/Ac/L2/Current'] = round(total_current_L2 ,2)
    self._dbusservice['/Ac/L3/Current'] = round(total_current_L3 ,2)
    self._dbusservice['/Ac/L1/Power'] = round(total_power_L1, 2)
    self._dbusservice['/Ac/L2/Power'] = round(total_power_L2, 2)
    self._dbusservice['/Ac/L3/Power'] = round(total_power_L3, 2)

    self._dbusservice['/Ac/Energy/Forward'] = total_energy_need
    self._dbusservice['/Ac/Energy/Reverse'] = total_energy_feed
    logging.info("House Consumption: {:.0f}".format(total_power))
    # increment UpdateIndex - to show that new data is available
    index = self._dbusservice[path_UpdateIndex] + 1  # increment index
    if index > 255:   # maximum value of the index
      index = 0       # overflow from 255 to 0
    self._dbusservice[path_UpdateIndex] = index
    return True

  def _handlechangedvalue(self, path, value):
    logging.debug("someone else updated %s to %s" % (path, value))
    return True # accept the change

def main():
  logging.basicConfig(level=logging.DEBUG) # use .INFO for less logging
  thread.daemon = True # allow the program to quit

  from dbus.mainloop.glib import DBusGMainLoop
  # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
  DBusGMainLoop(set_as_default=True)
  
  pvac_output = DbusDummyService(
    servicename='com.victronenergy.grid.cgwacs_ttyUSB0_mb1',
    deviceinstance=0,
    paths={
      '/Ac/Power': {'initial': 0},
      '/Ac/L1/Voltage': {'initial': 0},
      '/Ac/L2/Voltage': {'initial': 0},
      '/Ac/L3/Voltage': {'initial': 0},
      '/Ac/L1/Current': {'initial': 0},
      '/Ac/L2/Current': {'initial': 0},
      '/Ac/L3/Current': {'initial': 0},
      '/Ac/L1/Power': {'initial': 0},
      '/Ac/L2/Power': {'initial': 0},
      '/Ac/L3/Power': {'initial': 0},
      '/Ac/Energy/Forward': {'initial': 0}, # energy bought from the grid
      '/Ac/Energy/Reverse': {'initial': 0}, # energy sold to the grid
      path_UpdateIndex: {'initial': 0},
    })

  logging.info('Connected to dbus, and switching over to gobject.MainLoop() (= event based)')
  mainloop = gobject.MainLoop()
  mainloop.run()

# Konfiguration MQTT
client = mqtt.Client(MQTTNAME) # create new instance
client.on_disconnect = on_disconnect
client.on_connect = on_connect
client.on_message = on_message
client.connect(broker_address)  # connect to broker

client.loop_start()

if __name__ == "__main__":
  main()
