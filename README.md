# BMS Pace - Home Assistant Add-on
Pace Battery Management System

## Important

This addon comes with absolutely no guarantees whatsoever. Use at own risk.  
Feel free to fork and expand!


## RJ11 Interface

When viewed into the RJ11 socket, tab to the bottom, pins are (in my device) ordered:  
1:NC 2:GND 3:BMS_Tx 4:BMS_Rx 5:GND 6:NC

Either a direct serial interface from your hardware, a USB to serial, or a network connected TCP server device will work. 
Note the voltage levels are normal RS232 (and not TTL / 5V or something else). 
