EESchema Schematic File Version 4
LIBS:power
LIBS:device
LIBS:Connector_Generic
EELAYER 29 0
EELAYER END
$Descr A4 11693 8268
Sheet 1 1
Title "IchiPing UNO Q Audio Shield"
Date "2026-08-24"
Rev "A"
Comp "IchiPing UNO Q"
Comment1 "XH2.54 vertical pin order is top-view pin 1 to pin N"
$EndDescr
Text Notes 900 800 0    100  ~ 20
IchiPing UNO Q Audio Shield
Text Notes 900 1050 0    60   ~ 12
J15-32/34/36/38 = CLK/WS/DATA0/DATA1; J14 supplies +1V8 and +5V.
$Comp
L Connector_Generic:Conn_01x04 J_AMP_SIG
U 1 1 95879501
P 1700 1700
F 0 "J_AMP_SIG" H 1580 2050 50  0000 C CNN
F 1 "XH2.54_VERTICAL_4" H 1580 1350 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical" H 1700 1700 50  0001 C CNN
F 3 "~" H 1700 1700 50  0001 C CNN
	1    1700 1700
	-1   0    0    1
$EndComp
Wire Wire Line
	1800 1550 2350 1550
Text Label 2000 1550 0    45   ~ 0
MI2S0_WS
Text Notes 800 1565 0    45   ~ 0
1: MI2S0_WS
Wire Wire Line
	1800 1650 2350 1650
Text Label 2000 1650 0    45   ~ 0
MI2S0_CLK
Text Notes 800 1665 0    45   ~ 0
2: MI2S0_CLK
Wire Wire Line
	1800 1750 2350 1750
Text Label 2000 1750 0    45   ~ 0
MI2S0_DATA1
Text Notes 800 1765 0    45   ~ 0
3: MI2S0_DATA1
Wire Wire Line
	1800 1850 2350 1850
Text Label 2000 1850 0    45   ~ 0
AMP_GAIN
Text Notes 800 1865 0    45   ~ 0
4: AMP_GAIN
$Comp
L Connector_Generic:Conn_01x03 J_AMP_PWR
U 1 1 7681F8F5
P 4300 1700
F 0 "J_AMP_PWR" H 4180 2050 50  0000 C CNN
F 1 "XH2.54_VERTICAL_3" H 4180 1350 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical" H 4300 1700 50  0001 C CNN
F 3 "~" H 4300 1700 50  0001 C CNN
	1    4300 1700
	-1   0    0    1
$EndComp
Wire Wire Line
	4400 1600 4950 1600
Text Label 4600 1600 0    45   ~ 0
AMP_SD
Text Notes 3400 1615 0    45   ~ 0
1: AMP_SD
Wire Wire Line
	4400 1700 4950 1700
Text Label 4600 1700 0    45   ~ 0
GND
Text Notes 3400 1715 0    45   ~ 0
2: GND
Wire Wire Line
	4400 1800 4950 1800
Text Label 4600 1800 0    45   ~ 0
+5V
Text Notes 3400 1815 0    45   ~ 0
3: +5V
$Comp
L Connector_Generic:Conn_01x06 J_MIC
U 1 1 481F479B
P 6900 1700
F 0 "J_MIC" H 6780 2050 50  0000 C CNN
F 1 "XH2.54_VERTICAL_6" H 6780 1350 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical" H 6900 1700 50  0001 C CNN
F 3 "~" H 6900 1700 50  0001 C CNN
	1    6900 1700
	-1   0    0    1
$EndComp
Wire Wire Line
	7000 1450 7550 1450
Text Label 7200 1450 0    45   ~ 0
GND
Text Notes 6000 1465 0    45   ~ 0
1: GND
Wire Wire Line
	7000 1550 7550 1550
Text Label 7200 1550 0    45   ~ 0
+1V8
Text Notes 6000 1565 0    45   ~ 0
2: +1V8
Wire Wire Line
	7000 1650 7550 1650
Text Label 7200 1650 0    45   ~ 0
MI2S0_DATA0
Text Notes 6000 1665 0    45   ~ 0
3: MI2S0_DATA0
Wire Wire Line
	7000 1750 7550 1750
Text Label 7200 1750 0    45   ~ 0
MI2S0_CLK
Text Notes 6000 1765 0    45   ~ 0
4: MI2S0_CLK
Wire Wire Line
	7000 1850 7550 1850
Text Label 7200 1850 0    45   ~ 0
MI2S0_WS
Text Notes 6000 1865 0    45   ~ 0
5: MI2S0_WS
Wire Wire Line
	7000 1950 7550 1950
Text Label 7200 1950 0    45   ~ 0
MIC_LR
Text Notes 6000 1965 0    45   ~ 0
6: MIC_LR
$Comp
L Connector_Generic:Conn_01x02 SJ_MUTE
U 1 1 0CC8DFD7
P 1700 3400
F 0 "SJ_MUTE" H 1580 3750 50  0000 C CNN
F 1 "XH2.54_VERTICAL_2" H 1580 3050 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" H 1700 3400 50  0001 C CNN
F 3 "~" H 1700 3400 50  0001 C CNN
	1    1700 3400
	-1   0    0    1
$EndComp
Wire Wire Line
	1800 3350 2350 3350
Text Label 2000 3350 0    45   ~ 0
AMP_SD
Text Notes 800 3365 0    45   ~ 0
1: AMP_SD
Wire Wire Line
	1800 3450 2350 3450
Text Label 2000 3450 0    45   ~ 0
GND
Text Notes 800 3465 0    45   ~ 0
2: GND
$EndSCHEMATC
