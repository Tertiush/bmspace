

cid2PackNumber          = b"\x39\x30"       # 0x90
cid2PackAnalogData      = b"\x34\x32"       # 0x42
cid2SoftwareVersion     = b"\x43\x31"       # 0xC1
cid2SerialNumber        = b"\x43\x32"       # 0xC2
cid2PackCapacity        = b"\x41\x36"       # 0xA6
cid2WarnInfo            = b"\x34\x34"       # 0x44


warningStates = {   b'00': "Normal",
                    b'01': "< low limit",
                    b'02': "> up limit",
                    b'F0': "other fault"} # 80H～EFH：user defined

protectState1 = {   1: "Above cell volt protect",
                    2: "Lower cell volt protect",
                    3: "Above total volt protect",
                    4: "Lower total volt protect",
                    5: "Charge current protect",
                    6: "Discharge current protect",
                    7: "Short circuit",
                    8: "undefined"}

protectState2 = {   1: "Above charge temp protect",
                    2: "Above discharge temp protect",
                    3: "Lower charge temp protect",
                    4: "Lower discharge temp protect",
                    5: "Above MOS temp protect",
                    6: "Above Env temp protect",
                    7: "Lower Env temp protect",
                    8: "Fully"}

instructionState = {1: "Current limit indicate ON",
                    2: "CFET indicate ON",
                    3: "DFET indicate ON",
                    4: "Pack indicate ON",
                    5: "Reverse indicate ON",
                    6: "ACin ON",
                    7: "Undefined",
                    8: "Heart indicate ON"}

controlState =     {1: "Buzzer warn function enabled",
                    2: "undefined",
                    3: "undefined",
                    4: "Current limit gear => low gear",
                    5: "Current limit function disabled",
                    6: "LED warn functiuon disabled",
                    7: "Undefined",
                    8: "Undefined"}

faultState =       {1: "Charge MOS fault",
                    2: "Discharge MOS fault",
                    3: "NTC fault (NTC)",
                    4: "Undefined",
                    5: "Cell fault",
                    6: "Sample fault",
                    7: "Undefined",
                    8: "Undefined"}

warnState1 =       {1: "Above cell volt warn",
                    2: "Lower cell volt warn",
                    3: "Above total volt warn",
                    4: "Lower total volt warn",
                    5: "Charge current warn",
                    6: "Discharge current warn",
                    7: "Undefined",
                    8: "Undefined"}

warnState2 =       {1: "Above charge temp warn",
                    2: "Above discharge temp warn",
                    3: "Low charge temp warn",
                    4: "Low discharge temp warn",
                    5: "High env temp warn",
                    6: "Low env temp warn",
                    7: "High MOS temp warn",
                    8: "Low power warn"}