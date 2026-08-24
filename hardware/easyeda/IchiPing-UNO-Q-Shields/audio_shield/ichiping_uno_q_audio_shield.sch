EESchema Schematic File Version 4
LIBS:ichiping_uno_q_audio_shield-cache
LIBS:power
LIBS:device
LIBS:Connector_Generic
EELAYER 29 0
EELAYER END
$Descr A4 11693 8268
Sheet 1 1
Title "IchiPing UNO Q Audio Shield"
Date "2026-08-25"
Rev "B"
Comp "IchiPing UNO Q"
Comment1 "Complete circuit; all discrete parts are through-hole"
$EndDescr
Text Notes 700 650 0    100  ~ 20
IchiPing UNO Q Audio Shield - complete circuit
Text Notes 700 900 0    55   ~ 11
QRB2210 MI2S0 is 1.8 V logic. Confirm Device Tree and ALSA direction before fitting modules.
$Comp
L Connector_Generic:Conn_02x20_Odd_Even J14
U 1 1 45E5478E
P 1700 3000
F 0 "J14" H 1900 3150 50  0000 C CNN
F 1 "UNO Breakout Carrier" H 2050 2850 50  0000 C CNN
F 2 "Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical" H 1700 3000 50  0001 C CNN
F 3 "~" H 1700 3000 50  0001 C CNN
	1    1700 3000
	1 0 0 -1
$EndComp
NoConn ~ 1500 2100
NoConn ~ 2000 2100
NoConn ~ 1500 2200
NoConn ~ 2000 2200
Wire Wire Line
	1500 2300 1050 2300
Text Label 1050 2300 0    45   ~ 0
GND
Wire Wire Line
	2000 2300 2450 2300
Text Label 2450 2300 0    45   ~ 0
GND
Wire Wire Line
	1500 2400 1050 2400
Text Label 1050 2400 0    45   ~ 0
+5V
NoConn ~ 2000 2400
Wire Wire Line
	1500 2500 1050 2500
Text Label 1050 2500 0    45   ~ 0
+5V
NoConn ~ 2000 2500
NoConn ~ 1500 2600
NoConn ~ 2000 2600
Wire Wire Line
	1500 2700 1050 2700
Text Label 1050 2700 0    45   ~ 0
+3V3
NoConn ~ 2000 2700
Wire Wire Line
	1500 2800 1050 2800
Text Label 1050 2800 0    45   ~ 0
+3V3
NoConn ~ 2000 2800
NoConn ~ 1500 2900
NoConn ~ 2000 2900
Wire Wire Line
	1500 3000 1050 3000
Text Label 1050 3000 0    45   ~ 0
+1V8
NoConn ~ 2000 3000
Wire Wire Line
	1500 3100 1050 3100
Text Label 1050 3100 0    45   ~ 0
+1V8
NoConn ~ 2000 3100
NoConn ~ 1500 3200
NoConn ~ 2000 3200
NoConn ~ 1500 3300
NoConn ~ 2000 3300
NoConn ~ 1500 3400
NoConn ~ 2000 3400
NoConn ~ 1500 3500
NoConn ~ 2000 3500
NoConn ~ 1500 3600
NoConn ~ 2000 3600
NoConn ~ 1500 3700
NoConn ~ 2000 3700
NoConn ~ 1500 3800
NoConn ~ 2000 3800
NoConn ~ 1500 3900
NoConn ~ 2000 3900
NoConn ~ 1500 4000
NoConn ~ 2000 4000
$Comp
L Connector_Generic:Conn_02x20_Odd_Even J15
U 1 1 D89C5157
P 4000 3000
F 0 "J15" H 4200 3150 50  0000 C CNN
F 1 "UNO Breakout Carrier" H 4350 2850 50  0000 C CNN
F 2 "Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical" H 4000 3000 50  0001 C CNN
F 3 "~" H 4000 3000 50  0001 C CNN
	1    4000 3000
	1 0 0 -1
$EndComp
NoConn ~ 3800 2100
NoConn ~ 4300 2100
NoConn ~ 3800 2200
NoConn ~ 4300 2200
NoConn ~ 3800 2300
NoConn ~ 4300 2300
NoConn ~ 3800 2400
NoConn ~ 4300 2400
NoConn ~ 3800 2500
NoConn ~ 4300 2500
NoConn ~ 3800 2600
NoConn ~ 4300 2600
NoConn ~ 3800 2700
NoConn ~ 4300 2700
NoConn ~ 3800 2800
NoConn ~ 4300 2800
NoConn ~ 3800 2900
NoConn ~ 4300 2900
NoConn ~ 3800 3000
NoConn ~ 4300 3000
NoConn ~ 3800 3100
NoConn ~ 4300 3100
Wire Wire Line
	3800 3200 3350 3200
Text Label 3350 3200 0    45   ~ 0
GND
NoConn ~ 4300 3200
NoConn ~ 3800 3300
NoConn ~ 4300 3300
NoConn ~ 3800 3400
NoConn ~ 4300 3400
NoConn ~ 3800 3500
Wire Wire Line
	4300 3500 4750 3500
Text Label 4750 3500 0    45   ~ 0
GND
NoConn ~ 3800 3600
Wire Wire Line
	4300 3600 4750 3600
Text Label 4750 3600 0    45   ~ 0
MI2S0_CLK
NoConn ~ 3800 3700
Wire Wire Line
	4300 3700 4750 3700
Text Label 4750 3700 0    45   ~ 0
MI2S0_WS
NoConn ~ 3800 3800
Wire Wire Line
	4300 3800 4750 3800
Text Label 4750 3800 0    45   ~ 0
MI2S0_DATA0
NoConn ~ 3800 3900
Wire Wire Line
	4300 3900 4750 3900
Text Label 4750 3900 0    45   ~ 0
MI2S0_DATA1
NoConn ~ 3800 4000
Wire Wire Line
	4300 4000 4750 4000
Text Label 4750 4000 0    45   ~ 0
GND
$Comp
L Connector_Generic:Conn_01x04 J_AMP_SIG
U 1 1 4CA7888A
P 6700 1650
F 0 "J_AMP_SIG" H 6900 1800 50  0000 C CNN
F 1 "XH2.54_VERTICAL_4" H 7050 1500 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical" H 6700 1650 50  0001 C CNN
F 3 "~" H 6700 1650 50  0001 C CNN
	1    6700 1650
	-1 0 0 1
$EndComp
Wire Wire Line
	6900 1750 7350 1750
Text Label 7350 1750 0    45   ~ 0
MI2S0_WS
Text Notes 5850 1765 0    40   ~ 0
1: MI2S0_WS
Wire Wire Line
	6900 1650 7350 1650
Text Label 7350 1650 0    45   ~ 0
MI2S0_CLK
Text Notes 5850 1665 0    40   ~ 0
2: MI2S0_CLK
Wire Wire Line
	6900 1550 7350 1550
Text Label 7350 1550 0    45   ~ 0
MI2S0_DATA1
Text Notes 5850 1565 0    40   ~ 0
3: MI2S0_DATA1
Wire Wire Line
	6900 1450 7350 1450
Text Label 7350 1450 0    45   ~ 0
AMP_GAIN
Text Notes 5850 1465 0    40   ~ 0
4: AMP_GAIN
$Comp
L Connector_Generic:Conn_01x03 J_AMP_PWR
U 1 1 AAF89768
P 6700 2850
F 0 "J_AMP_PWR" H 6900 3000 50  0000 C CNN
F 1 "XH2.54_VERTICAL_3" H 7050 2700 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical" H 6700 2850 50  0001 C CNN
F 3 "~" H 6700 2850 50  0001 C CNN
	1    6700 2850
	-1 0 0 1
$EndComp
Wire Wire Line
	6900 2950 7350 2950
Text Label 7350 2950 0    45   ~ 0
AMP_SD
Text Notes 5850 2965 0    40   ~ 0
1: AMP_SD
Wire Wire Line
	6900 2850 7350 2850
Text Label 7350 2850 0    45   ~ 0
GND
Text Notes 5850 2865 0    40   ~ 0
2: GND
Wire Wire Line
	6900 2750 7350 2750
Text Label 7350 2750 0    45   ~ 0
+5V
Text Notes 5850 2765 0    40   ~ 0
3: +5V
$Comp
L Connector_Generic:Conn_01x06 J_MIC
U 1 1 7E4EFF42
P 6700 4300
F 0 "J_MIC" H 6900 4450 50  0000 C CNN
F 1 "XH2.54_VERTICAL_6" H 7050 4150 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical" H 6700 4300 50  0001 C CNN
F 3 "~" H 6700 4300 50  0001 C CNN
	1    6700 4300
	-1 0 0 1
$EndComp
Wire Wire Line
	6900 4500 7350 4500
Text Label 7350 4500 0    45   ~ 0
GND
Text Notes 5850 4515 0    40   ~ 0
1: GND
Wire Wire Line
	6900 4400 7350 4400
Text Label 7350 4400 0    45   ~ 0
+1V8
Text Notes 5850 4415 0    40   ~ 0
2: +1V8
Wire Wire Line
	6900 4300 7350 4300
Text Label 7350 4300 0    45   ~ 0
MI2S0_DATA0
Text Notes 5850 4315 0    40   ~ 0
3: MI2S0_DATA0
Wire Wire Line
	6900 4200 7350 4200
Text Label 7350 4200 0    45   ~ 0
MI2S0_CLK
Text Notes 5850 4215 0    40   ~ 0
4: MI2S0_CLK
Wire Wire Line
	6900 4100 7350 4100
Text Label 7350 4100 0    45   ~ 0
MI2S0_WS
Text Notes 5850 4115 0    40   ~ 0
5: MI2S0_WS
Wire Wire Line
	6900 4000 7350 4000
Text Label 7350 4000 0    45   ~ 0
MIC_LR
Text Notes 5850 4015 0    40   ~ 0
6: MIC_LR
$Comp
L Device:R R_GAIN
U 1 1 12D3FE4D
P 9000 1700
F 0 "R_GAIN" H 9200 1850 50  0000 C CNN
F 1 "0R GAIN=GND" H 9350 1550 50  0000 C CNN
F 2 "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal" H 9000 1700 50  0001 C CNN
F 3 "~" H 9000 1700 50  0001 C CNN
	1    9000 1700
	0 -1 -1 0
$EndComp
Wire Wire Line
	8850 1700 8500 1700
Text Label 8500 1700 0    45   ~ 0
AMP_GAIN
Wire Wire Line
	9150 1700 9500 1700
Text Label 9500 1700 0    45   ~ 0
GND
$Comp
L Device:R R_SD
U 1 1 08868A24
P 9000 2500
F 0 "R_SD" H 9200 2650 50  0000 C CNN
F 1 "100k SD pull-up" H 9350 2350 50  0000 C CNN
F 2 "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal" H 9000 2500 50  0001 C CNN
F 3 "~" H 9000 2500 50  0001 C CNN
	1    9000 2500
	0 -1 -1 0
$EndComp
Wire Wire Line
	8850 2500 8500 2500
Text Label 8500 2500 0    45   ~ 0
AMP_SD
Wire Wire Line
	9150 2500 9500 2500
Text Label 9500 2500 0    45   ~ 0
+3V3
$Comp
L Device:R R_LR
U 1 1 823967F9
P 9000 4700
F 0 "R_LR" H 9200 4850 50  0000 C CNN
F 1 "0R MIC_LR=GND" H 9350 4550 50  0000 C CNN
F 2 "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal" H 9000 4700 50  0001 C CNN
F 3 "~" H 9000 4700 50  0001 C CNN
	1    9000 4700
	0 -1 -1 0
$EndComp
Wire Wire Line
	8850 4700 8500 4700
Text Label 8500 4700 0    45   ~ 0
MIC_LR
Wire Wire Line
	9150 4700 9500 4700
Text Label 9500 4700 0    45   ~ 0
GND
$Comp
L Connector_Generic:Conn_01x02 JP_MUTE
U 1 1 97F6F778
P 9000 3200
F 0 "JP_MUTE" H 9200 3350 50  0000 C CNN
F 1 "AMP SD MUTE (OPEN)" H 9350 3050 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" H 9000 3200 50  0001 C CNN
F 3 "~" H 9000 3200 50  0001 C CNN
	1    9000 3200
	-1 0 0 1
$EndComp
Wire Wire Line
	9200 3200 9500 3200
Text Label 9500 3200 0    45   ~ 0
AMP_SD
Wire Wire Line
	9200 3100 9500 3100
Text Label 9500 3100 0    45   ~ 0
GND
$Comp
L Device:C_Polarized C1
U 1 1 2A8D9D4F
P 8400 3900
F 0 "C1" H 8600 4050 50  0000 C CNN
F 1 "10u 10V" H 8750 3750 50  0000 C CNN
F 2 "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm" H 8400 3900 50  0001 C CNN
F 3 "~" H 8400 3900 50  0001 C CNN
	1    8400 3900
	1 0 0 -1
$EndComp
Wire Wire Line
	8400 3750 8400 3550
Text Label 8400 3550 0    45   ~ 0
+5V
Wire Wire Line
	8400 4050 8400 4250
Text Label 8400 4250 0    45   ~ 0
GND
$Comp
L Device:C C2
U 1 1 BF875E18
P 9300 3900
F 0 "C2" H 9500 4050 50  0000 C CNN
F 1 "100n" H 9650 3750 50  0000 C CNN
F 2 "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm" H 9300 3900 50  0001 C CNN
F 3 "~" H 9300 3900 50  0001 C CNN
	1    9300 3900
	1 0 0 -1
$EndComp
Wire Wire Line
	9300 3750 9300 3550
Text Label 9300 3550 0    45   ~ 0
+5V
Wire Wire Line
	9300 4050 9300 4250
Text Label 9300 4250 0    45   ~ 0
GND
$Comp
L Device:C C3
U 1 1 6E523890
P 10200 3900
F 0 "C3" H 10400 4050 50  0000 C CNN
F 1 "100n" H 10550 3750 50  0000 C CNN
F 2 "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm" H 10200 3900 50  0001 C CNN
F 3 "~" H 10200 3900 50  0001 C CNN
	1    10200 3900
	1 0 0 -1
$EndComp
Wire Wire Line
	10200 3750 10200 3550
Text Label 10200 3550 0    45   ~ 0
+1V8
Wire Wire Line
	10200 4050 10200 4250
Text Label 10200 4250 0    45   ~ 0
GND
Text Notes 8050 1250 0    60   ~ 12
Configuration and decoupling (THT)
Text Notes 8050 5200 0    50   ~ 10
JP_MUTE open: amplifier enabled by R_SD. Fit shunt: SD forced Low / mute.
Text Notes 700 5600 0    50   ~ 10
J14: 5/6=GND, 7/9=+5V, 13/15=+3V3, 19/21=+1V8
Text Notes 700 5850 0    50   ~ 10
J15: 23/30/40=GND, 32=CLK, 34=WS, 36=DATA0(mic), 38=DATA1(amp)
$EndSCHEMATC
