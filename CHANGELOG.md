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
<h1>Changelog</h1>
<h2>v2.2.0</h2>
Added a calculated cell maximum voltage difference (highest cell voltage - smallest cell voltage)
Rewrite Dockerfile to cache library dependencies to speed up future builds. (thanks jpmeijers)
Add docker-compose.yaml to run using docker compose, with auto restarting. (thanks jpmeijers)
Bugfix - Removing any spaces in the serial numbers to prevent HA unique identifiers having spaces
<h2>v2.1.0</h2>
Fix for multiple packs not parsed correctly in some instances. 
Abbreviated some warning info to help prevent exceeding HAs character limits
<h2>v2.0.4</h2>
Balance data should be base 16, not 8.
<h2>v2.0.3</h2>
Possible bugfix for larger banks reading incorrect analog data
<h2>v2.0.2</h2>
Naming fixes. Possible fix for native and USB serial devices
<h2>v2.0.1</h2>
Bug fixs
<h2>v2.0.0</h2> Major rewrite using the official Pace RS232 Protocol Definition. Breaking changes including prefixing most data with its Pack number (to support multiple batteries in parallel). Temperatures values are now retrieved without names, in my case the first 4 values are cell temperatures, temp 5 the MOSFET, and temp 6 is ambient / environment.
<h1>Known / possible issues</h1>
The overall Pack data collected under the root MQTT topic seems to follow the data of the first battery in the Pack.