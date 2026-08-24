# IchiPing UNO Q shield design

The binding design input is [SPECIFICATION.md](SPECIFICATION.md). This file
records implementation notes for the generated KiCad/EasyEDA board data.

Both `*_easyeda_import.zip` archives contain the routed PCB and a KiCad 8
`.kicad_sch` complete circuit. The legacy `.sch` files and `-cache.lib` files
are retained as reproducible conversion sources. The UNO circuit includes all
four shield headers, all 12 XH connectors, and the three power capacitors. The
audio circuit includes the J14/J15 physical pin numbers, all three XH
connectors, configuration resistors, mute jumper, and decoupling capacitors.
The repository's `board/Ichiping uno q.eprj2` project contains both routed
boards and both circuit drawings.

## Assembly variants

`variants/` contains three routed, schematic-matched versions of **each**
board. Connector references, pin numbers, nets, board outlines, and placement
origins are identical across the variants.

| Directory | Connectors | Resistors/capacitors | Intended use |
|---|---|---|---|
| `variants/tht/` | THT | THT | Hand assembly and repair |
| `variants/smd/` | SMD | SMD | Reflow assembly / geometry comparison |
| `variants/hybrid/` | THT | SMD | XH harness strength with automated passive placement |

Each board directory includes `.kicad_sch`, `.kicad_pcb`, project, ERC report,
and DRC report files. The adjacent `*_easyeda_import.zip` contains the matching
schematic and PCB for EasyEDA Pro import. Regenerate them with
`scripts/generate_variants.py` and audit technology, 2.54 mm pitch, connector
pin order, and power nets with `scripts/audit_variants.py`.

Important mechanical limitation: the XH/XH2.54 family has no standard
top-entry surface-mount header equivalent. The `smd` variant therefore uses a
project-local 2.54 mm vertical SMD pin landing pattern for an XH-harness mating
interface. It does **not** provide the shroud, key, or latch of the vertical THT
XH-compatible connector. Use `hybrid` when the specified vertical polarized
XH housing and cable retention are mandatory; do not release the `smd` variant
for production until an exact supplier part and its drawing are approved.

## Design assumptions

- In the binding THT and hybrid builds, all external harness connectors are vertical, through-hole, 2.54 mm pitch
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

- The board outline, four mounting holes, and the four shield headers are
  inherited unchanged from KiCad 8's official `Arduino_Uno` board template.
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
beside `J_PWR_IN`; `C_PWR_HF` (100 nF) remains in parallel. The separate
`C_SERVO_BULK` 1000 uF capacitor remains beside the servo-power branch.

The complete circuit is in
`uno_shield/ichiping_uno_q_shield.kicad_sch`. Unused UNO header pins are
explicitly marked no-connect so KiCad ERC can distinguish deliberate unused
pins from wiring omissions.

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

In the binding THT build, `GAIN` and `L/R` default to GND through removable 0-ohm axial DIN0207
resistors. `SD` has a 100 kOhm DIN0207 pull-up to 3.3 V and a normally open
2.54 mm `JP_MUTE` header to GND. C1 is a radial 10 uF / 10 V electrolytic;
C2/C3 are 100 nF through-hole disc capacitors. No SMD part is used on Board B.

The complete circuit is in
`audio_shield/ichiping_uno_q_audio_shield.kicad_sch`; the legacy `.sch` and its
`-cache.lib` are retained as reproducible conversion sources. The complete
circuit is no longer only a connector map.

## Manufacturing defaults

- 2-layer FR-4, 1.6 mm, 1 oz copper.
- Signal tracks 0.25 mm; power tracks 0.50 mm; +5 V tracks 1.00 mm.
- Track clearance is 0.25 mm and copper-pour clearance is 0.30 mm. Standard
  vias are 0.90/0.50 mm (diameter/drill); the pour and drill sizes leave
  margin above EasyEDA Pro's defaults after import rounding.
- GND copper pours on both layers with stitching vias.
- JST XH pin 1 is marked on both copper footprint and silkscreen.
- Run ERC/DRC again after EasyEDA Pro import because library conversion can
  alter courtyard and solder-mask rules.
- EasyEDA Pro converts KiCad's footprint metadata into `Origin Footprint`, so
  its native symbol-footprint and schematic-netlist identity checks cannot be
  used for imported symbols. In `board/Ichiping uno q.eprj2`, those two
  schematic checks are set to Note and PCB custom DRC rule 124 (`Schematic
  Netlist`) is unchecked. All electrical wiring checks and all 123 physical PCB
  checks remain enabled. Use `Design > Check DRC(Custom)... > Check Now` for
  the imported PCB; the saved result is `All (0)`. The UNO KiCad checks remain
  the independent binding cross-check: ERC 0 errors/0 warnings and PCB DRC 0
  violations/0 unrouted items.
