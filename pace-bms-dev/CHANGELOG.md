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
<h2>Development Version:</h2>

2.3dev - Added optional zero(0) padding for pack and cell values, to help maintain ordering. If used your history will be spread across the old and new names!

Added nested exception catches that might help the script not fail if a pack is missing.


<h1>Known / possible issues</h1>
The overall Pack data collected under the root MQTT topic seems to follow the data of the first battery in the Pack.