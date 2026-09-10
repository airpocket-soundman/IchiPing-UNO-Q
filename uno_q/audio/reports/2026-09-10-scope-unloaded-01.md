# 無負荷BCLK/WS測定 — 2026-09-10 19:07 JST

判定: **測定未成立（トリガー未検出）。クロック出力の合否は未判定。**

## 条件

- ユーザー確認: アンプ・マイクを両方取り外し、共通GND、両プローブ×10。
- CH1=GPIO98/BCLK、CH2=GPIO99/WS。拡張ボード側。
- OWON USB VID:PID=5345:1234、USB識別文字列VDS1022。
  I付き型番かは実機ラベル未確認。
- 公式アプリV1.1.7、libusb-win32 1.2.6.0（oem98.inf）、Windows問題コード0。
- アプリ画面で両CH ×10/DC、各2 V/div、2 µs/div、100 MS/s、5k points。
  CH1立ち上がり640 mV、単発取得のReady表示を確認して試験開始。
- ボードUSB VID:PID=2341:0078、serial=2261748543。
- kernel=6.16.7-g0dd6551ae96b。
- q6asm-dai.ko SHA256=c4292c7c9504c7aa01a94cd0007b86213def67a1d4a8123dd23be3ff92653526。
- 再生前にALSA card Arduino-Imola-IchiPing-MI2S0を確認。
- 試験コードは未コミットのinstrument-playbackモードを
  `/var/tmp/ichiping-scope-20260910-01/` に配備。
- safe-audio-test.sh SHA256=642d3eebc6a09c0bc3584b7953acab231fd19d2bd620e67a4396ca80536e4d09。
- audio-smoke-test.py SHA256=f5bfd1e634b26fda71fbac64095d84d9635522024320455c1adc290694258c86。
- route-mi2s0.sh SHA256=9d97ef8e84355a43c7e8d98683dc0cf6e3f422daf60131f3dcd08d7c93619bac。
- zero.raw SHA256=ea0787f65f73b0013d03b359490e3125211b28ad5c1502ffb1544c0ded4192f5。
  48kHz stereo S32_LE、500ms、全ゼロ。録音ルートは開いていない。

## 観測

ボード時刻2026-09-10T10:07:40+00:00にUSB識別とPCM検証成功。
aplayは「Playing raw data ... Signed 32 bit Little Endian, Rate 48000 Hz, Stereo」
まで出力した。ただし、この行はPCM RUNNING／ピンのクロック出力成立を証明しない。

前回ブートのjournalには10:07:41 UTCに独立watchdog service起動と
`systemctl: Rebooting.` を確認。再起動後boot_idは
`39547583-ec7d-48df-844a-9f9552c43c6b`。
ログは秒精度なので、正確な500ms停止の実測証拠にはならない。

オシロは試験後もReadyのままで単発取得が成立しなかった。
画面に残る波形は取得前のものなので、I²S測定結果として保存・解釈しない。
生波形ファイルは得られていない。最後に取得をStopへ戻した。

再起動後 `/proc/asound/cards` は `--- no soundcards ---`。
ADSP remoteproc1はrunningだがsoundおよびSoundWireのprobeが
LPASS pinctrl supplier待ち。既知の起動不安定症状と整合するが、
今回のトリガー未検出と同一原因とは断定しない。

## 次の切り分け

1. オシロ補償出力でプローブ・取得経路を検証する（測定点の付け替えが必要）。
2. ボードのALSA/LPASS復帰を確認する。
3. 500ms期限を延長せず、実際のPCM RUNNING成立時刻とクロック開始を確認する。
4. GPIO98/99の波形取得後にGPIO101のデータ確認へ進む。

本試験はスピーカー発音・マイク録音の合否を更新しない。

## 追試: CH1の補償出力確認（同日）

ユーザーがCH1を本体の「5V 1kHz」補償出力へ付け替えた。
UNO Qの再生・リセット命令は実行していない。
Computer Useで公式アプリのオートセット後、200µs/divへ変更。
CH1 DC・×10、5V/div、1.25MS/s、5k pointsで、周波数表示1.000kHz、
画面上約1div（約5Vpp）の方形波を確認した。
これは画面読み取りであり、電圧の精密測定や校正完了を意味しない。

オートセットはAlternateトリガーを選んだため、Singleソース/CH1へ明示変更。
レベルをSet 50%で3.200Vへ設定し、右上の単発取得ボタンを押した。
波形取得後、Stop表示と再生ボタン表示への復帰を確認。
CH1の信号取得・トリガー・単発停止という基本機能は成立した。
GPIO98の3.072MHz信号に対する帯域・電圧精度・プローブ補償の厳密な評価は未実施。
CH2は補償出力への接続を依頼しておらず、表示された低周波成分を
UNO Qの異常として解釈しない。CH2の測定経路は未検証。

最終設定: 取得Stop、200µs/div、CH1=5V/div、CH2=100mV/div、
CH1立ち上がり3.200V。GPIO測定に戻す際は1.8V用の設定へ戻す必要がある。
