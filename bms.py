#Todo: availability offline

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


print("Starting up...")

config = {}

# with open(r'config.yaml') as file:
#     config = yaml.load(file, Loader=yaml.FullLoader)['options']


with open(r'/data/options.json') as file:
    config = json.load(file)
    print("Config: " + json.dmps(config))


scan_interval = config['scan_interval']
connection_type = config['connection_type']
bms_serial = config['bms_serial']
ha_discovery_enabled = config['mqtt_ha_discovery']
code_running = True
bms_connected = False
mqtt_connected = False
print_initial = True
disc_payload = {}

bms_version = ''
bms_sn = ''
cells = 13
temps = 4
v_cell = []
t_cell = []
t_mos = 0
t_env = 0
i_pack = 0
v_pack = 0
i_cap = 0
soh = 0
cycles = 0
i_full = 0
soc = 0
flags = []

print("Connection Type: " + connection_type)

def on_connect(client, userdata, flags, rc):
    print("MQTT connected with result code "+str(rc))
    global mqtt_connected
    mqtt_connected = True

def on_disconnect(client, userdata, rc):
    print("MQTT disconnected with result code "+str(rc))
    global mqtt_connected
    mqtt_connected = False


client = mqtt.Client()
client.on_connect = on_connect
client.on_disconnect = on_disconnect
#client.on_message = on_message

client.username_pw_set(username=config['mqtt_user'], password=config['mqtt_password'])
client.connect(config['mqtt_host'], config['mqtt_port'], 60)
client.loop_start()
time.sleep(2)

def exit_handler():
    
    client.publish(config['mqtt_base_topic'] + "/availability","offline")
    return


def bms_connect(address, port):

    if connection_type == "Serial":

        try:
            print("trying to connect %s" % bms_serial)
            s = serial.Serial(bms_serial,timeout = 1)
            print("BMS serial connected")
            return s, True
        except IOError as msg:
            print("BMS socket error connecting: %s" % msg)
            return False, False    

    else:

        try:
            print("trying to connect %s" % address)
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
            global bms_connected
            return False

    else:

        try:
            if len(request) > 0:
                comms.send(request)
                time.sleep(0.25)
                return True
        except Exception as e:
            print("BMS socket error: %s" % e)
            global bms_connected
            return False

def bms_get_data(comms,len):

    if connection_type == "Serial":
        inc_data = comms.readline()
    else:
        inc_data = comms.recv(1024)

    return inc_data


def get_bms_version(comms):

    global bms_version

    message = b"\x7e\x32\x35\x30\x31\x34\x36\x43\x31\x30\x30\x30\x30\x46\x44\x39\x41\x0d"
    if not bms_sendData(bms,message):
        bms_connected = False
        return
 
    #inc_data = bms.recv(1024)
    inc_data = bms_get_data(bms,1024)

    bms_version = bytes.fromhex(inc_data[13:53].decode("ascii")).decode("ASCII")
    client.publish(config['mqtt_base_topic'] + "/bms_version",bms_version)
    print("BMS Version: " + bms_version)
    return

def get_bms_sns(comms):

    global bms_sn

    message = b"\x7e\x32\x35\x30\x31\x34\x36\x43\x32\x30\x30\x30\x30\x46\x44\x39\x39\x0d"
    if not bms_sendData(bms,message):
        bms_connected = False
        return

    #inc_data = bms.recv(1024)
    inc_data = bms_get_data(bms,1024)

    bms_sn = bytes.fromhex(inc_data[13:43].decode("ascii")).decode("ASCII")
    pack_sn = bytes.fromhex(inc_data[53:81].decode("ascii")).decode("ASCII")
    client.publish(config['mqtt_base_topic'] + "/bms_sn",bms_sn)
    client.publish(config['mqtt_base_topic'] + "/pack_sn",pack_sn)
    print("BMS Serial Number: " + bms_sn)
    print("Pack Serial Number: " + pack_sn)
    return

def get_bms_data(comms):

    global print_initial
    global cells
    global temps

    message = b"\x7e\x32\x35\x30\x31\x34\x36\x34\x32\x45\x30\x30\x32\x30\x31\x46\x44\x33\x30\x0d"
    if not bms_sendData(comms,message):
        bms_connected = False
        return

    inc_data = bms_get_data(bms,1024)

    cells = int(inc_data[17:19],16)
    if print_initial:
        print("Cells: " + str(cells))
    
    for i in range(0,cells):
        v_cell.append(int(inc_data[19+i*4:23+i*4],16))
        test = inc_data[19+i*4:23+i*4]
        client.publish(config['mqtt_base_topic'] + "/v_cells/cell_" + str(i+1) ,str(v_cell[i]))
        if print_initial:
            print("V Cell" + str(i+1) + ": " + str(v_cell[i]) + " mV")

    temps = int(inc_data[23+(cells-1)*4:23+(cells-1)*4+2],16)

    if print_initial:
        print("Temperature Sensors: " + str(temps))

    for i in range(0,temps-2):
        t_cell.append((int(inc_data[23+cells*4-1+i*4:27+cells*4-1+i*4],16))/160-273)
        client.publish(config['mqtt_base_topic'] + "/t_cells/cell_" + str(i+1) ,str(round(t_cell[i],1)))
        offset = 27+cells*4-1+i*4
        if print_initial:
            print("T Cell" + str(i+1) + ": " + str(t_cell[i]) + " Deg")

    t_mos= (int(inc_data[offset:offset+4],16))/160-273
    client.publish(config['mqtt_base_topic'] + "/t_mos",str(round(t_mos,1)))
    if print_initial:
        print("T Mos: " + str(t_mos) + " Deg")

    t_env= (int(inc_data[offset+4:offset+8],16))/160-273
    client.publish(config['mqtt_base_topic'] + "/t_env",str(round(t_env,1)))
    offset += 7
    if print_initial:
        print("T Env: " + str(t_env) + " Deg")

    i_pack= int(inc_data[offset:offset+4],16)
    if i_pack >= 32768:
        i_pack = -1*(65535 - i_pack)
    i_pack = i_pack/100
    client.publish(config['mqtt_base_topic'] + "/pack/i_pack",str(i_pack))
    if print_initial:
        print("I Pack: " + str(i_pack) + " A")

    v_pack= int(inc_data[offset+4:offset+8],16)/1000
    client.publish(config['mqtt_base_topic'] + "/pack/v_pack",str(v_pack))
    if print_initial:
        print("V Pack: " + str(v_pack) + " V")

    i_cap= int(inc_data[offset+8:offset+12],16)*10
    client.publish(config['mqtt_base_topic'] + "/pack/i_cap",str(i_cap))
    if print_initial:
        print("I Capacity: " + str(i_cap) + " mAh")

    soh= int(inc_data[offset+14:offset+18],16)/100
    client.publish(config['mqtt_base_topic'] + "/pack/soh",str(soh))
    if print_initial:
        print("SOH: " + str(soh) + " %")

    cycles= int(inc_data[offset+18:offset+22],16)
    client.publish(config['mqtt_base_topic'] + "/pack/cycles",str(cycles))
    if print_initial:
        print("Cycles: " + str(cycles))

    i_full= int(inc_data[offset+22:offset+26],16)*10
    client.publish(config['mqtt_base_topic'] + "/pack/i_full",str(i_full))
    if print_initial:
        print("I Full: " + str(i_full) + " mAh")

    soc= int(inc_data[offset+26:offset+28],16)
    client.publish(config['mqtt_base_topic'] + "/pack/soc",str(soc))
    if print_initial:
        print("SOC: " + str(soc) + " %")

    if print_initial:
        print("Script running....")

    return


while bms_connected == False:

    client.publish(config['mqtt_base_topic'] + "/availability","offline")

    bms,bms_connected = bms_connect(config['bms_ip'],config['bms_port'])

    if bms_connected == False:
        print("Retrying BMS connection in 10 seconds...")
        time.sleep(10)
        

get_bms_version(bms)
get_bms_sns(bms)

def ha_discovery():

    global ha_discovery_enabled

    if ha_discovery_enabled:
        
        print("Publishing HA Discovery topic...")

        disc_payload['availability_topic'] = config['mqtt_base_topic'] + "/availability"

        device = {}
        device['manufacturer'] = "BMS Pace"
        device['model'] = "AM-x"
        device['identifiers'] = "bmspace_" + bms_sn
        device['name'] = "Hubble Lithium"
        device['sw_version'] = bms_version
        disc_payload['device'] = device

        for i in range(0,cells):
            disc_payload['name'] = "Cell_" + str(i+1) + "_Voltage"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_v_cell_" + str(i+1)
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/v_cells/cell_" + str(i+1)
            disc_payload['unit_of_measurement'] = "mV"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'] + "/config",json.dumps(disc_payload),qos=0, retain=True)

        for i in range(0,temps-2):
            disc_payload['name'] = "Cell_" + str(i+1) + "_Temp"
            disc_payload['unique_id'] = "bmspace_" + bms_sn + "_t_cell_" + str(i+1)
            disc_payload['state_topic'] = config['mqtt_base_topic'] + "/t_cells/cell_" + str(i+1)
            disc_payload['unit_of_measurement'] = "°C"
            client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'] + "/config",json.dumps(disc_payload),qos=0, retain=True)

        disc_payload['name'] = "MOS_Temp"
        disc_payload['unique_id'] = "bmspace_" + bms_sn + "_t_mos"
        disc_payload['state_topic'] = config['mqtt_base_topic'] + "/t_mos"
        disc_payload['unit_of_measurement'] = "°C"
        client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'] + "/config",json.dumps(disc_payload),qos=0, retain=True)

        disc_payload['name'] = "Environmental_Temp"
        disc_payload['unique_id'] = "bmspace_" + bms_sn + "_t_env"
        disc_payload['state_topic'] = config['mqtt_base_topic'] + "/t_env"
        disc_payload['unit_of_measurement'] = "°C"
        client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'] + "/config",json.dumps(disc_payload),qos=0, retain=True)

        disc_payload['name'] = "Pack_Current"
        disc_payload['unique_id'] = "bmspace_" + bms_sn + "_i_pack"
        disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack/i_pack"
        disc_payload['unit_of_measurement'] = "A"
        client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'] + "/config",json.dumps(disc_payload),qos=0, retain=True)

        disc_payload['name'] = "Pack_Voltage"
        disc_payload['unique_id'] = "bmspace_" + bms_sn + "_v_pack"
        disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack/v_pack"
        disc_payload['unit_of_measurement'] = "V"
        client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'] + "/config",json.dumps(disc_payload),qos=0, retain=True)

        disc_payload['name'] = "Pack_Capacity"
        disc_payload['unique_id'] = "bmspace_" + bms_sn + "_i_cap"
        disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack/i_cap"
        disc_payload['unit_of_measurement'] = "mAh"
        client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'] + "/config",json.dumps(disc_payload),qos=0, retain=True)

        disc_payload['name'] = "Pack_State_of_Health"
        disc_payload['unique_id'] = "bmspace_" + bms_sn + "_soh"
        disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack/soh"
        disc_payload['unit_of_measurement'] = "%"
        client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'] + "/config",json.dumps(disc_payload),qos=0, retain=True)

        disc_payload['name'] = "Pack_Cycles"
        disc_payload['unique_id'] = "bmspace_" + bms_sn + "_cycles"
        disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack/cycles"
        disc_payload['unit_of_measurement'] = ""
        client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'] + "/config",json.dumps(disc_payload),qos=0, retain=True)

        disc_payload['name'] = "Pack_Full_Capacity"
        disc_payload['unique_id'] = "bmspace_" + bms_sn + "_i_full"
        disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack/i_full"
        disc_payload['unit_of_measurement'] = "mAh"
        client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'] + "/config",json.dumps(disc_payload),qos=0, retain=True)

        disc_payload['name'] = "Pack_State_of_Charge"
        disc_payload['unique_id'] = "bmspace_" + bms_sn + "_soc"
        disc_payload['state_topic'] = config['mqtt_base_topic'] + "/pack/soc"
        disc_payload['unit_of_measurement'] = "%"
        client.publish(config['mqtt_ha_discovery_topic']+"/sensor/BMS-" + bms_sn + "/" + disc_payload['name'] + "/config",json.dumps(disc_payload),qos=0, retain=True)
    else:
        print("HA Discovery Disabled")

atexit.register(exit_handler)

while code_running == True:

    if bms_connected == True:
        if mqtt_connected == True:
            get_bms_data(bms)

            if print_initial:
                ha_discovery()
                client.publish(config['mqtt_base_topic'] + "/availability","online")

            print_initial = False
            time.sleep(scan_interval)
        
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
        print_initial = True

client.loop_stop()
