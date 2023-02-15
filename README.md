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

## Important

This addon comes with absolutely no guarantees whatsoever. Use at own risk.  
Feel free to fork and expand!

## Confirmed working with
* Hubble Lithium (AM2, AM4)
* Revov R100
* let me know if yours work

## Configuring
### --- Manually ---
Install the pre-requisites as per requirements.txt. Then edit the config.yaml file to suit your needs and run the script bms.py
NB: Test with Python 3.9

### --- Home Assistant ---
All configuration options are available from within Home Assistant.

### --- Notes on configuration options ---
debug_output: Options are 0 for minimal, 1 for minor errors such as checksums, 2-3 for more severe debug logs.

## RJ11 Interface (for Hubble AM2 and AM4)

When viewed into the RJ11 socket, tab to the bottom, pins are (in Hubble AM2 and AM4) ordered:  
1:NC 2:GND 3:BMS_Tx 4:BMS_Rx 5:GND 6:NC

Either a direct serial interface from your hardware, a USB to serial, or a network connected TCP server device will work. 
Note the voltage levels are normal RS232 (and not TTL / 5V or something else). 
