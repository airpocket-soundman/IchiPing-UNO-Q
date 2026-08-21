# IchiPing UNO Q

IchiPingをArduino UNO Qへ移植する独立プロジェクトです。元の
[`airpocket-soundman/IchiPing`](https://github.com/airpocket-soundman/IchiPing)
は変更せず、既存の信号処理、32状態ラベル、学習・評価資産をこのリポジトリへコピーして出発しています。

## 現在の到達点

- UNO QをUSBのCOMポートとADBデバイスとして認識
- QRB2210上のDebianとSTM32U585上のArduino/Zephyrを確認
- Arduino App Lab形式のbring-upアプリを追加
- 内蔵8×13 LED Matrixに5状態と信頼度を表示
- D3–D7の状態入力、D8のEXEC、D9の雨入力を割り当て
- D20/D21のI²CでPCA9685（0x40）を非破壊検出
- Router BridgeでLinux PythonとMCUスケッチを接続
- 2026-08-21実機smoke test PASS（Bridge往復、Matrix API、GPIO読取、I²C未接続処理）

音響推論はまだloopbackです。既存INMP441/MAX98357AはQRB2210の1.8 V MI2S0を第一候補として再利用を評価します。信号は標準UNOヘッダではなくJMISC／UNO Breakout Carrier経由のため、Device TreeとALSA routeを確定してから接続します。USB Audioはフォールバックです。
Debian上ではALSAデバイスが列挙されますが、外部音響機器なしの16 kHzモノラル録音プローブは`EINVAL`となるため、音響経路は未合格です。

推論はQRB2210 / Debian側で精度を最優先します。現行XL（約0.7 MiB）に縛られず、FP32の大型モデルや2〜3モデルensembleも比較し、未知の収録条件で精度が上がった候補を採用します。

## 設計資料

- [UNO Q移植方針・センサ接続・GPIO](docs/uno_q_port.html)
- [UNO Q精度優先AI方針](docs/uno_q_ai_strategy.html)
- [UNO Q bring-upアプリ](uno_q/README.md)
- [元IchiPing仕様のコピー](docs/spec.html)
- [既存NN設計](docs/nn_design.html)
- [既存データ採取・学習資産](pc/README.md)

## アーキテクチャ

| 層 | UNO Q側 | 担当 |
|---|---|---|
| リアルタイムI/O | STM32U585 / Zephyr | GPIO、I²C、サーボ、LED Matrix、推論トリガ |
| アプリ・推論 | QRB2210 / Debian | 特徴量、モデル推論、保存、ネットワーク |
| MCU–Linux通信 | Arduino Router Bridge | 状態・推論要求・推論結果 |

## LED Matrix表示

左から窓a、窓b、窓c、扉AB、扉BCの5セルです。明るいセルは開、暗いセルは閉を示します。右端の縦バーは信頼度、中央から広がる菱形はping／推論中です。

## bring-upアプリの実行

Arduino App Labで `uno_q/app` を開くか、USB接続したUNO Qへ同フォルダを転送し、UNO Q上で実行します。

```sh
TMPDIR=/tmp arduino-app-cli app start /home/arduino/ArduinoApps/ichiping-uno-q
TMPDIR=/tmp arduino-app-cli app logs /home/arduino/ArduinoApps/ichiping-uno-q --all
```

## 移植ロードマップ

1. Matrix・Bridge・GPIO・PCA9685検出のbring-up
2. PCA9685 + SG90 ×5と既存サーボ座標の移植
3. MI2S0（USB Audioをフォールバック）による16 kHzモノラル録音とping再生
4. 既存モデルをbaselineに、精度優先の大型モデルとensembleをLinux側で比較
5. 起動時実行、ログ、ネットワーク通知の統合

## リポジトリ構成

| パス | 内容 |
|---|---|
| `uno_q/app/` | UNO Q用Arduino App Labアプリ |
| `uno_q/tools/` | ONNX実機ベンチなどUNO Q評価ツール |
| `docs/uno_q_port.html` | 開発方針、配線、GPIO、Matrix表示規約 |
| `docs/uno_q_ai_strategy.html` | 精度指標、モデル探索、実機資源上限 |
| `firmware/` | 元FRDM-MCXN947実装（移植参照） |
| `pc/` | データ採取、学習、評価、既存モデル資産 |
| `hardware/` | 元ハードウェア資料（UNO Q版は上記HTMLを正とする） |

## ライセンス

元IchiPingのライセンス条件を継承します。Arduino提供コードを参照した箇所は各ファイルのライセンス条件に従います。
