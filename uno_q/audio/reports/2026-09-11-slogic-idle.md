# SLogic16 U3 初回取得 — 2026-09-11 JST

- アンプ・マイクはユーザー確認により未接続。
- UNO Q: ADB serial `2261748543`。管理者権限の確認 `sudo -n true` はパスワード要求で失敗。試験信号は出していない。
- SLogic16 U3: serial `202512191855`、USB `359f:3031`。通常モードで検出・取得成功。
- ソフト: SLogic release-1.1.0、sigrok-cli 0.8.0 / libsigrok 0.6.0。
- 配置: `C:/Users/yamashita_y00031/Downloads/windows-x86_64-ucrt`。
- 同梱SHA256SUMSと3実行ファイルのハッシュ一致。独立した真正性保証ではない。CLIは電子署名なし。
- 取得: 50 MS/s、5,000,000 samples、100 ms。しきい値指定 `voltage_threshold=0.9-0.9`。
- D0～D3を指定したが、取得データは16ch・2 bytes/sampleで保存された。受信10,000,000 bytes、保存ファイルのサンプル数も一致。
- ローカル生データ: `uno_q/audio/local-runs/slogic-idle-20260911-121048/idle.sr`。同フォルダのCSVはベンダー出力のままで、内部解析形式へ未変換。時間単位・dedup挙動を確認するまで解析入力に使わない。

## 判定

USB通信と有限長の受動取得・保存は成功。I2S信号の周波数、データ一致、配線、音響品質は未判定。
過去PCでの「DFUのみ認識」はこのPCでは再現していない。

## 次の作業

UNO Q側の管理者認証と最新安全試験スクリプトの別ディレクトリ配備を行い、ロジアナ取得開始後に短時間ゼロPCM試験を実行する。
既存の古い `/var/tmp/safe-audio-test.sh` はそのまま実行しない。

## 同日追記: 管理者認証・ゼロPCM取得

- ユーザー指定により今後の試験ユーザーは `airpocket`。
- 実機の `id airpocket` と `getent group sudo` で既存のsudoグループ所属を確認。sudo認証と試験実行も成功。追加の権限変更・NOPASSWD設定はしていない。
- 最新スクリプトを `/var/tmp/ichiping-instrument-20260911-01/` に別途配備。PCのオフライン25テスト成功、実機でzero/sineのネイティブPCM検証成功。
- ロジアナをD0立上り待ちにしてから、500msリセット予約付きinstrument-playbackでzero.rawを実行。UNO Qは再起動しADB再接続確認済み。
- 生データ: `uno_q/audio/local-runs/instrument-prep-20260911-01/zero-capture.sr`。
- 要調査: 指定100,000,000 samplesに対しCLI末尾は96,250,496 samplesと報告し、SRファイル内チャンク合計は106,250,496 samples。取得・トリガー・保存の整合性を確定するまで全期間合格にしない。
- SRチャンクをサンプル番号から直接CSV化した一次解析: 59,229完全スロット、DATAは全てゼロ。短いスロット12、長いスロット8、WSの立上り同時変化3。クロック区間約0.623秒、末尾静止約1.302秒。BCLK周期中央値はサンプル量子化の影響を受けるため公称周波数との単純比較で判定しない。
- ゼロDATAの確認はできたが、異常スロットが信号起因か取得起因か未確定。サイン波試験・音響合格は未実施。
