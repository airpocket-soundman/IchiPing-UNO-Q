# I²S外部計測の準備（2026-09-10）

**次の実機環境はオシロあり・ロジアナなし。アンプ/マイク試験は
[引き継ぎ・実験計画](HANDOFF_SCOPE_TEST.md)を優先する。**
以下のロジアナ手順は今回の環境での再現用であり、次環境の必須条件ではない。

2026-09-11追記: [無負荷信号監査](reports/2026-09-11-i2s-signal-audit.md)で、
SLogicの4ch・50 MS/s・トリガーなし取得とサインPCM完全一致を確認。
ただしBCLKのみ残る停止区間があるため、下記のアンプ再接続手順へそのまま進まず、
まずSDを含む有効化/停止順序を解決する。発音の合格ではない。
同日追加の `instrument-duplex FILE`（無負荷用）は同じPCMで再生RUNNING確認後に録音を開始し、
一意の録音ファイルを作る。500ms再起動予約は維持するが実測クロックは約1.02秒続いた。
再生＋録音でも基準PCM一致。詳細と計測器警告は上記監査記録を参照。

状態: オフライン実装後、2026-09-10に公式OWONアプリ・ドライバーを導入。
再生専用モードで無負荷ゼロPCMを1回実行したが、オシロの単発トリガーは成立せず。
波形取得・出力合否は未確認。詳細は[初回測定記録](reports/2026-09-10-scope-unloaded-01.md)。
OWON APIの補償信号取得・CSV保存は実装し実測成功。ただしレンジ依存の電圧不整合が
再現しており電圧評価は未成立。詳細は[API測定記録](reports/2026-09-10-owon-api.md)。
その後APIでBCLK約3.072 MHz、WS約48 kHzを取得。WS周期当たり64クロックを確認。
WSはBCLK開始より遅れるため、`--trigger-ch 2`でWS自身にトリガーして取得する。
詳細は[無負荷API測定](reports/2026-09-10-owon-i2s.md)。Sipeedソフトは未導入。
GPIO101も取得し339ビットが送信PCM部分列と一致。WS未同時取得のためフレーム位相は未判定。
詳細は[データ線測定](reports/2026-09-10-owon-din.md)。
WS/DIN同時取得でも、WS半周期32bitを仮定した標準I²S位置の18スロットが送信PCMと一致。
BCLK同時取得なし・先頭正値のみの確認なので、全期間・setup/hold・音響品質は未判定。
正本の配線は `../../docs/uno_q_port.html`。GPIO番号は標準UNOのD番号ではない。

## 接続・順番

ロジアナ固定: D0=GPIO98/BCLK、D1=GPIO99/WS、D2=GPIO101/DIN、
D3=GPIO100/マイクSD。D4～15未接続。GNDは共通GNDのみ。
最初は拡張ボード側の同じ測定点で比較する。

| 順番 | 外部ボード | オシロCH1 | オシロCH2 |
|---|---|---|---|
| 1 | アンプ・マイクなし | 98 BCLK | 99 WS |
| 2 | 同上 | 98 BCLK | 101 DIN |
| 3 | アンプのみ | 98 BCLK | 99 WS |
| 4 | 同上 | 98 BCLK | 101 DIN |
| 5 | アンプ＋マイク | 98 BCLK | 99 WS |
| 6 | 同上 | 98 BCLK | 101 DIN |
| 7 | 同上 | 98 BCLK | 100 マイクSD |

電源OFFで接続変更。未給電の外部ボードに信号線だけ残さず、バックパワーを避ける。
1.8Vロジック。入力専用、短いGND、プローブ・測定位置を揃える。
スピーカー＋／−にGNDクリップを接続しない。USB絶縁はチャンネル間絶縁ではない。
GPIO100はマイク未接続時には評価しない。

## 機器APIの接続確認（次回、発音前）

- OWONは型番VDS1022I（末尾Iを仮定）、実機・API版・プローブ倍率・校正設定を確認。
  ユーザーの利用可能APIを優先。公開候補の
  [vds1022 Python API](https://github.com/florentbr/OWON-VDS1022) は**非公式**。
  native USBがそのままSCPIであるとは仮定しない。
- SLogicは[Sipeed対応libsigrok](https://github.com/sipeed/libsigrok/tree/slogic-dev)
  / sigrok-cliの実際のdriver名、channel名、選択可能レート、しきい値を確認。
  [公式ガイド](https://wiki.sipeed.com/hardware/en/logic_analyzer/slogic16u3/Software_User_Guide.html)。
- ドライバー更新・置換、ファーム更新、プラグイン導入は今回行っていない。
  OWONは `owon-capture.py` で補償信号とI²SクロックをAPI取得可能（電圧不整合調査中）。
  `--profile i2s --i2s-rate 25000000` は200µs、既定100MS/sは50µs。
  armed.jsonの未トリガー状態を確認してから別途UNO Qの500ms試験を開始する。
  Sipeed取得アダプターは未実装。UNO Qはarmed.json確認後に別途安全試験を開始する。
  以下のCSVは内部交換形式であり、ベンダーのCSVを無変換で読めるという意味ではない。

ロジアナは対応する50～100MS/s付近、4ch、しきい値約0.9Vから実測に合わせる。
生セッション（例 .sr）も保存し、2秒程度の取得を先にarm/readyにする。
オシロは2chの短時間・高サンプルレート取得。初回は平均化しない。
25MHz帯域ではns単位のエッジ品質の完全な検証はできない。
長い受動記録と、UNO Qの500ms動作期限は別。記録開始時刻だけで同期済みと扱わず、
実際のBCLK開始・終了と、終了後の取得余白を確認する。

## オフライン準備

リポジトリルートから（Python標準ライブラリのみ）:

```powershell
python uno_q/audio/instrument-analysis.py prepare uno_q/audio/local-runs/instrument-prep-001
python -m unittest discover -s uno_q/audio -p 'test_*offline.py'
```

既存ディレクトリを上書きしない。zero.raw、sine.raw、manifest.jsonを生成。
48kHz stereo S32_LE（上位24bit）、500msファイル。sineは100ms先行ゼロ、
100msの440Hz音（5msフェード）、300ms末尾ゼロ。ピークは厳密に0.01%FS以下。
左右同値なので、これだけでは左右入れ替わりを証明できない。
manifestの機器・ボード・ソフト・接続状態・設定欄は実測時に埋め、
生データ・変換データ・解析結果を実験ごとの別ディレクトリに保存する。

## 次回の実機試験（今は実行しない）

1. 電源OFFで指定の配線状態にし、UNO QのUSB VID/PID・serialを確認。
2. 計測器で無動作時の取得・数値保存を確認。manifestに条件を記録。
3. 計測器の取得準備完了後、生成済みzero.rawだけを次の新モードで送る。
4. 波形・PCM・開始停止を評価し、異常があればその段階で止める。
5. 正常なら同じ設定でsine.raw。変更要因は一つずつ。

ボードに必要ファイルを配備してから使うコマンド（ボード上の例）:

```sh
sudo ICHIPING_EXPECTED_USB_SERIAL=2261748543 ./safe-audio-test.sh instrument-playback /path/to/zero.raw
```

このモードはUSB識別照合・PCM検証後、ルート有効化前に独立500ms直接リセットを予約。
再生ルートのみを開き、録音ルートは開かない。転送はリセットで中断し得る。
**500msはソフトウェア期限であり、音響停止の保証ではない。** ゼロPCMも物理ミュートではない。
capture routeを閉じた状態でマイクSDが駆動されるかは実測対象。
出力側の問題を解消するまで、録音経路を追加する変更は混ぜない。
通常の再生コマンドや測定ソフトから直接発音しない。

## ロジアナ解析

内部CSVヘッダ: `time_s,bclk,ws,din,mic`（mic省略可）。
秒単位・有限・厳密増加の時刻、各行はその時刻で更新後の全信号状態、論理値0/1。
均一サンプルまたは変化時だけの行を許容するが、BCLKの立ち下がりを省略しない。
同時刻の信号別イベントは変換時に一行に統合。単位変換・channel対応を必ず確認。
大きい取得では無変化行を省略し、生データは別途保持する。

```powershell
python uno_q/audio/instrument-analysis.py decode capture.csv uno_q/audio/local-runs/decoded-001
```

標準I²S、32bit/slot、WS=0左、BCLK立ち上がりで復号する。
WS変化を観測したエッジは前slotのLSB、次エッジが新slotのMSB。
最初と最後の不完全slotを捨て、長短slot・クロック欠落・立ち上がりと同時の信号変化を報告。
同時変化フラグは取得分解能による可能性もあり、単独でsetup/hold違反と断定しない。
report.jsonとdecoded.csvを保存。マイクは `--data-column mic` で別解析するが、
非駆動slotや有効bit数はマイク仕様に沿って別途解釈する。

基準データとの比較は、最初の完全な左slotが基準ファイルの何frame目かを
開始部の記録から確認して、明示的に指定する（例の0を盲目的に使わない）:

```powershell
python uno_q/audio/instrument-analysis.py decode capture.csv uno_q/audio/local-runs/compared-001 --reference uno_q/audio/local-runs/instrument-prep-001/sine.raw --reference-frame-offset 0
```

これはDSPがwire wordを保持するという仮説の完全一致比較。DSP変換は別途確認する。
都合のよい区間へ自動整列せず、不一致数・比較範囲を報告。短い一致を全体成功としない。
無データ、末尾切れ、周波数異常、電気波形の崩れを「正常」と扱わない。
440Hz成分の存在やデジタル一致だけでは、正常発音／正常電圧／確実な消音とは判定しない。

オシロは生波形と `time_s,ch1_v,ch2_v` 相当の電圧データ、設定を保存し、
電圧範囲・リンギング・クロックとデータの関係を確認する。
現時点で電気的合否の自動判定は実装していない。
