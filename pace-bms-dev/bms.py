

import paho.mqtt.client as mqtt
import socket
import time
import yaml
import os
import json
import serial
import io
import json
import atexit
import sys
import constants

print("Starting up...")

config = {}
script_version = ""

if os.path.exists('/data/options.json'):
    print("Loading options.json")
    with open(r'/data/options.json') as file:
        config = json.load(file)
        print("Config: " + json.dumps(config))

elif os.path.exists('pace-bms-dev\\config.yaml'):
    print("Loading config.yaml")
    with open(r'pace-bms-dev\\config.yaml') as file:
        config = yaml.load(file, Loader=yaml.FullLoader)['options']
        
else:
    sys.exit("No config file found")  


scan_interval = config['scan_interval']
connection_type = config['connection_type']
bms_serial = config['bms_serial']
ha_discovery_enabled = config['mqtt_ha_discovery']
code_running = True
bms_connected = False
mqtt_connected = False
print_initial = True
debug_output = config['debug_output']
disc_payload = {}
repub_discovery = 0

bms_version = ''
bms_sn = ''
pack_sn = ''
packs = 1
cells = 13
temps = 6


print("Connection Type: " + connection_type)

def on_connect(client, userdata, flags, rc):
    print("MQTT connected with result code "+str(rc))
    client.will_set(config['mqtt_base_topic'] + "/availability","offline", qos=0, retain=False)
    global mqtt_connected
    mqtt_connected = True

def on_disconnect(client, userdata, rc):
    print("MQTT disconnected with result code "+str(rc))
    global mqtt_connected
    mqtt_connected = False


client = mqtt.Client("bmspace")
client.on_connect = on_connect
client.on_disconnect = on_disconnect
#client.on_message = on_message

client.username_pw_set(username=config['mqtt_user'], password=config['mqtt_password'])
client.connect(config['mqtt_host'], config['mqtt_port'], 60)
client.loop_start()
time.sleep(2)

def exit_handler():
    print("Script exiting")
    client.publish(config['mqtt_base_topic'] + "/availability","offline")
    return

atexit.register(exit_handler)

def bms_connect(address, port):

    if connection_type == "Serial":

        try:
            print("trying to connect %s" % bms_serial)
            s = serial.Serial(bms_serial,timeout = 1)
            print("BMS serial connected")
            return s, True
        except IOError as msg:
            print("BMS serial error connecting: %s" % msg)
            return False, False    

    else:

        try:
            print("trying to connect " + address + ":" + str(port))
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((address, port))
            print("BMS socket connected")
            return s, True
        except OSError as msg:
            print("BMS socket error connecting: %s" % msg)
            return False, False

def bms_sendData(comms,request=''):

    if connection_type == "Serial":

        try:
            if len(request) > 0:
                comms.write(request)
                time.sleep(0.25)
                return True
        except IOError as e:
            print("BMS serial error: %s" % e)
            # global bms_connected
            return False

    else:

        try:
            if len(request) > 0:
                comms.send(request)
                time.sleep(0.25)
                return True
        except Exception as e:
            print("BMS socket error: %s" % e)
            # global bms_connected
            return False

def bms_get_data(comms):
    try:
        if connection_type == "Serial":
            inc_data = comms.readline()
        else:
            temp = bytes()
            
            while len(temp) == 0 or temp[-1] != 13:
                temp = temp + comms.recv(4096)

            temp2 = temp.split(b'\r')
            # Decide which one to take:
            for element in range(0,len(temp2)):
                SOI = hex(ord(temp2[element][0:1]))
                if SOI == '0x7e':
                    inc_data = temp2[element] + b'\r'
                    break

            if (len(temp2) > 2) & (debug_output > 0):
                print("Multiple EOIs detected")
                print("...for incoming data: " + str(temp) + " |Hex: " + str(temp.hex(' ')))
                
        return inc_data
    except Exception as e:
        print("BMS socket receive error: %s" % e)
        # global bms_connected
        return False

def ha_discovery():

    global ha_discovery_enabled
    global packs

    if ha_discovery_enabled:
        
        print("Publishing HA Discovery topic...")

        disc_payload['availability_topic'] = config['mqtt_base_topic'] + "/availability"

        device = {}
        device['manufacturer'] = "BMS Pace"
        device['model'] = "AM-x"
        device['identifiers'] = "bmspace_" + bms_sn
        device['name'] = "Generic Lithium"
        device['sw_version'] = bms_version
        disc_payload['device'] = device

        for p in range (1,packs+1):

            for i in range(0,cells):
                disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Cell " + str(i+1).zfill(config['zero_pad_number_cells']) + " Voltage"
                disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_v_cell_" + str(i+1).zfill(config['zero_pad_number_cells'])
                disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/v_cells/cell_" + str(i+1).zfill(config['zero_pad_number_cells'])
                disc_payload['unit_of_measurement'] = "mV"
                client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            for i in range(0,temps):
                disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Temperature " + str(i+1)
                disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_temp_" + str(i+1)
                disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/temps/temp_" + str(i+1)
                disc_payload['unit_of_measurement'] = "°C"
                client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            # disc_payload['name'] = "MOS_Temp"
            # disc_payload['unique_id'] = "bmspace_" + bms_sn + "_t_mos"
            # disc_payload['state_topic'] = config['mqtt_base_topic'] + "/t_mos"
            # disc_payload['unit_of_measurement'] = "°C"
            # client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'] + "/config",json.dumps(disc_payload),qos=0, retain=True)

            # disc_payload['name'] = "Environmental_Temp"
            # disc_payload['unique_id'] = "bmspace_" + bms_sn + "_t_env"
            # disc_payload['state_topic'] = config['mqtt_base_topic'] + "/t_env"
            # disc_payload['unit_of_measurement'] = "°C"
            # client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'] + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Current"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_i_pack"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/i_pack"
            disc_payload['unit_of_measurement'] = "A"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Voltage"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_v_pack"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/v_pack"
            disc_payload['unit_of_measurement'] = "V"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Remaining Capacity"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_i_remain_cap"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/i_remain_cap"
            disc_payload['unit_of_measurement'] = "mAh"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " State of Health"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_soh"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/soh"
            disc_payload['unit_of_measurement'] = "%"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Cycles"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_cycles"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/cycles"
            disc_payload['unit_of_measurement'] = ""
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Full Capacity"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_i_full_cap"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/i_full_cap"
            disc_payload['unit_of_measurement'] = "mAh"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Design Capacity"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_i_design_cap"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/i_design_cap"
            disc_payload['unit_of_measurement'] = "mAh"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " State of Charge"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_soc"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/soc"
            disc_payload['unit_of_measurement'] = "%"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " State of Health"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_soh"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/soh"
            disc_payload['unit_of_measurement'] = "%"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)


            disc_payload.pop('unit_of_measurement')

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Warnings"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_warnings"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/warnings"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Balancing1"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_balancing1"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/balancing1"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Balancing2"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_balancing2"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/balancing2"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)


            # Binary Sensors
            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Protection Short Circuit"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_prot_short_circuit"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/prot_short_circuit"
            disc_payload['payload_on'] = "1"
            disc_payload['payload_off'] = "0"
            client.publish(config['mqtt_ha_discovery_topic']+"/binary_sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Protection Discharge Current"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_prot_discharge_current"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/prot_discharge_current"
            disc_payload['payload_on'] = "1"
            disc_payload['payload_off'] = "0"
            client.publish(config['mqtt_ha_discovery_topic']+"/binary_sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Protection Charge Current"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_prot_charge_current"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/prot_charge_current"
            disc_payload['payload_on'] = "1"
            disc_payload['payload_off'] = "0"
            client.publish(config['mqtt_ha_discovery_topic']+"/binary_sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Current Limit"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_current_limit"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/current_limit"
            disc_payload['payload_on'] = "1"
            disc_payload['payload_off'] = "0"
            client.publish(config['mqtt_ha_discovery_topic']+"/binary_sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Charge FET"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_charge_fet"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/charge_fet"
            disc_payload['payload_on'] = "1"
            disc_payload['payload_off'] = "0"
            client.publish(config['mqtt_ha_discovery_topic']+"/binary_sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Discharge FET"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_discharge_fet"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/discharge_fet"
            disc_payload['payload_on'] = "1"
            disc_payload['payload_off'] = "0"
            client.publish(config['mqtt_ha_discovery_topic']+"/binary_sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Pack Indicate"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_pack_indicate"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/pack_indicate"
            disc_payload['payload_on'] = "1"
            disc_payload['payload_off'] = "0"
            client.publish(config['mqtt_ha_discovery_topic']+"/binary_sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Reverse"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_reverse"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/reverse"
            disc_payload['payload_on'] = "1"
            disc_payload['payload_off'] = "0"
            client.publish(config['mqtt_ha_discovery_topic']+"/binary_sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " AC In"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_ac_in"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/ac_in"
            disc_payload['payload_on'] = "1"
            disc_payload['payload_off'] = "0"
            client.publish(config['mqtt_ha_discovery_topic']+"/binary_sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Heart"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_heart"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/heart"
            disc_payload['payload_on'] = "1"
            disc_payload['payload_off'] = "0"
            client.publish(config['mqtt_ha_discovery_topic']+"/binary_sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack " + str(p).zfill(config['zero_pad_number_packs']) + " Cell Max Volt Diff"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_" + str(p).zfill(config['zero_pad_number_packs']) + "_cells_max_diff_calc"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/cells_max_diff_calc"
            disc_payload['unit_of_measurement'] = "mV"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            # Pack data
            disc_payload.pop('payload_on')
            disc_payload.pop('payload_off')

            disc_payload['name'] = "Pack Remaining Capacity"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_i_remain_cap"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_remain_cap"
            disc_payload['unit_of_measurement'] = "mAh"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack Full Capacity"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_i_full_cap"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_full_cap"
            disc_payload['unit_of_measurement'] = "mAh"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack Design Capacity"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_i_design_cap"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_design_cap"
            disc_payload['unit_of_measurement'] = "mAh"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack State of Charge"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_soc"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_soc"
            disc_payload['unit_of_measurement'] = "%"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

            disc_payload['name'] = "Pack State of Health"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_pack_soh"
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack_soh"
            disc_payload['unit_of_measurement'] = "%"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'].replace(' ', '_') + "/config",json.dumps(disc_payload),qos=0, retain=True)

    else:
        print("HA Discovery Disabled")

def chksum_calc(data):

    global debug_output
    chksum = 0

    try:

        for element in range(1, len(data)): #-5):
            chksum += (data[element])
        
        chksum = chksum % 65536
        chksum = '{0:016b}'.format(chksum)
    
        flip_bits = '' 
        for i in chksum:
            if i == '0':
                flip_bits += '1'
            else:
                flip_bits += '0'

        chksum = flip_bits
        chksum = int(chksum,2)+1

        chksum = format(chksum, 'X')

    except Exception as e:
        if debug_output > 0:
            print("Error calculating CHKSUM using data: " + data)
            print("Error details: ", str(e))
        return(False)

    return(chksum)

def cid2_rtn(rtn):

    # RTN Reponse codes, looking for errors
    if rtn == b'00':
        return False, False
    elif rtn == b'01':
        return True, "RTN Error 01: Undefined RTN error"
    elif rtn == b'02':
        return True, "RTN Error 02: CHKSUM error"
    elif rtn == b'03':
        return True, "RTN Error 03: LCHKSUM error"
    elif rtn == b'04':
        return True, "RTN Error 04: CID2 undefined"
    elif rtn == b'05':
        return True, "RTN Error 05: Undefined error"
    elif rtn == b'06':
        return True, "RTN Error 06: Undefined error"
    elif rtn == b'09':
        return True, "RTN Error 09: Operation or write error"
    else:
        return False, False

def bms_parse_data(inc_data):

    global debug_output

    #inc_data = b'~25014600D0F40002100DD50DBC0DD70DD70DD40DD70DD20DD50DD30DD60DC10DD40DD50DD70DD30DD5060B760B710B700B7A0B7D0B9D0000DD2326A90226AC011126AC64100DD30DBD0DD40DC60DD50DD40DD50DD50DD60DD60DD40DD20DD30\r'

    try:
        
        SOI = hex(ord(inc_data[0:1]))
        if SOI != '0x7e':
            return(False,"Incorrect starting byte for incoming data")

        if debug_output > 1:
            print("SOI: ", SOI)
            print("VER: ", inc_data[1:3])
            print("ADR: ", inc_data[3:5])
            print("CID1 (Type): ", inc_data[5:7])

        RTN = inc_data[7:9]
        error, info = cid2_rtn(RTN)
        if error:
            print(error)
            raise Exception(error)
        
        LCHKSUM = inc_data[9]

        if debug_output > 1:
            print("RTN: ", RTN)
            print("LENGTH: ", inc_data[9:13])
            print(" - LCHKSUM: ", LCHKSUM)
            print(" - LENID: ", inc_data[10:13])

        LENID = int(inc_data[10:13],16) #amount of bytes, i.e. 2x hex

        calc_LCHKSUM = lchksum_calc(inc_data[10:13])
        if calc_LCHKSUM == False:
            return(False,"Error calculating LCHKSUM for incoming data")

        if LCHKSUM != ord(calc_LCHKSUM):
            if debug_output > 0:
                print("LCHKSUM received: " + str(LCHKSUM) + " does not match calculated: " + str(ord(calc_LCHKSUM)))
            return(False,"LCHKSUM received: " + str(LCHKSUM) + " does not match calculated: " + str(ord(calc_LCHKSUM)))

        if debug_output > 1:
            print(" - LENID (int): ", LENID)

        INFO = inc_data[13:13+LENID]

        if debug_output > 1:
            print("INFO: ", INFO)

        CHKSUM = inc_data[13+LENID:13+LENID+4]
        
        if debug_output > 1:
            print("CHKSUM: ", CHKSUM)
            #print("EOI: ", hex(inc_data[13+LENID+4]))

        calc_CHKSUM = chksum_calc(inc_data[:len(inc_data)-5])


        if debug_output > 1:
            print("Calc CHKSUM: ", calc_CHKSUM)
    except Exception as e:
        if debug_output > 0:
            print("Error1 calculating CHKSUM using data: ", inc_data)
        return(False,"Error1 calculating CHKSUM: " + str(e))

    if calc_CHKSUM == False:
        if debug_output > 0:
            print("Error2 calculating CHKSUM using data: ", inc_data)
        return(False,"Error2 calculating CHKSUM")

    if CHKSUM.decode("ASCII") == calc_CHKSUM:
        return(True,INFO)
    else:
        if debug_output > 0:
            print("Received and calculated CHKSUM does not match: Received: " + CHKSUM.decode("ASCII") + ", Calculated: " + calc_CHKSUM)
            print("...for incoming data: " + str(inc_data) + " |Hex: " + str(inc_data.hex(' ')))
            print("Length of incoming data as measured: " + str(len(inc_data)))
            print("SOI: ", SOI)
            print("VER: ", inc_data[1:3])
            print("ADR: ", inc_data[3:5])
            print("CID1 (Type): ", inc_data[5:7])
            print("RTN (decode!): ", RTN)
            print("LENGTH: ", inc_data[9:13])
            print(" - LCHKSUM: ", inc_data[9])
            print(" - LENID: ", inc_data[10:13])
            print(" - LENID (int): ", int(inc_data[10:13],16))
            print("INFO: ", INFO)
            print("CHKSUM: ", CHKSUM)
            #print("EOI: ", hex(inc_data[13+LENID+4]))
        return(False,"Checksum error")

def lchksum_calc(lenid):

    chksum = 0

    try:

        # for element in range(1, len(lenid)): #-5):
        #     chksum += (lenid[element])
        
        for element in range(0, len(lenid)):
            chksum += int(chr(lenid[element]),16)

        chksum = chksum % 16
        chksum = '{0:04b}'.format(chksum)

        flip_bits = '' 
        for i in chksum:
            if i == '0':
                flip_bits += '1'
            else:
                flip_bits += '0'

        chksum = flip_bits
        chksum = int(chksum,2)

        chksum += 1

        if chksum > 15:
            chksum = 0

        chksum = format(chksum, 'X')

    except:

        print("Error calculating LCHKSUM using LENID: ", lenid)
        return(False)

    return(chksum)

def bms_request(bms, ver=b"\x32\x35",adr=b"\x30\x31",cid1=b"\x34\x36",cid2=b"\x43\x31",info=b"",LENID=False):

    global bms_connected
    global debug_output
    
    request = b'\x7e'
    request += ver
    request += adr
    request += cid1
    request += cid2

    if not(LENID):
        LENID = len(info)
        #print("Length: ", LENID)
        LENID = bytes(format(LENID, '03X'), "ASCII")

    #print("LENID: ", LENID)

    if LENID == b'000':
        LCHKSUM = '0'
    else:
        LCHKSUM = lchksum_calc(LENID)
        if LCHKSUM == False:
            return(False,"Error calculating LCHKSUM)")
    #print("LCHKSUM: ", LCHKSUM)
    request += bytes(LCHKSUM, "ASCII")
    request += LENID
    request += info
    CHKSUM = bytes(chksum_calc(request), "ASCII")
    if CHKSUM == False:
        return(False,"Error calculating CHKSUM)")
    request += CHKSUM
    request += b'\x0d'

    if debug_output > 2:
        print("-> Outgoing Data: ", request)

    if not bms_sendData(bms,request):
        bms_connected = False
        print("Error, connection to BMS lost")
        return(False,"Error, connection to BMS lost")

    inc_data = bms_get_data(bms)

    if inc_data == False:
        print("Error retrieving data from BMS")
        return(False,"Error retrieving data from BMS")

    if debug_output > 2:
        print("<- Incoming data: ", inc_data)

    success, INFO = bms_parse_data(inc_data)

    return(success, INFO)

def bms_getPackNumber(bms):

    success, INFO = bms_request(bms,cid2=constants.cid2PackNumber)

    if success == False:
        return(False,INFO)    

    try:
        packNumber = int(INFO,16)
    except:
        print("Error extracting total battery count in pack")
        return(False,"Error extracting total battery count in pack")

    return(success,packNumber)

def bms_getVersion(comms):

    global bms_version

    success, INFO = bms_request(bms,cid2=constants.cid2SoftwareVersion)

    if success == False:
        return(False,INFO)

    try:

        bms_version = bytes.fromhex(INFO.decode("ascii")).decode("ASCII")
        client.publish(config['mqtt_base_topic'] + "/bms_version",bms_version)
        print("BMS Version: " + bms_version)
    except:
        return(False,"Error extracting BMS version")

    return(success,bms_version)

def bms_getSerial(comms):

    global bms_sn
    global pack_sn

    success, INFO = bms_request(bms,cid2=constants.cid2SerialNumber)

    if success == False:
        print("Error: " + INFO)
        return(False,INFO, False)

    try:

        bms_sn = bytes.fromhex(INFO[0:30].decode("ascii")).decode("ASCII").replace(" ", "") #Remove spaces to prevent the unique ID having spaces
        pack_sn = bytes.fromhex(INFO[40:68].decode("ascii")).decode("ASCII").replace(" ", "")
        client.publish(config['mqtt_base_topic'] + "/bms_sn",bms_sn)
        client.publish(config['mqtt_base_topic'] + "/pack_sn",pack_sn)
        print("BMS Serial Number: " + bms_sn)
        print("Pack Serial Number: " + pack_sn)

    except:
        return(False,"Error extracting BMS version", False)

    return(success,bms_sn,pack_sn)

def bms_getAnalogData(bms,batNumber):

    global print_initial
    global cells
    global temps
    global packs
    byte_index = 2
    i_pack = []
    v_pack = []
    i_remain_cap = []
    i_design_cap = []
    cycles = []
    i_full_cap = []
    soc = []
    soh = []

    battery = bytes(format(batNumber, '02X'), 'ASCII')

    success, inc_data = bms_request(bms,cid2=constants.cid2PackAnalogData,info=battery)

    #bms_request -> bms_get_data(inc_data/INFO = bms_parse_data)

    #prefix: ~250146006118
    #To test set: inc_data = INFO
    #inc_data = b'000A100CF40CF40CF40CF50CF30CF40CF40CF30CF80CF30CF30CF30CF30CF50CF40CF4060B2E0B300B2D0B300B3B0B47FEFCCF406B58096D2700146D60626D606D606D606D6064D1180000100000000000000000000000000000000000000000000000000000000000000000060AAA0AAA0AAA0AAA0AAA0AAA000000000000090000000000006200000000000000006400000000100CF40CF40CF30CF40CF30CF40CF40CF40CF30CF30CF40CF40CF30CF30CF40CF2060B320B2F0B340B2C0B3D0B4AFEF6CF386B65096D2700146D60626D606D606D606D6064CF320000100CF30CF40CF40CF40CF40CF40CF40CF40CF40CF40CF40CF40CF40CF40CF40CF4060B330B320B2E0B340B410B48FEF9CF3F6B72096D2700146D60626D606D606D606D6064CFCC0000100CF40CF30CF40CF30CF40CF40CF30CF40CF30CF30CF30CF40CF30CF40CF30CF1060B330B2D0B2F0B340B3D0B48FF10CF646B7A096D2700146D60626D606D606D606D6064CFF70000100CF40CF30CF20CF20CF30CF20CF30CF10CF30CF30CF30CF20CF30CF30CF30CF1060B2D0B320B300B310B3C0B49FF11CF296B7F096D2A00136D60626D606D606D606D6064D0030000100CF40CF40CF40CF40CF40CF40CF40CF40CF40CF40CF40CF50CF40CF40CF40CF3060B310B2E0B310B2E0B400B4AFF1ACF4075580976EE00146D60636D606D606D606D6064CFD20000100CF30CF10CF40CF30CF30CF40CF30CF30CF10CF30CF40CF30CF30CF30CF30CF2060B300B2E0B2F0B330B3B0B42FF07CF636B50096D2400156D60626D606D606D606D6064CFCE0000100CF40CF40CF40CF40CF40CF40CF40CF40CF40CF40CF40CF40CF40CF40CF40CF3060B2B0B2D0B290B2F0B3B0B4BFF1BCF3F6B7F096D2D00126D60626D606D606D606D6064D1260000100CF40CF40CF40CF40CF40CF40CF40CF60CF30CF40CF40CF40CF40CF40CF40CF3060B2A0B2E0B2D0B2A0B390B43FF24CF406B5F096D2700146D60626D606D606D606D6064D0C70000'


    if success == False:
        return(False,inc_data)

    try:

        packs = int(inc_data[byte_index:byte_index+2],16)
        if print_initial:
            print("Packs: " + str(packs))
        byte_index += 2

        v_cell = {}
        t_cell = {}

        for p in range(1,packs+1):

            if p > 1:
                cells_prev = cells

            cells = int(inc_data[byte_index:byte_index+2],16)

            #Possible remove this next test as were now testing for the INFOFLAG at the end
            if p > 1:
                if cells != cells_prev:
                    byte_index += 2
                    cells = int(inc_data[byte_index:byte_index+2],16)
                    if cells != cells_prev:
                        print("Error parsing BMS analog data: Cannot read multiple packs")
                        return(False,"Error parsing BMS analog data: Cannot read multiple packs")

            if print_initial:
                print("Pack " + str(p).zfill(config['zero_pad_number_packs']) + ", Total cells: " + str(cells))
            byte_index += 2
            
            cell_min_volt = 0
            cell_max_volt = 0

            for i in range(0,cells):
                v_cell[(p-1,i)] = int(inc_data[byte_index:byte_index+4],16)
                byte_index += 4
                client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/v_cells/cell_" + str(i+1).zfill(config['zero_pad_number_cells']) ,str(v_cell[(p-1,i)]))
                if print_initial:
                    print("Pack " + str(p).zfill(config['zero_pad_number_packs']) +", V Cell" + str(i+1).zfill(config['zero_pad_number_cells']) + ": " + str(v_cell[(p-1,i)]) + " mV")

                #Calculate cell max and min volt
                if i == 0:
                    cell_min_volt = v_cell[(p-1,i)]
                    cell_max_volt = v_cell[(p-1,i)]
                else:
                    if v_cell[(p-1,i)] < cell_min_volt:
                        cell_min_volt = v_cell[(p-1,i)]
                    if v_cell[(p-1,i)] > cell_max_volt:
                        cell_max_volt = v_cell[(p-1,i)]
            
            #Calculate cells max diff volt
            cell_max_diff_volt = cell_max_volt - cell_min_volt
            client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/cells_max_diff_calc" ,str(cell_max_diff_volt))
            if print_initial:
                print("Pack " + str(p).zfill(config['zero_pad_number_packs']) +", Cell Max Diff Volt Calc: " + str(cell_max_diff_volt) + " mV")

            temps = int(inc_data[byte_index:byte_index + 2],16)
            if print_initial:
                print("Pack " + str(p).zfill(config['zero_pad_number_packs']) + ", Total temperature sensors: " + str(temps))
            byte_index += 2

            for i in range(0,temps): #temps-2
                t_cell[(p-1,i)] = (int(inc_data[byte_index:byte_index + 4],16)-2730)/10
                byte_index += 4
                client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/temps/temp_" + str(i+1) ,str(round(t_cell[(p-1,i)],1)))
                if print_initial:
                    print("Pack " + str(p).zfill(config['zero_pad_number_packs']) + ", Temp" + str(i+1) + ": " + str(round(t_cell[(p-1,i)],1)) + " ℃")

            # t_mos= (int(inc_data[byte_index:byte_index+4],16))/160-273
            # client.publish(config['mqtt_base_topic'] + "/t_mos",str(round(t_mos,1)))
            # if print_initial:
            #     print("T Mos: " + str(t_mos) + " Deg")

            # t_env= (int(inc_data[byte_index:byte_index+4],16))/160-273
            # client.publish(config['mqtt_base_topic'] + "/t_env",str(round(t_env,1)))
            # offset += 7
            # if print_initial:
            #     print("T Env: " + str(t_env) + " Deg")

            i_pack.append(int(inc_data[byte_index:byte_index+4],16))
            byte_index += 4
            if i_pack[p-1] >= 32768:
                i_pack[p-1] = -1*(65535 - i_pack[p-1])
            i_pack[p-1] = i_pack[p-1]/100
            client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/i_pack",str(i_pack[p-1]))
            if print_initial:
                print("Pack " + str(p).zfill(config['zero_pad_number_packs']) + ", I Pack: " + str(i_pack[p-1]) + " A")

            v_pack.append(int(inc_data[byte_index:byte_index+4],16)/1000)
            byte_index += 4
            client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/v_pack",str(v_pack[p-1]))
            if print_initial:
                print("Pack " + str(p).zfill(config['zero_pad_number_packs']) + ", V Pack: " + str(v_pack[p-1]) + " V")

            i_remain_cap.append(int(inc_data[byte_index:byte_index+4],16)*10)
            byte_index += 4
            client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/i_remain_cap",str(i_remain_cap[p-1]))
            if print_initial:
                print("Pack " + str(p).zfill(config['zero_pad_number_packs']) + ", I Remaining Capacity: " + str(i_remain_cap[p-1]) + " mAh")

            byte_index += 2 # Manual: Define number P = 3

            i_full_cap.append(int(inc_data[byte_index:byte_index+4],16)*10)
            byte_index += 4
            client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/i_full_cap",str(i_full_cap[p-1]))
            if print_initial:
                print("Pack " + str(p).zfill(config['zero_pad_number_packs']) + ", I Full Capacity: " + str(i_full_cap[p-1]) + " mAh")

            try:
                soc.append(round(i_remain_cap[p-1]/i_full_cap[p-1]*100,2))
                client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/soc",str(soc[p-1]))
                if print_initial:
                    print("Pack " + str(p).zfill(config['zero_pad_number_packs']) + ", SOC: " + str(soc[p-1]) + " %")
            except Exception as e:
                print("Error parsing BMS analog data, missing pack"  + str(p).zfill(config['zero_pad_number_packs']) + " full capacity: ", str(e))

            cycles.append(int(inc_data[byte_index:byte_index+4],16))
            byte_index += 4
            client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/cycles",str(cycles[p-1]))
            if print_initial:
                print("Pack " + str(p).zfill(config['zero_pad_number_packs']) + ", Cycles: " + str(cycles[p-1]))

            i_design_cap.append(int(inc_data[byte_index:byte_index+4],16)*10)
            byte_index += 4
            client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/i_design_cap",str(i_design_cap[p-1]))
            if print_initial:
                print("Pack " + str(p).zfill(config['zero_pad_number_packs']) + ", Design Capacity: " + str(i_design_cap[p-1]) + " mAh")

            try:
                soh.append(round(i_full_cap[p-1]/i_design_cap[p-1]*100,2))
                client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/soh",str(soh[p-1]))
                if print_initial:
                    print("Pack " + str(p).zfill(config['zero_pad_number_packs']) + ", SOH: " + str(soh[p-1]) + " %")
            except Exception as e:
                print("Error parsing BMS analog data, missing pack"  + str(p).zfill(config['zero_pad_number_packs']) + " design capacity: ", str(e))

            #byte_index += 2

            byte_index += int(config['force_pack_offset'])

            #Test for non signed value (matching cell count), to skip possible INFOFLAG present in data
            if p < packs: #Test - Is there more packs to read?
                while (byte_index < len(inc_data)) and (cells != int(inc_data[byte_index:byte_index+2],16)):
                    byte_index += 2
                    if byte_index > len(inc_data):
                        print("Error parsing BMS analog data: Cannot read multiple packs")
                        return(False,"Error parsing BMS analog data: Cannot read multiple packs")


    except Exception as e:
        print("Error parsing BMS analog data: ", str(e))
        return(False,"Error parsing BMS analog data: " + str(e))

    if print_initial:
        print("Script running....")

    return True,True

def bms_getPackCapacity(bms):

    byte_index = 0

    success, inc_data = bms_request(bms,cid2=constants.cid2PackCapacity) # Seem to always reply with pack 1 data, even with ADR= 0 or FF and INFO= '' or FF

    if success == False:
        return(False,inc_data)

    try:

        pack_remain_cap = int(inc_data[byte_index:byte_index+4],16)*10
        byte_index += 4
        client.publish(config['mqtt_base_topic'] + "/pack_remain_cap",str(pack_remain_cap))
        if print_initial:
            print("Pack Remaining Capacity: " + str(pack_remain_cap) + " mAh")

        pack_full_cap = int(inc_data[byte_index:byte_index+4],16)*10
        byte_index += 4
        client.publish(config['mqtt_base_topic'] + "/pack_full_cap",str(pack_full_cap))
        if print_initial:
            print("Pack Full Capacity: " + str(pack_full_cap) + " mAh")

        pack_design_cap = int(inc_data[byte_index:byte_index+4],16)*10
        byte_index += 4
        client.publish(config['mqtt_base_topic'] + "/pack_design_cap",str(pack_design_cap))
        if print_initial:
            print("Pack Design Capacity: " + str(pack_design_cap) + " mAh")

        pack_soc = round(pack_remain_cap/pack_full_cap*100,2)
        client.publish(config['mqtt_base_topic'] + "/pack_soc",str(pack_soc))
        if print_initial:
            print("Pack SOC: " + str(pack_soc) + " %")

        pack_soh = round(pack_full_cap/pack_design_cap*100,2)
        client.publish(config['mqtt_base_topic'] + "/pack_soh",str(pack_soh))
        if print_initial:
            print("Pack SOH: " + str(pack_soh) + " %")

    except Exception as e:
        print("Error parsing BMS pack capacity data: ", str(e))
        return False, "Error parsing BMS pack capacity data: " + str(e)

    return True,True

def bms_getWarnInfo(bms):

    byte_index = 2
    packsW = 1
    warnings = ""

    success, inc_data = bms_request(bms,cid2=constants.cid2WarnInfo,info=b'FF')

    if success == False:
        return(False,inc_data)

    #inc_data = b'000210000000000000000000000000000000000600000000000000000000000E0000000000001110000000000000000000000000000000000600000000000000000000000E00000000000000'
    

    try:

        packsW = int(inc_data[byte_index:byte_index+2],16)
        if print_initial:
            print("Packs for warnings: " + str(packs))
        byte_index += 2

        for p in range(1,packs+1):

            cellsW = int(inc_data[byte_index:byte_index+2],16)
            byte_index += 2

            for c in range(1,cellsW+1):

                if inc_data[byte_index:byte_index+2] != b'00':
                    warn = constants.warningStates[inc_data[byte_index:byte_index+2]]
                    warnings += "cell " + str(c) + " " + warn + ", "
                byte_index += 2

            tempsW = int(inc_data[byte_index:byte_index+2],16)
            byte_index += 2
        
            for t in range(1,tempsW+1):

                if inc_data[byte_index:byte_index+2] != b'00':
                    warn = constants.warningStates[inc_data[byte_index:byte_index+2]]
                    warnings += "temp " + str(t) + " " + warn + ", "
                byte_index += 2

            if inc_data[byte_index:byte_index+2] != b'00':
                warn = constants.warningStates[inc_data[byte_index:byte_index+2]]
                warnings += "charge current " + warn + ", "
            byte_index += 2

            if inc_data[byte_index:byte_index+2] != b'00':
                warn = constants.warningStates[inc_data[byte_index:byte_index+2]]
                warnings += "total voltage " + warn + ", "
            byte_index += 2

            if inc_data[byte_index:byte_index+2] != b'00':
                warn = constants.warningStates[inc_data[byte_index:byte_index+2]]
                warnings += "discharge current " + warn + ", "
            byte_index += 2

            protectState1 = ord(bytes.fromhex(inc_data[byte_index:byte_index+2].decode('ascii')))
            if protectState1 > 0:
                warnings += "Protection State 1: "
                for x in range(0,8):
                    if (protectState1 & (1<<x)):
                        warnings += constants.protectState1[x+1] + " | "
                warnings = warnings.rstrip("| ")
                warnings += ", "
            client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/prot_short_circuit",str(protectState1>>6 & 1))  
            client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/prot_discharge_current",str(protectState1>>5 & 1))  
            client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/prot_charge_current",str(protectState1>>4 & 1))  
            byte_index += 2

            protectState2 = ord(bytes.fromhex(inc_data[byte_index:byte_index+2].decode('ascii')))
            if protectState2 > 0:
                warnings += "Protection State 2: "
                for x in range(0,8):
                    if (protectState2 & (1<<x)):
                        warnings += constants.protectState2[x+1] + " | "
                warnings = warnings.rstrip("| ")
                warnings += ", "
            client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/fully",str(protectState2>>7 & 1))  
            byte_index += 2

            # instructionState = ord(bytes.fromhex(inc_data[byte_index:byte_index+2].decode('ascii')))
            # if instructionState > 0:
            #     warnings += "Instruction State: "
            #     for x in range(0,8):
            #         if (instructionState & (1<<x)):
            #              warnings += constants.instructionState[x+1] + " | "
            #     warnings = warnings.rstrip("| ")
            #     warnings += ", "  
            # byte_index += 2

            instructionState = ord(bytes.fromhex(inc_data[byte_index:byte_index+2].decode('ascii')))
            client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/current_limit",str(instructionState>>0 & 1))
            client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/charge_fet",str(instructionState>>1 & 1))
            client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/discharge_fet",str(instructionState>>2 & 1))
            client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/pack_indicate",str(instructionState>>3 & 1))
            client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/reverse",str(instructionState>>4 & 1))
            client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/ac_in",str(instructionState>>5 & 1))
            client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/heart",str(instructionState>>7 & 1))
            byte_index += 2

            controlState = ord(bytes.fromhex(inc_data[byte_index:byte_index+2].decode('ascii')))
            if controlState > 0:
                warnings += "Control State: "
                for x in range(0,8):
                    if (controlState & (1<<x)):
                        warnings += constants.controlState[x+1] + " | "
                warnings = warnings.rstrip("| ")
                warnings += ", "  
            byte_index += 2

            faultState = ord(bytes.fromhex(inc_data[byte_index:byte_index+2].decode('ascii')))
            if faultState > 0:
                warnings += "Fault State: "
                for x in range(0,8):
                    if (faultState & (1<<x)):
                        warnings += constants.faultState[x+1] + " | "
                warnings = warnings.rstrip("| ")
                warnings += ", "  
            byte_index += 2

            balanceState1 = '{0:08b}'.format(int(inc_data[byte_index:byte_index+2],16))
            byte_index += 2

            balanceState2 = '{0:08b}'.format(int(inc_data[byte_index:byte_index+2],16))
            byte_index += 2

            warnState1 = ord(bytes.fromhex(inc_data[byte_index:byte_index+2].decode('ascii')))
            if warnState1 > 0:
                warnings += "Warning State 1: "
                for x in range(0,8):
                    if (warnState1 & (1<<x)):
                        warnings += constants.warnState1[x+1] + " | "
                warnings = warnings.rstrip("| ")
                warnings += ", "  
            byte_index += 2

            warnState2 = ord(bytes.fromhex(inc_data[byte_index:byte_index+2].decode('ascii')))
            if warnState2 > 0:
                warnings += "Warning State 2: "
                for x in range(0,8):
                    if (warnState2 & (1<<x)):
                        warnings += constants.warnState2[x+1] + " | "
                warnings = warnings.rstrip("| ")
                warnings += ", "  
            byte_index += 2

            warnings = warnings.rstrip(", ")

            client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/warnings",warnings)
            if print_initial:
                print("Pack " + str(p).zfill(config['zero_pad_number_packs']) + ", warnings: " + warnings)

            client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/balancing1",balanceState1)
            if print_initial:
                print("Pack " + str(p).zfill(config['zero_pad_number_packs']) + ", balancing1: " + balanceState1)

            client.publish(config['mqtt_base_topic'] + "/pack_" + str(p).zfill(config['zero_pad_number_packs']) + "/balancing2",balanceState2)
            if print_initial:
                print("Pack " + str(p).zfill(config['zero_pad_number_packs']) + ", balancing2: " + balanceState2)

            warnings = ""

            #Test for non signed value (matching cell count), to skip possible INFOFLAG present in data
            if (byte_index < len(inc_data)) and (cellsW != int(inc_data[byte_index:byte_index+2],16)):
                byte_index += 2

    except Exception as e:
        print("Error parsing BMS warning data: ", str(e))
        return False, "Error parsing BMS warning data: " + str(e)

    return True,True


print("Connecting to BMS...")
bms,bms_connected = bms_connect(config['bms_ip'],config['bms_port'])

client.publish(config['mqtt_base_topic'] + "/availability","offline")
print_initial = True

success, data = bms_getVersion(bms)
if success != True:
    print("Error retrieving BMS version number")

time.sleep(0.1)
success, bms_sn,pack_sn = bms_getSerial(bms)

if success != True:
    print("Error retrieving BMS and pack serial numbers. This is required for HA Discovery. Exiting...")
    quit()


while code_running == True:

    if bms_connected == True:
        if mqtt_connected == True:

            success, data = bms_getAnalogData(bms,batNumber=255)
            if success != True:
                print("Error retrieving BMS analog data: " + data)
            time.sleep(scan_interval/3)
            success, data = bms_getPackCapacity(bms)
            if success != True:
                print("Error retrieving BMS pack capacity: " + data)
            time.sleep(scan_interval/3)
            success, data = bms_getWarnInfo(bms)
            if success != True:
                print("Error retrieving BMS warning info: " + data)
            time.sleep(scan_interval/3)

            if print_initial:
                ha_discovery()
                
            client.publish(config['mqtt_base_topic'] + "/availability","online")

            print_initial = False
            

            repub_discovery += 1
            if repub_discovery*scan_interval > 3600:
                repub_discovery = 0
                print_initial = True
        
        else: #MQTT not connected
            client.loop_stop()
            print("MQTT disconnected, trying to reconnect...")
            client.connect(config['mqtt_host'], config['mqtt_port'], 60)
            client.loop_start()
            time.sleep(5)
            print_initial = True
    else: #BMS not connected
        print("BMS disconnected, trying to reconnect...")
        bms,bms_connected = bms_connect(config['bms_ip'],config['bms_port'])
        client.publish(config['mqtt_base_topic'] + "/availability","offline")
        time.sleep(5)
        print_initial = True

client.loop_stop()
