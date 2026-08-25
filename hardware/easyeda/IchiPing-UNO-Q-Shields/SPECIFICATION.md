# IchiPing UNO Q シールド基板仕様書

版: Rev A 設計入力 / 2026-08-24

本書は、EasyEDAネイティブ回路図・PCBの設計入力とレビュー基準の正本とする。GPIOの正本
`docs/uno_q_port.html`、元IchiPingの`docs/pins.xlsx`、UNO QおよびUNO
Breakout Carrierの公式資料を突き合わせた結果を記載する。

## 1. 共通コネクタ仕様

- センサ、スイッチ、表示器、音響モジュール、外部電源に接続するコネクタは
  すべてXH形状、2.54 mmピッチ、基板上面から挿抜する垂直型とする。
- フットプリント名は`XH2.54_Vertical_1xNN`とし、1番ピンを角ランド、
  シルク三角、信号名で識別する。
- 純正JST XHの公称ピッチは2.50 mmであり、本仕様の2.54 mmとは異なる。
  BOMには`XH2.54互換`と明記し、純正`B?B-XH-A`を指定しない。
- ピン順は基板上面から見て、シルクの1番ピン側から数える。
- UNO QおよびUNO Breakout Carrierへ直接嵌合するArduinoヘッダ／2x20ソケットは
  基板間接続なので、外部ハーネス用XH統一の対象外とする。

## 2. Board A: UNOレイアウト・シールド

### 2.1 機械仕様

- Arduino UNO外形、4取付穴、4列のArduinoシールドヘッダ位置を使用する。
- EasyEDA上で確定したArduino UNO互換の非矩形外形を維持する。
- 外形バウンディングボックスは約68.73 x 53.49 mm、取付穴は3.2 mm。
- XHはすべてトップエントリー垂直型とし、USB-C、ボタン、既存部品との高さ干渉を
  3D表示で確認する。

### 2.2 5 V電源

| Ref | 極数 | Pin 1 | Pin 2 | 接続 |
|---|---:|---|---|---|
| J_PWR_IN | 2 | +5V_IN | GND | 外部の安定化5 V電源入力 |
| J_SERVO_5V_OUT | 2 | +5V_SERVO | GND | PCA9685サーボ電源V+へ出力 |

- UNO Qの`VIN`は7-24 V入力である。5 Vを`VIN`へ接続してはならない。
- `J_PWR_IN`の+5 VはUNO Q JANALOGヘッダの`+5V`端子へ接続する。Arduino公式資料は
  安定化5 Vをこの端子へ入力してUNO Qを給電できるとしている。
- `+5V_SERVO`は`+5V_IN`から直接分岐し、UNO Qの3.3 Vレールを通さない。
- UNO Q、シールド、PCA9685、外部5 V電源のGNDを共通化する。
- 入力は5.0 V安定化電源とし、通常範囲を4.75-5.25 Vとする。極性逆接は禁止。
- XH2.54互換コネクタ、端子、ハーネスの定格を含め、入力からサーボ出力までの
  連続電流上限を3 Aとする。5個のSG90を同時にストールさせない。
- 5 V入力コネクタ直近に470 uF / 10 V以上の低ESR電解コンデンサと100 nFを配置する。
  電解コンデンサはPin 1が+5 V、Pin 2がGNDで、シルクの極性表示を確認して実装する。
- サーボ出力直近には1000 uF以上の低ESR電解コンデンサを追加配置する。
- `+5V_SERVO`をPCA9685のロジック`VCC`へ接続しない。V+専用とする。

### 2.3 GPIO・表示・サーボ制御

トグルおよびEXECは内部プルアップを使うアクティブLow入力で、Pin 1が信号、
Pin 2がGNDである。

| Ref | 極数 | XH2.54のピン順 | UNO Q接続 |
|---|---:|---|---|
| J_WIN_A | 2 | WIN_A, GND | D3, GND |
| J_WIN_B | 2 | WIN_B, GND | D4, GND |
| J_WIN_C | 2 | WIN_C, GND | D5, GND |
| J_DOOR_AB | 2 | DOOR_AB, GND | D6, GND |
| J_DOOR_BC | 2 | DOOR_BC, GND | D7, GND |
| J_EXEC | 2 | EXEC, GND | D8, GND |
| J_RAIN | 3 | VCC, GND, D0 | 3V3, GND, D9 |
| J_SERVO_CTRL | 4 | GND, SCL, SDA, VIN | GND, D21, D20, 3V3 |
| J_TFT_SIG | 5 | MISO, LED, SCK, MOSI, DC | D12, A5, D13, D11, A4 |
| J_TFT_PWR | 4 | RST, CS, GND, VCC | A3, A2, GND, 3V3 |

`J_SERVO_CTRL`の`VIN`表記はPCA9685モジュールのロジック電源入力を意味し、3.3 Vで
ある。サーボ電源V+は`J_SERVO_5V_OUT`から別配線する。雨センサD0は必ず3.3 V以下に
なる3.3 V動作モジュールを用いる。TFT MISOはコネクタへ出すが、現行ドライバは
書込み専用なので未使用でもよい。

### 2.4 ソフトウェアとの一致

- 状態bit 0..4 = D3..D7 = 窓a、窓b、窓c、扉AB、扉BC。
- EXEC = D8、雨入力 = D9。
- PCA9685 = `Wire`、SDA=D20、SCL=D21、アドレス0x40。
- TFT = D11 MOSI、D12 MISO、D13 SCK、A2 CS、A3 RST、A4 DC、A5 BL。
- A4/A5はTFT GPIOであり、UNO Qの専用I2C D20/D21とは別ピンである。

## 3. Board B: UNO Breakout Carrier音響シールド

### 3.1 機械・基板間接続

- UNO Breakout CarrierのJ14/J15へ、2x20、2.54 mmピッチのボトム側メスソケットで
  直接嵌合する。この2個だけはXHではない。
- Carrier公式外形107.6 x 53.34 mm、J14/J15中心間隔15.24 mmを基準に配置する。
- J14/J15の嵌合位置は維持し、基板外形は79 x 53.34 mmとする。J15より右側へ33 mm
  延長し、外部ハーネスがCarrier本体側へ回り込まない構造にする。
- 外部モジュール向けコネクタはすべてXH2.54垂直型とする。
- J_AMP_SIG、J_AMP_PWR、J_MICはすべてJ15ヘッダより右側へ配置する。

### 3.2 音響コネクタ

| Ref | 極数 | XH2.54のピン順 | Carrier接続／既定値 |
|---|---:|---|---|
| J_AMP_SIG | 4 | LRC, BCLK, DIN, GAIN | J15-34, J15-32, J15-38, R_GAIN |
| J_AMP_PWR | 3 | SD, GND, VIN | R_SD/JP_MUTE, GND, J14-7 (+5V) |
| J_MIC | 6 | GND, VCC, SD, SCK, WS, L/R | GND, J14-19 (+1V8), J15-36, J15-32, J15-34, R_LR |

- MI2S0 BCLK = SOC_GPIO_98 = J15-32、WS/LRCLK = SOC_GPIO_99 = J15-34。
- マイクデータ候補 = SOC_GPIO_100 = J15-36。
- アンプデータ候補 = SOC_GPIO_101 = J15-38。
- 上記4信号はすべてQRB2210の1.8 Vドメインである。
- マイクVCCはJ14-19の+1.8 V、MAX98357A VINはJ14-7の+5 Vを使う。
- `R_GAIN`と`R_LR`は実装時0 ΩでGNDへ接続し、既定状態を固定する。変更時は
  0 Ω抵抗を取り外して所望のストラップ抵抗へ置換する。
- `R_SD`は100 kΩで3.3 Vへプルアップし、MAX98357Aを既定で有効にする。
  `JP_MUTE`に2.54 mmジャンパシャントを挿すとSDをGNDへ落としてミュートできる。
- `R_GAIN`、`R_LR`、`R_SD`はリードピッチ10.16 mmのアキシャル抵抗、C2/C3は
  リードピッチ5.00 mmのラジアル積層セラミック、C1はラジアル電解、
  JP_MUTEは2.54 mmスルーホールピンヘッダとする。すべてスルーホール実装とする。
- C1は10 uF / 10 V以上で+5 Vをデカップリングし、C2=100 nFを並列配置する。
  C3=100 nFは+1.8 Vをデカップリングする。C1の極性はPin 1=+5 V、Pin 2=GND。
- DATA0/1のcapture/playback方向、Device Tree、codec DAI、ALSA routeが実機確定する
  までは、音響モジュールを接続・通電しない。

### 3.3 基板間XH電源ケーブル

Board BはUNO Breakout CarrierのJ14から+5 V、+1.8 V、GNDを取得できるため、
Board AからBoard Bへ電源を渡すXHケーブルは現仕様では不要である。将来Carrierを
使わず別置きする場合は、XH2のPin 1=+5 V、Pin 2=GNDで追加し、逆給電が起きない
電源経路を別途レビューする。

## 4. 配線・製造ルール

- 2層FR-4、1.6 mm、1 oz銅を初期値とする。
- 3.3 V/1.8 V信号線は0.25 mm以上、一般電源は0.50 mm以上。
- 5 V入力およびサーボ電源は細いトラックではなく両面の広い銅箔で配線し、
  サーマルネックを作らない。
- GNDプレーンを両面に設け、適切なスティッチングビアを配置する。
- I2SのBCLK/WSは短く、並走長を抑え、サーボ5 V配線と離す。
- 全コネクタにRef、信号順、Pin 1マーク、電圧をシルク印刷する。
- EDA設計の正本は`board/Ichiping uno q.eprj2`だけとする。2枚ともEasyEDAの
  Board内でネイティブ回路図とPCBを関連付け、部品Ref、Unique ID、回路図ピン番号、
  PCBパッド番号、ネット、外形、配線、シルクを一体管理する。外部EDAとの変換・同期は
  行わない。
- 製造前にEasyEDAのPCB DRCを両基板で実行し、クリアランス、異ネット短絡、
  接続エラー、未配線、基板外形干渉をすべて0件とする。
- 回路図のDevice／FootprintはPCBと同じプロジェクト内レコードへ関連付ける。
  カスタムDRCの124番`Schematic Netlist`を含む全項目を有効にし、`All (0)`を必須とする。
  Ref、Unique ID、ピン／パッド番号、ネット名の対応監査はUNOシールド19部品／70ピン、
  Audioシールド12部品／107ピンを対象とし、差分0件を必須とする。UNOシールドの取付穴4個は
  直径3.2 mmの独立した非メッキ穴として扱い、電気部品のネットリストには含めない。
- 製造前にEasyEDAの回路図DRCも両Boardで実行し、各部品のRef、Unique ID、ピン／
  パッド番号、ネットが対応することを確認する。回路接続は本仕様書、
  `docs/uno_q_port.html`、回路図、PCBネット、各基板の`bom.csv`を突き合わせて
  レビューする。

## 4.1 実装方式（単一設計）

UNOシールドと音響シールドは、次の実装方式だけを正規設計とする。

| 部品種別 | 実装方式 |
|---|---|
| UNO／キャリア接続ヘッダ、XH2.54、ジャンパなど全コネクタ | スルーホール |
| 極性付き電解コンデンサ | ラジアル・スルーホール |
| UNOシールドの`C_PWR_HF` | 100 nFラジアル・スルーホール、5.00 mmピッチ |
| Audioシールドの固定抵抗 | アキシャル・スルーホール、10.16 mmピッチ |
| Audioシールドの無極性コンデンサ | ラジアル・スルーホール、5.00 mmピッチ |

- 正規設計は`uno_shield/`と`audio_shield/`だけに保存し、実装方式別の派生版は作らない。
- 外形、Ref、ネット名、コネクタのピン番号と2.54 mm中心間隔を維持する。
- `J_PWR_IN`はUNO Qの`+5V`へ接続し、`VIN`へ接続しない。
- 外部コネクタは指定どおり垂直XH2.54互換品とする。
- EasyEDAの回路図DRC、PCB DRC、回路図／PCB対応監査と目視レビューで実装属性、
  ピン順、ピッチ、5 V/VIN分離を監査し、各PCBのDRC=0、接続エラー=0、未配線=0を
  製造前の必須条件とする。

## 5. 参照資料

- UNO Q datasheet: https://docs.arduino.cc/resources/datasheets/ABX00162-ABX00173-datasheet.pdf
- UNO Q full pinout: https://docs.arduino.cc/resources/pinouts/ABX00162-full-pinout.pdf
- UNO Breakout Carrier datasheet: https://docs.arduino.cc/resources/datasheets/ASX00085-datasheet.pdf
- 元IchiPing配線図: `docs/pins.xlsx`
- UNO Q GPIO正本: `docs/uno_q_port.html`
