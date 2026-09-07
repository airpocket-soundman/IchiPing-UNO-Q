# Audio shield pin mapping

版: 配線修正版設計入力 / 2026-09-07

この表は、UNO Breakout Carrierに重ねるAudio shieldの回路図・PCBを修正するための
正本である。コネクタ番号はCarrier公式回路図のJ14/J15、XH番号は基板上面から見た
Pin 1マーク側を起点とする。

## UNO Breakout Carrier側の使用端子

| Carrier端子 | 公式信号名 | MI2S0機能 | 方向（UNO Q基準） | 電圧 | 接続先 |
|---|---|---|---|---:|---|
| J15-32 | SOC_GPIO_98 | MI2S0_CLK | 出力 | 1.8 V | MAX98357A BCLK、マイク SCK |
| J15-34 | SOC_GPIO_99 | MI2S0_WS | 出力 | 1.8 V | MAX98357A LRC、マイク WS |
| J15-36 | SOC_GPIO_100 | MI2S0_DATA0 | 入力 | 1.8 V | マイク SD（DOUT） |
| J15-38 | SOC_GPIO_101 | MI2S0_DATA1 | 出力 | 1.8 V | MAX98357A DIN |
| J14-7 | +5V USB OUT | — | 電源出力 | 5 V | MAX98357A VIN、SD |
| J14-19 | +1V8 OUT | — | 電源出力 | 1.8 V | マイク VCC |
| J15-40 | GND | — | — | 0 V | 全GND、GAIN、L/R |

J15の音響信号4本はすべて偶数ピンである。2x20ヘッダは `1-2, 3-4, ...,
39-40` のペアで番号を付ける。基板の表裏で見た目が左右反転するため、外形上の
左右ではなく、CarrierとAudio shield双方のPin 1表示とパッド番号で照合する。

## MAX98357A用XHコネクタ

### J_AMP_SIG（4極）

| XH Pin | 表示 | Carrier接続 | MAX98357A端子 | 備考 |
|---:|---|---|---|---|
| 1 | LRC | J15-34 / SOC_GPIO_99 | LRC | MI2S0_WS |
| 2 | BCLK | J15-32 / SOC_GPIO_98 | BCLK | MI2S0_CLK |
| 3 | DIN | J15-38 / SOC_GPIO_101 | DIN | MI2S0_DATA1 |
| 4 | GAIN | J15-40 / GND | GAIN | GND直結、12 dB固定 |

### J_AMP_PWR（3極）

| XH Pin | 表示 | Carrier接続 | MAX98357A端子 | 備考 |
|---:|---|---|---|---|
| 1 | SD | J14-7 / +5V | SD / MODE | VINへ直結して常時有効、左ch選択 |
| 2 | GND | J15-40 / GND | GND | 共通GND |
| 3 | VIN | J14-7 / +5V | VIN | アンプ電源 |

## I2Sマイク用J_MIC（6極）

| XH Pin | 表示 | Carrier接続 | INMP441等の端子 | 備考 |
|---:|---|---|---|---|
| 1 | GND | J15-40 / GND | GND | 共通GND |
| 2 | VCC | J14-19 / +1V8 | VDD / VCC | 1.8 V給電 |
| 3 | SD | J15-36 / SOC_GPIO_100 | SD / DOUT | MI2S0_DATA0、UNO Qへの入力 |
| 4 | SCK | J15-32 / SOC_GPIO_98 | SCK / BCLK | MI2S0_CLK |
| 5 | WS | J15-34 / SOC_GPIO_99 | WS / LRCLK | MI2S0_WS |
| 6 | L/R | J15-40 / GND | L/R / SEL | GND直結、左ch固定 |

## 部品を置かない方針

Audio shieldにはJ14、J15、J_AMP_SIG、J_AMP_PWR、J_MIC以外を実装しない。
抵抗、ジャンパ、電解コンデンサ、セラミックコンデンサは置かず、GAIN、SD、L/Rは
上表どおり銅配線で固定する。使用するMAX98357AおよびI2Sマイクは、必要な電源
デカップリングを搭載済みのブレークアウトモジュールを前提とする。裸ICを接続する
設計にはこの省略方針を適用しない。

MAX98357Aのデジタル入力High最小値は1.3 Vのため、UNO Qの1.8 V MI2S0と直結可能で
ある。INMP441は1.62～3.63 V電源に対応するため、VCCをCarrierの1.8 Vへ接続する。

現行EasyEDAのAudio shieldはこの表と一致するよう修正し、回路図とPCBのネット対応、
表裏ミラー、未配線、短絡をDRCで再確認するまで製造データとして使用しない。

## 一次資料

- Arduino UNO Breakout Carrier datasheet: https://docs.arduino.cc/resources/datasheets/ASX00085-datasheet.pdf
- Arduino UNO Breakout Carrier schematic: https://docs.arduino.cc/resources/schematics/ASX00085-schematics.pdf
- Arduino UNO Breakout Carrier full pinout: https://docs.arduino.cc/resources/pinouts/ASX00085-full-pinout.pdf
- Analog Devices MAX98357A/B datasheet: https://www.analog.com/media/en/technical-documentation/data-sheets/MAX98357A-MAX98357B.pdf
- TDK InvenSense INMP441 datasheet: https://invensense.tdk.com/wp-content/uploads/2015/02/INMP441.pdf
