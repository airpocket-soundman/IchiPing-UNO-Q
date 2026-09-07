# ILI9341 TFT pin mapping

版: 配線確認表 / 2026-09-07

この表は、UNO Qシールドの2個のTFT用XHコネクタと、ILI9341 SPIディスプレイ
モジュールの端子対応を示す。XHの番号は基板上面から見てPin 1マーク側を起点とする。

## UNO Q端子からディスプレイ端子への対応

| UNO Q端子 | シールド上の信号 | ILI9341モジュール端子 | 使用するXH端子 |
|---|---|---|---|
| A4 | TFT_DC | DC / D-C / RS | J_TFT_SIG Pin 5 |
| D11 | SPI MOSI | MOSI / SDI / SDA | J_TFT_SIG Pin 4 |
| D13 | SPI SCK | SCK / CLK | J_TFT_SIG Pin 3 |
| A5 | TFT_BL | LED / BL | J_TFT_SIG Pin 2 |
| D12 | SPI MISO | MISO / SDO | J_TFT_SIG Pin 1 |
| 3V3 | TFT_VCC | VCC / 3V3 | J_TFT_PWR Pin 4 |
| GND | GND | GND | J_TFT_PWR Pin 3 |
| A2 | TFT_CS | CS | J_TFT_PWR Pin 2 |
| A3 | TFT_RST | RST / RESET | J_TFT_PWR Pin 1 |

## J_TFT_SIG（5極）の物理ピン順

| XH Pin | シルク表示 | UNO Q端子 | ILI9341モジュール端子 |
|---:|---|---|---|
| 1 | MISO | D12 | MISO / SDO |
| 2 | LED | A5 | LED / BL |
| 3 | SCK | D13 | SCK / CLK |
| 4 | MOSI | D11 | MOSI / SDI / SDA |
| 5 | DC | A4 | DC / D-C / RS |

## J_TFT_PWR（4極）の物理ピン順

| XH Pin | シルク表示 | UNO Q端子 | ILI9341モジュール端子 |
|---:|---|---|---|
| 1 | RST | A3 | RST / RESET |
| 2 | CS | A2 | CS |
| 3 | GND | GND | GND |
| 4 | VCC | 3V3 | VCC / 3V3 |

## 配線上の注意

- TFTモジュールは3.3 V動作品を使用し、VCCを5 VやVINへ接続しない。
- `LED/BL`はバックライト制御入力であり、A5から制御する。モジュール側に
  バックライト用抵抗・トランジスタが搭載されている構成を前提とする。
- 現行ドライバは表示書き込み専用だが、指定されたハーネス互換性のためD12を
  `MISO/SDO`へ接続する。
- モジュールによって`MOSI`が`SDI`または`SDA`、`DC`が`D/C`または`RS`、`SCK`が
  `CLK`と表記される場合がある。タッチパネル用のT_CS/T_CLK/T_DIN等とは接続しない。
