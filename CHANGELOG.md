WARNING: Breaking Changes! As of version 2.0.0 each pack (battery) will be pre-fixed with its pack number. 
<br>
Use at own risk!! 
<br>
This is to support multiple packs. 
<br>
Additional data is now being retrieved, including warning, balancing, status indications, etc. 
<br>
This script excludes COMMANDS and should only retrieve data. Nonetheless the author accepts no reponsibility whatsoever of your use, in any way, of this script / addon. Again, USE AT OWN RISK!
<br>
<br>
2.0.0: Major rewrite using the official Pace RS232 Protocol Definition. Breaking Changes including prefixing most data with its Pack number (to support multiple batteries in parallel).
<br>
<br>
Known / possible issues: The overall Pack data collected under the root MQTT topic seems to follow the data of the first battery in the Pack.