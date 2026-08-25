# IchiPing UNO Q shield design

The binding electrical and mechanical requirements are in
[SPECIFICATION.md](SPECIFICATION.md). The sole editable EDA source is the
EasyEDA project `board/Ichiping uno q.eprj2`.

The project contains two EasyEDA-native schematic/PCB boards:
`ichiping_uno_q_shield` and `ichiping_uno_q_audio_shield`. Each Board owns one
schematic and its routed PCB. Component references, unique IDs, pin/pad
numbers, nets, footprints, copper, board outlines, and silkscreen are
maintained directly in EasyEDA. The schematics were rebuilt in EasyEDA; there
is no external EDA conversion or synchronization step.

## Assembly technology

The repository contains one binding production design for each board. All
connectors and polarized electrolytic capacitors are through-hole; fixed
resistors and non-polarized capacitors use SMD pads at the reviewed routing
centers. This keeps
mechanically loaded cable interfaces and large polarized parts serviceable
while allowing automated placement of the remaining components.

The `uno_shield/bom.csv` and `audio_shield/bom.csv` files are the board-specific
parts lists. `scripts/prune_easyeda_project.py` keeps the current EasyEDA
project tree limited to the two canonical schematic/PCB Boards while retaining
the project database's historical snapshots.

## Schematic/PCB association

| Board | Schematic | PCB |
|---|---|---|
| `ichiping_uno_q_shield` | `ichiping_uno_q_shield_schematic` / `Main` | `ichiping_uno_q_shield` |
| `ichiping_uno_q_audio_shield` | `ichiping_uno_q_audio_shield_schematic` / `Main` | `ichiping_uno_q_audio_shield` |

Every electrical PCB component is represented in its schematic with the same
reference, unique ID, pin/pad number, and net name. The four UNO mounting holes
are standalone 3.2 mm non-plated through holes, not electrical components, and
are therefore outside the electrical component audit.

The rebuilt schematics reference the same project-local Device and Footprint
records as their routed PCBs. EasyEDA `Import Changes` therefore reports no
component differences. The pin-level audit also reports zero differences for
19 components / 70 pins on the UNO shield and 12 components / 107 pins on the
audio shield. Keep rule 124 (`Schematic Netlist`) enabled together with all
other PCB checks.

## Design assumptions

- All external harness connectors are vertical, through-hole, 2.54 mm pitch
  XH-compatible parts. They use custom `XH2.54_Vertical_1xNN` footprints;
  genuine JST XH `B?B-XH-A` parts are 2.50 mm and must not be substituted.
- Connector pin numbers below are viewed from the PCB top. Pin 1 has a square
  pad and a silkscreen triangle.
- The requested `WIN` label on the MAX98357A power connector is interpreted as
  `VIN`.
- Toggle and EXEC connectors use pin 1 = signal and pin 2 = GND.
- The PCA9685 connector `VIN` is the 3.3 V logic supply. Servo V+ remains an
  external 5 V supply at the PCA9685 board and is never supplied by the UNO Q.
- MI2S0 signals are QRB2210 1.8 V logic. The microphone VCC is therefore 1.8 V.
- MAX98357A VIN is 5 V. Its I2S inputs are driven by the 1.8 V MI2S0 signals.
- Audio DATA0 is microphone input and DATA1 is amplifier output, matching the
  UNO Q porting plan. This must still be confirmed in Device Tree and ALSA
  before connecting the audio modules.

## Board A: IchiPing UNO Q Shield

The board uses the traditional UNO headers but keeps A4/A5 separate from the
dedicated top-header I2C pins D20/D21, as required by the UNO Q.

### Mechanical outline

- The board outline, four mounting holes, and the four shield headers retain
  the reviewed Arduino UNO shield geometry in EasyEDA.
- Edge bounding box: 68.73 x 53.49 mm (nominal Arduino UNO outline is commonly
  specified as 68.6 x 53.4 mm; the small difference includes plotted edge-line
  width and the shaped USB/DC-jack end of the template).
- Mounting-hole drill diameter: 3.2 mm.
- The non-rectangular UNO end profile and header offset are retained; do not
  replace the outline with a simple 68.6 x 53.4 mm rectangle.
- All added JST XH connectors and silkscreen are kept inside this outline.

| Reference | Connector | Pin order | UNO Q nets |
|---|---|---|---|
| J_WIN_A | XH-2 | WIN_A, GND | D3, GND |
| J_WIN_B | XH-2 | WIN_B, GND | D4, GND |
| J_WIN_C | XH-2 | WIN_C, GND | D5, GND |
| J_DOOR_AB | XH-2 | DOOR_AB, GND | D6, GND |
| J_DOOR_BC | XH-2 | DOOR_BC, GND | D7, GND |
| J_EXEC | XH-2 | EXEC, GND | D8, GND |
| J_TFT_SIG | XH-5 | MISO, LED, SCK, MOSI, DC | D12, A5, D13, D11, A4 |
| J_TFT_PWR | XH-4 | RST, CS, GND, VCC | A3, A2, GND, 3V3 |
| J_RAIN | XH-3 | VCC, GND, D0 | 3V3, GND, D9 |
| J_SERVO_CTRL | XH-4 | GND, SCL, SDA, VIN | GND, D21, D20, 3V3 |
| J_PWR_IN | XH-2 | +5V, GND | UNO Q +5V pin, GND (never VIN) |
| J_SERVO_5V_OUT | XH-2 | +5V, GND | Direct branch from J_PWR_IN for PCA9685 V+ |

`C_PWR_BULK` is a polarized 470 uF / 10 V low-ESR input capacitor in an
8.0 mm radial footprint with 3.50 mm lead spacing. It sits on the 5 V rail
beside `J_PWR_IN`; `C_PWR_HF` is a 100 nF radial through-hole ceramic
capacitor with 5.00 mm lead spacing and remains in parallel. The separate
`C_SERVO_BULK` 1000 uF capacitor remains beside the servo-power branch.

The PCB nets and connector table above define the electrical connections.
Unused UNO header pads are intentionally left without a net.

## Board B: IchiPing UNO Q Audio Shield

This board plugs into the UNO Breakout Carrier J14 and J15 2x20, 2.54 mm male
headers using bottom-side female sockets. The J14/J15 coordinates and official
15.24 mm spacing are unchanged. The outline is 79 x 53.34 mm: it extends 33 mm
to the right of the previous outline, and all three XH connectors are placed
to the right of J15.

| Reference | Connector | Pin order | Breakout Carrier nets |
|---|---|---|---|
| J_AMP_SIG | XH-4 | LRC, BCLK, DIN, GAIN | J15-34, J15-32, J15-38, gain selector |
| J_AMP_PWR | XH-3 | SD, GND, VIN | SD selector, GND, J14-7 (+5V) |
| J_MIC | XH-6 | GND, VCC, SD, SCK, WS, L/R | GND, J14-19 (+1V8), J15-36, J15-32, J15-34, channel selector |

`GAIN` and `L/R` default to GND through 0-ohm SMD resistors. `SD` has a
100 kOhm SMD pull-up to 3.3 V and a normally open through-hole 2.54 mm
`JP_MUTE` header to GND. C1 is a radial through-hole 10 uF / 10 V
electrolytic; C2/C3 are 100 nF SMD ceramic capacitors.

The PCB nets, connector table, configuration components, and board-specific BOM
define the complete electrical implementation.

## Manufacturing defaults

- 2-layer FR-4, 1.6 mm, 1 oz copper.
- Signal tracks 0.25 mm; power tracks 0.50 mm; +5 V tracks 1.00 mm.
- Track clearance is 0.25 mm and copper-pour clearance is 0.30 mm. Standard
  vias are 0.90/0.50 mm (diameter/drill); the pour and drill sizes leave
  margin above EasyEDA's defaults after import rounding.
- GND copper pours on both layers with stitching vias.
- JST XH pin 1 is marked on both copper footprint and silkscreen.
- Before manufacturing, run the saved EasyEDA custom PCB DRC on both Boards and
  require `All (0)`, including rule 124 (`Schematic Netlist`).
- Verify the schematic-to-PCB reference, unique-ID, pin/pad, and net mapping,
  then review connector pin order and supply rails against
  [SPECIFICATION.md](SPECIFICATION.md), `docs/uno_q_port.html`, and the
  board-specific BOMs.
