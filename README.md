# BMS Pace - Python data retrieval
Pace Battery Management System
Features:
* Compatible as a Home Assistant Add-on, see https://www.home-assistant.io/common-tasks/os#installing-third-party-add-ons
* Cell voltages
* Temperatures
* State of charge (SOC)
* State of health (SOH)
* Warnings & faults
* State indications
* Cell balancing state
* and many more.....

## 1. Important

This addon comes with absolutely no guarantees whatsoever. Use at own risk.  
Feel free to fork and expand!

## 2. Confirmed working with
Many brands using the PACE BMS, including:
* Greenrich U-P5000
* Hubble Lithium (AM2, AM4, X-101)
* Revov R100, R9
* SOK 48V (100Ah)
* YouthPower Rack Module 48V 100AH 4U-5U Lifepo4
* Allith 10kW LifePo4
* Joyvoit BW5KW
* etc.......

If your ports look something like this, its likely a PACE BMS:

![PACE BMS Ports](https://github.com/Tertiush/bmspace/blob/main/pace-bms-ports.png?raw=true)

## 3. Configuring
**Currently the DEV version is the most capable, and should work for most.**
### 3.1 Manually
Install the pre-requisites as per requirements.txt. Then edit the config.yaml file to suit your needs and run the script bms.py
NB: Tested with Python 3.9. Should work on later version as well.

### 3.2 Home Assistant
All configuration options are available from within Home Assistant.

### 3.3 Notes on configuration options
* **debug_output**: Options are 0 for minimal, 1 for minor errors such as checksums, 2-3 for more severe debug logs.
* **force_pack_offset**: This is currently available in the development version. This offset is used to force a defined offset between the data read from **multiple packs**. If you have more than one pack and only the first is read successfully, you can force an offset here to get subsequent packs to read in successfully. Default is 0, multiple of 2 (e.g. 2, 4, 6....) may work. As large as 20 has been used in one instance.
* **zero_pad_number_cells**: Adds leading 0's to the cell voltages, forcing then to display sequential in some dasboarding tools. E.g. setting this to 2 will display voltages as cell_01 rahter than cell_1.
* **zero_pad_number_packs**: Same as for _cells padding above.

## 4. RJ11 Interface (Typical, confirm your own model!)

When viewed into the RJ11 socket, tab to the bottom, pins are ordered:  
1:NC 2:GND 3:BMS_Tx 4:BMS_Rx 5:GND 6:NC

Either a direct serial interface from your hardware, a USB to serial, or a network connected TCP server device will work. 
Note the voltage levels are normal RS232 (and not TTL / 5V or something else). 
