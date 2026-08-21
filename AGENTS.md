# AGENTS.md — IchiPing UNO Q 作業ガイド

このリポジトリはIchiPingをArduino UNO Qへ移植する独立プロジェクトです。
元の `airpocket-soundman/IchiPing` は参照元であり、ここでの作業から変更しません。

## 正本と独立性

- UNO Q版の開発方針、配線、GPIOの正本は `docs/uno_q_port.html`。
- UNO Q実装の正本は `uno_q/app/`。
- `firmware/` と既存の `hardware/` はFRDM-MCXN947版からコピーした移植参照資料。
- 元IchiPingまたは `digikey_project` への逆同期は、ユーザーが明示的に依頼した場合だけ行う。
- 元IchiPingのリモートや作業ツリーを変更しない。

## 技術方針

- ボード: Arduino UNO Q。
- リアルタイムI/O: STM32U585 / Zephyr / Arduino sketch。
- 推論・保存・ネットワーク: QRB2210 / Debian / Python。
- MCU–Linux通信: Arduino Router Bridge。
- 表示: 内蔵8×13 blue LED Matrix。
- 状態順: bit 0..4 = 窓a、窓b、窓c、扉AB、扉BC。
- PCA9685: `Wire`、D20/SDA、D21/SCL、アドレス0x40。
- GPIO: D3–D7状態入力、D8 EXEC、D9雨入力。すべて3.3 V系で扱う。
- サーボ電源は外部5 V、UNO QとGND共通。UNO Qの3.3 V端子から給電しない。
- 音響I/Oは未確定。標準UNOヘッダに公式I²S割り当てがないため、INMP441/MAX98357Aの未検証直結は禁止。USB Audioを第一候補として検証する。

## 移植の進め方

1. Matrix、Bridge、GPIO、I²Cのbring-upを通す。
2. PCA9685とSG90を、1チャンネルずつ安全な角度範囲で検証する。
3. 音響経路を確定し、16 kHz / mono / PCMの録音とping再生を確認する。
4. PC版とUNO Q版の特徴量を同じ入力で比較する。
5. モデル推論を統合し、32状態評価を行う。
6. 起動時実行と障害回復を追加する。

## 実機作業の安全規則

- 書き込み前に対象がUNO QであることをUSB VID/PIDまたはADB serialで確認する。
- PCA9685の検出だけではサーボを動かさない。電源・GND・機械端を確認してからPWMを有効化する。
- GPIO、I²C、Matrixのテストは外部ハード未接続でも失敗せず継続できる構造にする。
- loopback、dummy、実モデルの結果をログと画面で明確に区別する。
- UNO Qのブート後20–30秒はMatrixがブート表示に使用されるため、OS起動完了後にアプリを開始する。

## ドキュメント規則

- 開発方針、配線、GPIOを変えたら `docs/uno_q_port.html` を同時更新する。
- `README.md` と `index.html` は同じ事実・状態・ロードマップを維持する。
- `AGENTS.md` と `Codex.html` は同じ作業方針を維持する。
- 図はSVGで作り、ASCIIアートや罫線による擬似図は使わない。
- 実機テスト結果には、日時、ボード識別、ソフトウェア版、合否、未接続機器を記録する。

## Git

- このリポジトリだけでコミットする。
- GitHubリポジトリ名は `airpocket-soundman/IchiPing-UNO-Q`。
- 生成キャッシュ、仮想環境、秘密情報、App Labの `.cache` はコミットしない。
