EESchema Schematic File Version 4
LIBS:power
LIBS:device
LIBS:Connector_Generic
EELAYER 29 0
EELAYER END
$Descr A4 11693 8268
Sheet 1 1
Title "IchiPing UNO Q Shield"
Date "2026-08-24"
Rev "A"
Comp "IchiPing UNO Q"
Comment1 "XH2.54 vertical pin order is top-view pin 1 to pin N"
$EndDescr
Text Notes 900 800 0    100  ~ 20
IchiPing UNO Q Shield
Text Notes 900 1050 0    60   ~ 12
A4/A5 are TFT GPIO; D20/D21 are the separate UNO Q I2C header pins.
$Comp
L Connector_Generic:Conn_01x02 J_WIN_A
U 1 1 4E01E08F
P 1700 1700
F 0 "J_WIN_A" H 1580 2050 50  0000 C CNN
F 1 "XH2.54_VERTICAL_2" H 1580 1350 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" H 1700 1700 50  0001 C CNN
F 3 "~" H 1700 1700 50  0001 C CNN
	1    1700 1700
	-1   0    0    1
$EndComp
Wire Wire Line
	1800 1650 2350 1650
Text Label 2000 1650 0    45   ~ 0
D3_WIN_A
Text Notes 800 1665 0    45   ~ 0
1: D3_WIN_A
Wire Wire Line
	1800 1750 2350 1750
Text Label 2000 1750 0    45   ~ 0
GND
Text Notes 800 1765 0    45   ~ 0
2: GND
$Comp
L Connector_Generic:Conn_01x02 J_WIN_B
U 1 1 FF86666D
P 4300 1700
F 0 "J_WIN_B" H 4180 2050 50  0000 C CNN
F 1 "XH2.54_VERTICAL_2" H 4180 1350 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" H 4300 1700 50  0001 C CNN
F 3 "~" H 4300 1700 50  0001 C CNN
	1    4300 1700
	-1   0    0    1
$EndComp
Wire Wire Line
	4400 1650 4950 1650
Text Label 4600 1650 0    45   ~ 0
D4_WIN_B
Text Notes 3400 1665 0    45   ~ 0
1: D4_WIN_B
Wire Wire Line
	4400 1750 4950 1750
Text Label 4600 1750 0    45   ~ 0
GND
Text Notes 3400 1765 0    45   ~ 0
2: GND
$Comp
L Connector_Generic:Conn_01x02 J_WIN_C
U 1 1 4CD11174
P 6900 1700
F 0 "J_WIN_C" H 6780 2050 50  0000 C CNN
F 1 "XH2.54_VERTICAL_2" H 6780 1350 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" H 6900 1700 50  0001 C CNN
F 3 "~" H 6900 1700 50  0001 C CNN
	1    6900 1700
	-1   0    0    1
$EndComp
Wire Wire Line
	7000 1650 7550 1650
Text Label 7200 1650 0    45   ~ 0
D5_WIN_C
Text Notes 6000 1665 0    45   ~ 0
1: D5_WIN_C
Wire Wire Line
	7000 1750 7550 1750
Text Label 7200 1750 0    45   ~ 0
GND
Text Notes 6000 1765 0    45   ~ 0
2: GND
$Comp
L Connector_Generic:Conn_01x02 J_DOOR_AB
U 1 1 C61368E4
P 1700 3400
F 0 "J_DOOR_AB" H 1580 3750 50  0000 C CNN
F 1 "XH2.54_VERTICAL_2" H 1580 3050 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" H 1700 3400 50  0001 C CNN
F 3 "~" H 1700 3400 50  0001 C CNN
	1    1700 3400
	-1   0    0    1
$EndComp
Wire Wire Line
	1800 3350 2350 3350
Text Label 2000 3350 0    45   ~ 0
D6_DOOR_AB
Text Notes 800 3365 0    45   ~ 0
1: D6_DOOR_AB
Wire Wire Line
	1800 3450 2350 3450
Text Label 2000 3450 0    45   ~ 0
GND
Text Notes 800 3465 0    45   ~ 0
2: GND
$Comp
L Connector_Generic:Conn_01x02 J_DOOR_BC
U 1 1 23226542
P 4300 3400
F 0 "J_DOOR_BC" H 4180 3750 50  0000 C CNN
F 1 "XH2.54_VERTICAL_2" H 4180 3050 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" H 4300 3400 50  0001 C CNN
F 3 "~" H 4300 3400 50  0001 C CNN
	1    4300 3400
	-1   0    0    1
$EndComp
Wire Wire Line
	4400 3350 4950 3350
Text Label 4600 3350 0    45   ~ 0
D7_DOOR_BC
Text Notes 3400 3365 0    45   ~ 0
1: D7_DOOR_BC
Wire Wire Line
	4400 3450 4950 3450
Text Label 4600 3450 0    45   ~ 0
GND
Text Notes 3400 3465 0    45   ~ 0
2: GND
$Comp
L Connector_Generic:Conn_01x02 J_EXEC
U 1 1 10F7DCF2
P 6900 3400
F 0 "J_EXEC" H 6780 3750 50  0000 C CNN
F 1 "XH2.54_VERTICAL_2" H 6780 3050 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" H 6900 3400 50  0001 C CNN
F 3 "~" H 6900 3400 50  0001 C CNN
	1    6900 3400
	-1   0    0    1
$EndComp
Wire Wire Line
	7000 3350 7550 3350
Text Label 7200 3350 0    45   ~ 0
D8_EXEC
Text Notes 6000 3365 0    45   ~ 0
1: D8_EXEC
Wire Wire Line
	7000 3450 7550 3450
Text Label 7200 3450 0    45   ~ 0
GND
Text Notes 6000 3465 0    45   ~ 0
2: GND
$Comp
L Connector_Generic:Conn_01x05 J_TFT_SIG
U 1 1 BFFE3A85
P 1700 5100
F 0 "J_TFT_SIG" H 1580 5450 50  0000 C CNN
F 1 "XH2.54_VERTICAL_5" H 1580 4750 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical" H 1700 5100 50  0001 C CNN
F 3 "~" H 1700 5100 50  0001 C CNN
	1    1700 5100
	-1   0    0    1
$EndComp
Wire Wire Line
	1800 4900 2350 4900
Text Label 2000 4900 0    45   ~ 0
D12_MISO
Text Notes 800 4915 0    45   ~ 0
1: D12_MISO
Wire Wire Line
	1800 5000 2350 5000
Text Label 2000 5000 0    45   ~ 0
A5_LED
Text Notes 800 5015 0    45   ~ 0
2: A5_LED
Wire Wire Line
	1800 5100 2350 5100
Text Label 2000 5100 0    45   ~ 0
D13_SCK
Text Notes 800 5115 0    45   ~ 0
3: D13_SCK
Wire Wire Line
	1800 5200 2350 5200
Text Label 2000 5200 0    45   ~ 0
D11_MOSI
Text Notes 800 5215 0    45   ~ 0
4: D11_MOSI
Wire Wire Line
	1800 5300 2350 5300
Text Label 2000 5300 0    45   ~ 0
A4_DC
Text Notes 800 5315 0    45   ~ 0
5: A4_DC
$Comp
L Connector_Generic:Conn_01x04 J_TFT_PWR
U 1 1 F6630EF8
P 4300 5100
F 0 "J_TFT_PWR" H 4180 5450 50  0000 C CNN
F 1 "XH2.54_VERTICAL_4" H 4180 4750 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical" H 4300 5100 50  0001 C CNN
F 3 "~" H 4300 5100 50  0001 C CNN
	1    4300 5100
	-1   0    0    1
$EndComp
Wire Wire Line
	4400 4950 4950 4950
Text Label 4600 4950 0    45   ~ 0
A3_RST
Text Notes 3400 4965 0    45   ~ 0
1: A3_RST
Wire Wire Line
	4400 5050 4950 5050
Text Label 4600 5050 0    45   ~ 0
A2_CS
Text Notes 3400 5065 0    45   ~ 0
2: A2_CS
Wire Wire Line
	4400 5150 4950 5150
Text Label 4600 5150 0    45   ~ 0
GND
Text Notes 3400 5165 0    45   ~ 0
3: GND
Wire Wire Line
	4400 5250 4950 5250
Text Label 4600 5250 0    45   ~ 0
+3V3
Text Notes 3400 5265 0    45   ~ 0
4: +3V3
$Comp
L Connector_Generic:Conn_01x03 J_RAIN
U 1 1 41254666
P 6900 5100
F 0 "J_RAIN" H 6780 5450 50  0000 C CNN
F 1 "XH2.54_VERTICAL_3" H 6780 4750 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical" H 6900 5100 50  0001 C CNN
F 3 "~" H 6900 5100 50  0001 C CNN
	1    6900 5100
	-1   0    0    1
$EndComp
Wire Wire Line
	7000 5000 7550 5000
Text Label 7200 5000 0    45   ~ 0
+3V3
Text Notes 6000 5015 0    45   ~ 0
1: +3V3
Wire Wire Line
	7000 5100 7550 5100
Text Label 7200 5100 0    45   ~ 0
GND
Text Notes 6000 5115 0    45   ~ 0
2: GND
Wire Wire Line
	7000 5200 7550 5200
Text Label 7200 5200 0    45   ~ 0
D9_RAIN
Text Notes 6000 5215 0    45   ~ 0
3: D9_RAIN
$Comp
L Connector_Generic:Conn_01x04 J_SERVO_CTRL
U 1 1 3394C7D4
P 1700 6800
F 0 "J_SERVO_CTRL" H 1580 7150 50  0000 C CNN
F 1 "XH2.54_VERTICAL_4" H 1580 6450 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical" H 1700 6800 50  0001 C CNN
F 3 "~" H 1700 6800 50  0001 C CNN
	1    1700 6800
	-1   0    0    1
$EndComp
Wire Wire Line
	1800 6650 2350 6650
Text Label 2000 6650 0    45   ~ 0
GND
Text Notes 800 6665 0    45   ~ 0
1: GND
Wire Wire Line
	1800 6750 2350 6750
Text Label 2000 6750 0    45   ~ 0
D21_SCL
Text Notes 800 6765 0    45   ~ 0
2: D21_SCL
Wire Wire Line
	1800 6850 2350 6850
Text Label 2000 6850 0    45   ~ 0
D20_SDA
Text Notes 800 6865 0    45   ~ 0
3: D20_SDA
Wire Wire Line
	1800 6950 2350 6950
Text Label 2000 6950 0    45   ~ 0
+3V3
Text Notes 800 6965 0    45   ~ 0
4: +3V3
$Comp
L Connector_Generic:Conn_01x02 J_PWR_IN
U 1 1 DD804698
P 4300 6800
F 0 "J_PWR_IN" H 4180 7150 50  0000 C CNN
F 1 "XH2.54_VERTICAL_2" H 4180 6450 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" H 4300 6800 50  0001 C CNN
F 3 "~" H 4300 6800 50  0001 C CNN
	1    4300 6800
	-1   0    0    1
$EndComp
Wire Wire Line
	4400 6750 4950 6750
Text Label 4600 6750 0    45   ~ 0
+5V
Text Notes 3400 6765 0    45   ~ 0
1: +5V
Wire Wire Line
	4400 6850 4950 6850
Text Label 4600 6850 0    45   ~ 0
GND
Text Notes 3400 6865 0    45   ~ 0
2: GND
$Comp
L Connector_Generic:Conn_01x02 J_SERVO_5V_OUT
U 1 1 3C4DB0A1
P 6900 6800
F 0 "J_SERVO_5V_OUT" H 6780 7150 50  0000 C CNN
F 1 "XH2.54_VERTICAL_2" H 6780 6450 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" H 6900 6800 50  0001 C CNN
F 3 "~" H 6900 6800 50  0001 C CNN
	1    6900 6800
	-1   0    0    1
$EndComp
Wire Wire Line
	7000 6750 7550 6750
Text Label 7200 6750 0    45   ~ 0
+5V
Text Notes 6000 6765 0    45   ~ 0
1: +5V
Wire Wire Line
	7000 6850 7550 6850
Text Label 7200 6850 0    45   ~ 0
GND
Text Notes 6000 6865 0    45   ~ 0
2: GND
$EndSCHEMATC
