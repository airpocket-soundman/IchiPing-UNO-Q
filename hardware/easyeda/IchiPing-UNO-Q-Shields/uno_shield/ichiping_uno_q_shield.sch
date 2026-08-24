EESchema Schematic File Version 4
LIBS:ichiping_uno_q_shield-cache
LIBS:power
LIBS:device
LIBS:Connector_Generic
EELAYER 29 0
EELAYER END
$Descr A4 11693 8268
Sheet 1 1
Title "IchiPing UNO Q Shield"
Date "2026-08-25"
Rev "B"
Comp "IchiPing UNO Q"
Comment1 "Complete circuit matching the routed PCB; XH2.54 vertical"
$EndDescr
Text Notes 600 500 0    100  ~ 20
IchiPing UNO Q Shield - complete circuit
Text Notes 600 750 0    55   ~ 11
External regulated 5 V feeds UNO +5V, never VIN. Servo 5 V is a direct protected-source branch.
$Comp
L Connector_Generic:Conn_01x08 J1
U 1 1 18863E7C
P 1450 1900
F 0 "J1" H 1300 2200 50  0000 C CNN
F 1 "UNO POWER" H 1350 1600 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinSocket_1x08_P2.54mm_Vertical" H 1450 1900 50  0001 C CNN
F 3 "~" H 1450 1900 50  0001 C CNN
	1    1450 1900
	-1 0 0 1
$EndComp
NoConn ~ 1650 2200
Text Notes 630 2215 0    38   ~ 0
1: NC
NoConn ~ 1650 2100
Text Notes 630 2115 0    38   ~ 0
2: NC
NoConn ~ 1650 2000
Text Notes 630 2015 0    38   ~ 0
3: NC
Wire Wire Line
	1650 1900 2100 1900
Text Label 2100 1900 0    45   ~ 0
+3V3
Text Notes 630 1915 0    38   ~ 0
4: +3V3
Wire Wire Line
	1650 1800 2100 1800
Text Label 2100 1800 0    45   ~ 0
+5V
Text Notes 630 1815 0    38   ~ 0
5: +5V
Wire Wire Line
	1650 1700 2100 1700
Text Label 2100 1700 0    45   ~ 0
GND
Text Notes 630 1715 0    38   ~ 0
6: GND
Wire Wire Line
	1650 1600 2100 1600
Text Label 2100 1600 0    45   ~ 0
GND
Text Notes 630 1615 0    38   ~ 0
7: GND
NoConn ~ 1650 1500
Text Notes 630 1515 0    38   ~ 0
8: NC
$Comp
L Connector_Generic:Conn_01x10 J2
U 1 1 8E03B9FA
P 3900 1900
F 0 "J2" H 3750 2200 50  0000 C CNN
F 1 "UNO DIGITAL 10" H 3800 1600 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinSocket_1x10_P2.54mm_Vertical" H 3900 1900 50  0001 C CNN
F 3 "~" H 3900 1900 50  0001 C CNN
	1    3900 1900
	-1 0 0 1
$EndComp
Wire Wire Line
	4100 2300 4550 2300
Text Label 4550 2300 0    45   ~ 0
D21_SCL
Text Notes 3080 2315 0    38   ~ 0
1: D21_SCL
Wire Wire Line
	4100 2200 4550 2200
Text Label 4550 2200 0    45   ~ 0
D20_SDA
Text Notes 3080 2215 0    38   ~ 0
2: D20_SDA
NoConn ~ 4100 2100
Text Notes 3080 2115 0    38   ~ 0
3: NC
Wire Wire Line
	4100 2000 4550 2000
Text Label 4550 2000 0    45   ~ 0
GND
Text Notes 3080 2015 0    38   ~ 0
4: GND
Wire Wire Line
	4100 1900 4550 1900
Text Label 4550 1900 0    45   ~ 0
D13_SCK
Text Notes 3080 1915 0    38   ~ 0
5: D13_SCK
Wire Wire Line
	4100 1800 4550 1800
Text Label 4550 1800 0    45   ~ 0
D12_MISO
Text Notes 3080 1815 0    38   ~ 0
6: D12_MISO
Wire Wire Line
	4100 1700 4550 1700
Text Label 4550 1700 0    45   ~ 0
D11_MOSI
Text Notes 3080 1715 0    38   ~ 0
7: D11_MOSI
NoConn ~ 4100 1600
Text Notes 3080 1615 0    38   ~ 0
8: NC
Wire Wire Line
	4100 1500 4550 1500
Text Label 4550 1500 0    45   ~ 0
D9_RAIN
Text Notes 3080 1515 0    38   ~ 0
9: D9_RAIN
Wire Wire Line
	4100 1400 4550 1400
Text Label 4550 1400 0    45   ~ 0
D8_EXEC
Text Notes 3080 1415 0    38   ~ 0
10: D8_EXEC
$Comp
L Connector_Generic:Conn_01x06 J3
U 1 1 181B5990
P 1450 3900
F 0 "J3" H 1300 4200 50  0000 C CNN
F 1 "UNO ANALOG" H 1350 3600 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinSocket_1x06_P2.54mm_Vertical" H 1450 3900 50  0001 C CNN
F 3 "~" H 1450 3900 50  0001 C CNN
	1    1450 3900
	-1 0 0 1
$EndComp
NoConn ~ 1650 4100
Text Notes 630 4115 0    38   ~ 0
1: NC
NoConn ~ 1650 4000
Text Notes 630 4015 0    38   ~ 0
2: NC
Wire Wire Line
	1650 3900 2100 3900
Text Label 2100 3900 0    45   ~ 0
A2
Text Notes 630 3915 0    38   ~ 0
3: A2
Wire Wire Line
	1650 3800 2100 3800
Text Label 2100 3800 0    45   ~ 0
A3
Text Notes 630 3815 0    38   ~ 0
4: A3
Wire Wire Line
	1650 3700 2100 3700
Text Label 2100 3700 0    45   ~ 0
A4
Text Notes 630 3715 0    38   ~ 0
5: A4
Wire Wire Line
	1650 3600 2100 3600
Text Label 2100 3600 0    45   ~ 0
A5
Text Notes 630 3615 0    38   ~ 0
6: A5
$Comp
L Connector_Generic:Conn_01x08 J4
U 1 1 7AFCC977
P 3900 3900
F 0 "J4" H 3750 4200 50  0000 C CNN
F 1 "UNO DIGITAL 8" H 3800 3600 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinSocket_1x08_P2.54mm_Vertical" H 3900 3900 50  0001 C CNN
F 3 "~" H 3900 3900 50  0001 C CNN
	1    3900 3900
	-1 0 0 1
$EndComp
Wire Wire Line
	4100 4200 4550 4200
Text Label 4550 4200 0    45   ~ 0
D7_DOOR_BC
Text Notes 3080 4215 0    38   ~ 0
1: D7_DOOR_BC
Wire Wire Line
	4100 4100 4550 4100
Text Label 4550 4100 0    45   ~ 0
D6_DOOR_AB
Text Notes 3080 4115 0    38   ~ 0
2: D6_DOOR_AB
Wire Wire Line
	4100 4000 4550 4000
Text Label 4550 4000 0    45   ~ 0
D5_WIN_C
Text Notes 3080 4015 0    38   ~ 0
3: D5_WIN_C
Wire Wire Line
	4100 3900 4550 3900
Text Label 4550 3900 0    45   ~ 0
D4_WIN_B
Text Notes 3080 3915 0    38   ~ 0
4: D4_WIN_B
Wire Wire Line
	4100 3800 4550 3800
Text Label 4550 3800 0    45   ~ 0
D3_WIN_A
Text Notes 3080 3815 0    38   ~ 0
5: D3_WIN_A
NoConn ~ 4100 3700
Text Notes 3080 3715 0    38   ~ 0
6: NC
NoConn ~ 4100 3600
Text Notes 3080 3615 0    38   ~ 0
7: NC
NoConn ~ 4100 3500
Text Notes 3080 3515 0    38   ~ 0
8: NC
$Comp
L Connector_Generic:Conn_01x02 J_EXEC
U 1 1 3F718A7B
P 6200 1250
F 0 "J_EXEC" H 6050 1550 50  0000 C CNN
F 1 "XH2.54_VERTICAL_2" H 6100 950 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" H 6200 1250 50  0001 C CNN
F 3 "~" H 6200 1250 50  0001 C CNN
	1    6200 1250
	-1 0 0 1
$EndComp
Wire Wire Line
	6400 1250 6850 1250
Text Label 6850 1250 0    45   ~ 0
D8_EXEC
Text Notes 5380 1265 0    38   ~ 0
1: D8_EXEC
Wire Wire Line
	6400 1150 6850 1150
Text Label 6850 1150 0    45   ~ 0
GND
Text Notes 5380 1165 0    38   ~ 0
2: GND
$Comp
L Connector_Generic:Conn_01x02 J_DOOR_BC
U 1 1 5BF5E028
P 7800 1250
F 0 "J_DOOR_BC" H 7650 1550 50  0000 C CNN
F 1 "XH2.54_VERTICAL_2" H 7700 950 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" H 7800 1250 50  0001 C CNN
F 3 "~" H 7800 1250 50  0001 C CNN
	1    7800 1250
	-1 0 0 1
$EndComp
Wire Wire Line
	8000 1250 8450 1250
Text Label 8450 1250 0    45   ~ 0
D7_DOOR_BC
Text Notes 6980 1265 0    38   ~ 0
1: D7_DOOR_BC
Wire Wire Line
	8000 1150 8450 1150
Text Label 8450 1150 0    45   ~ 0
GND
Text Notes 6980 1165 0    38   ~ 0
2: GND
$Comp
L Connector_Generic:Conn_01x02 J_DOOR_AB
U 1 1 1EAC34A1
P 9400 1250
F 0 "J_DOOR_AB" H 9250 1550 50  0000 C CNN
F 1 "XH2.54_VERTICAL_2" H 9300 950 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" H 9400 1250 50  0001 C CNN
F 3 "~" H 9400 1250 50  0001 C CNN
	1    9400 1250
	-1 0 0 1
$EndComp
Wire Wire Line
	9600 1250 10050 1250
Text Label 10050 1250 0    45   ~ 0
D6_DOOR_AB
Text Notes 8580 1265 0    38   ~ 0
1: D6_DOOR_AB
Wire Wire Line
	9600 1150 10050 1150
Text Label 10050 1150 0    45   ~ 0
GND
Text Notes 8580 1165 0    38   ~ 0
2: GND
$Comp
L Connector_Generic:Conn_01x02 J_WIN_C
U 1 1 E6BBC4EE
P 6200 2250
F 0 "J_WIN_C" H 6050 2550 50  0000 C CNN
F 1 "XH2.54_VERTICAL_2" H 6100 1950 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" H 6200 2250 50  0001 C CNN
F 3 "~" H 6200 2250 50  0001 C CNN
	1    6200 2250
	-1 0 0 1
$EndComp
Wire Wire Line
	6400 2250 6850 2250
Text Label 6850 2250 0    45   ~ 0
D5_WIN_C
Text Notes 5380 2265 0    38   ~ 0
1: D5_WIN_C
Wire Wire Line
	6400 2150 6850 2150
Text Label 6850 2150 0    45   ~ 0
GND
Text Notes 5380 2165 0    38   ~ 0
2: GND
$Comp
L Connector_Generic:Conn_01x02 J_WIN_B
U 1 1 283B512B
P 7800 2250
F 0 "J_WIN_B" H 7650 2550 50  0000 C CNN
F 1 "XH2.54_VERTICAL_2" H 7700 1950 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" H 7800 2250 50  0001 C CNN
F 3 "~" H 7800 2250 50  0001 C CNN
	1    7800 2250
	-1 0 0 1
$EndComp
Wire Wire Line
	8000 2250 8450 2250
Text Label 8450 2250 0    45   ~ 0
D4_WIN_B
Text Notes 6980 2265 0    38   ~ 0
1: D4_WIN_B
Wire Wire Line
	8000 2150 8450 2150
Text Label 8450 2150 0    45   ~ 0
GND
Text Notes 6980 2165 0    38   ~ 0
2: GND
$Comp
L Connector_Generic:Conn_01x02 J_WIN_A
U 1 1 AFA59F50
P 9400 2250
F 0 "J_WIN_A" H 9250 2550 50  0000 C CNN
F 1 "XH2.54_VERTICAL_2" H 9300 1950 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" H 9400 2250 50  0001 C CNN
F 3 "~" H 9400 2250 50  0001 C CNN
	1    9400 2250
	-1 0 0 1
$EndComp
Wire Wire Line
	9600 2250 10050 2250
Text Label 10050 2250 0    45   ~ 0
D3_WIN_A
Text Notes 8580 2265 0    38   ~ 0
1: D3_WIN_A
Wire Wire Line
	9600 2150 10050 2150
Text Label 10050 2150 0    45   ~ 0
GND
Text Notes 8580 2165 0    38   ~ 0
2: GND
$Comp
L Connector_Generic:Conn_01x03 J_RAIN
U 1 1 4D1D0DB7
P 6200 3450
F 0 "J_RAIN" H 6050 3750 50  0000 C CNN
F 1 "XH2.54_VERTICAL_3" H 6100 3150 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical" H 6200 3450 50  0001 C CNN
F 3 "~" H 6200 3450 50  0001 C CNN
	1    6200 3450
	-1 0 0 1
$EndComp
Wire Wire Line
	6400 3550 6850 3550
Text Label 6850 3550 0    45   ~ 0
+3V3
Text Notes 5380 3565 0    38   ~ 0
1: +3V3
Wire Wire Line
	6400 3450 6850 3450
Text Label 6850 3450 0    45   ~ 0
GND
Text Notes 5380 3465 0    38   ~ 0
2: GND
Wire Wire Line
	6400 3350 6850 3350
Text Label 6850 3350 0    45   ~ 0
D9_RAIN
Text Notes 5380 3365 0    38   ~ 0
3: D9_RAIN
$Comp
L Connector_Generic:Conn_01x04 J_SERVO_CTRL
U 1 1 975DF9A0
P 7800 3450
F 0 "J_SERVO_CTRL" H 7650 3750 50  0000 C CNN
F 1 "XH2.54_VERTICAL_4" H 7700 3150 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical" H 7800 3450 50  0001 C CNN
F 3 "~" H 7800 3450 50  0001 C CNN
	1    7800 3450
	-1 0 0 1
$EndComp
Wire Wire Line
	8000 3550 8450 3550
Text Label 8450 3550 0    45   ~ 0
GND
Text Notes 6980 3565 0    38   ~ 0
1: GND
Wire Wire Line
	8000 3450 8450 3450
Text Label 8450 3450 0    45   ~ 0
D21_SCL
Text Notes 6980 3465 0    38   ~ 0
2: D21_SCL
Wire Wire Line
	8000 3350 8450 3350
Text Label 8450 3350 0    45   ~ 0
D20_SDA
Text Notes 6980 3365 0    38   ~ 0
3: D20_SDA
Wire Wire Line
	8000 3250 8450 3250
Text Label 8450 3250 0    45   ~ 0
+3V3
Text Notes 6980 3265 0    38   ~ 0
4: +3V3
$Comp
L Connector_Generic:Conn_01x05 J_TFT_SIG
U 1 1 F3DF07A5
P 9400 3450
F 0 "J_TFT_SIG" H 9250 3750 50  0000 C CNN
F 1 "XH2.54_VERTICAL_5" H 9300 3150 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical" H 9400 3450 50  0001 C CNN
F 3 "~" H 9400 3450 50  0001 C CNN
	1    9400 3450
	-1 0 0 1
$EndComp
Wire Wire Line
	9600 3650 10050 3650
Text Label 10050 3650 0    45   ~ 0
D12_MISO
Text Notes 8580 3665 0    38   ~ 0
1: D12_MISO
Wire Wire Line
	9600 3550 10050 3550
Text Label 10050 3550 0    45   ~ 0
A5
Text Notes 8580 3565 0    38   ~ 0
2: A5
Wire Wire Line
	9600 3450 10050 3450
Text Label 10050 3450 0    45   ~ 0
D13_SCK
Text Notes 8580 3465 0    38   ~ 0
3: D13_SCK
Wire Wire Line
	9600 3350 10050 3350
Text Label 10050 3350 0    45   ~ 0
D11_MOSI
Text Notes 8580 3365 0    38   ~ 0
4: D11_MOSI
Wire Wire Line
	9600 3250 10050 3250
Text Label 10050 3250 0    45   ~ 0
A4
Text Notes 8580 3265 0    38   ~ 0
5: A4
$Comp
L Connector_Generic:Conn_01x04 J_TFT_PWR
U 1 1 7B1ACE50
P 6200 4750
F 0 "J_TFT_PWR" H 6050 5050 50  0000 C CNN
F 1 "XH2.54_VERTICAL_4" H 6100 4450 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical" H 6200 4750 50  0001 C CNN
F 3 "~" H 6200 4750 50  0001 C CNN
	1    6200 4750
	-1 0 0 1
$EndComp
Wire Wire Line
	6400 4850 6850 4850
Text Label 6850 4850 0    45   ~ 0
A3
Text Notes 5380 4865 0    38   ~ 0
1: A3
Wire Wire Line
	6400 4750 6850 4750
Text Label 6850 4750 0    45   ~ 0
A2
Text Notes 5380 4765 0    38   ~ 0
2: A2
Wire Wire Line
	6400 4650 6850 4650
Text Label 6850 4650 0    45   ~ 0
GND
Text Notes 5380 4665 0    38   ~ 0
3: GND
Wire Wire Line
	6400 4550 6850 4550
Text Label 6850 4550 0    45   ~ 0
+3V3
Text Notes 5380 4565 0    38   ~ 0
4: +3V3
$Comp
L Connector_Generic:Conn_01x02 J_PWR_IN
U 1 1 D5159CAC
P 7800 4750
F 0 "J_PWR_IN" H 7650 5050 50  0000 C CNN
F 1 "XH2.54_VERTICAL_2" H 7700 4450 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" H 7800 4750 50  0001 C CNN
F 3 "~" H 7800 4750 50  0001 C CNN
	1    7800 4750
	-1 0 0 1
$EndComp
Wire Wire Line
	8000 4750 8450 4750
Text Label 8450 4750 0    45   ~ 0
+5V
Text Notes 6980 4765 0    38   ~ 0
1: +5V
Wire Wire Line
	8000 4650 8450 4650
Text Label 8450 4650 0    45   ~ 0
GND
Text Notes 6980 4665 0    38   ~ 0
2: GND
$Comp
L Connector_Generic:Conn_01x02 J_SERVO_5V_OUT
U 1 1 290FE9C6
P 9400 4750
F 0 "J_SERVO_5V_OUT" H 9250 5050 50  0000 C CNN
F 1 "XH2.54_VERTICAL_2" H 9300 4450 50  0000 C CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" H 9400 4750 50  0001 C CNN
F 3 "~" H 9400 4750 50  0001 C CNN
	1    9400 4750
	-1 0 0 1
$EndComp
Wire Wire Line
	9600 4750 10050 4750
Text Label 10050 4750 0    45   ~ 0
+5V
Text Notes 8580 4765 0    38   ~ 0
1: +5V
Wire Wire Line
	9600 4650 10050 4650
Text Label 10050 4650 0    45   ~ 0
GND
Text Notes 8580 4665 0    38   ~ 0
2: GND
$Comp
L Device:C_Polarized C_PWR_BULK
U 1 1 8A185EDF
P 6500 6200
F 0 "C_PWR_BULK" H 6350 6500 50  0000 C CNN
F 1 "470u 10V LOW ESR" H 6400 5900 50  0000 C CNN
F 2 "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm" H 6500 6200 50  0001 C CNN
F 3 "~" H 6500 6200 50  0001 C CNN
	1    6500 6200
	1 0 0 -1
$EndComp
Wire Wire Line
	6500 6050 6500 5850
Text Label 6500 5850 0    45   ~ 0
+5V
Wire Wire Line
	6500 6350 6500 6550
Text Label 6500 6550 0    45   ~ 0
GND
$Comp
L Device:C C_PWR_HF
U 1 1 A82D120F
P 8000 6200
F 0 "C_PWR_HF" H 7850 6500 50  0000 C CNN
F 1 "100n" H 7900 5900 50  0000 C CNN
F 2 "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm" H 8000 6200 50  0001 C CNN
F 3 "~" H 8000 6200 50  0001 C CNN
	1    8000 6200
	1 0 0 -1
$EndComp
Wire Wire Line
	8000 6050 8000 5850
Text Label 8000 5850 0    45   ~ 0
+5V
Wire Wire Line
	8000 6350 8000 6550
Text Label 8000 6550 0    45   ~ 0
GND
$Comp
L Device:C_Polarized C_SERVO_BULK
U 1 1 70CD1808
P 9500 6200
F 0 "C_SERVO_BULK" H 9350 6500 50  0000 C CNN
F 1 "1000u LOW ESR" H 9400 5900 50  0000 C CNN
F 2 "Capacitor_THT:CP_Radial_D10.0mm_P5.00mm" H 9500 6200 50  0001 C CNN
F 3 "~" H 9500 6200 50  0001 C CNN
	1    9500 6200
	1 0 0 -1
$EndComp
Wire Wire Line
	9500 6050 9500 5850
Text Label 9500 5850 0    45   ~ 0
+5V
Wire Wire Line
	9500 6350 9500 6550
Text Label 9500 6550 0    45   ~ 0
GND
Text Notes 600 5450 0    50   ~ 10
TFT: J_TFT_SIG 1=MISO(unused by write-only display), 2=LED/A5, 3=SCK/D13, 4=MOSI/D11, 5=DC/A4
Text Notes 600 5700 0    50   ~ 10
TFT: J_TFT_PWR 1=RST/A3, 2=CS/A2, 3=GND, 4=3V3
Text Notes 600 5950 0    50   ~ 10
All GPIO and I2C logic is 3.3 V. J_SERVO_5V_OUT is servo power only; grounds are common.
$EndSCHEMATC
