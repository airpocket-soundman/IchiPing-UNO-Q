# 回路図の可読性レビュー（2026-09-08）

対象は既存の `uno_q_shield` / `analog_shield` に関連付けられた回路図。
新しい基板や回路図の複製は作成していない。PCB の配置・配線はこの作業では変更していない。

## 変更内容

- Audio: J14/J15を左側、マイク、アンプ電源・ミュート、ゲイン設定を機能別に配置。
- Audio: R_SD、JP_MUTE、J_AMP_PWR、C1/C2 の回路、マイクのLR設定、アンプのGAIN設定を実線で接続。
- UNO: Arduinoヘッダを左側、電源を上中央、状態入力を右側、ディスプレイ端子を中央下に配置。
- UNO: 外部5V入力、サーボ電源出力、3個のコンデンサを実線で接続。
- 部品番号、値、ネット名の重複表示を整理し、文字と配線の重なりをPDFで確認して調整。

## 接続検証

両回路図について、変更前後の製造用ネットリストを比較した。
部品のUnique ID、Designator、Device、Footprint、Nameと、全ピンのネット名が一致。
この検証は回路の電気設計そのものの再承認や、新たな基板DRCの実行を意味しない。

## 比較PDF

- [Audio変更前](../output/pdf/audio-schematic-before.pdf)
- [Audio変更後](../output/pdf/audio-schematic-after.pdf)
- [UNO変更前](../output/pdf/uno-schematic-before.pdf)
- [UNO変更後](../output/pdf/uno-schematic-after.pdf)

変更前はユーザーが保存したEasyEDAのPDFをそのまま保管。
変更後は、EasyEDAの通常PDF出力に削除済み文字が残留する現象を確認したため、
現在表示されている回路図を200%表示で分割キャプチャし、座標を合わせてA4 PDFへ配置した。
図面を別途描き直したものではない。背景のグリッドはエディタ表示であり、回路配線ではない。
前後ともページ寸法は848.88 × 600.48 pt、図面座標の縮尺は0.72 pt/unit。

通常のPDFエクスポート側の残留表示問題は未解消。提出用の比較には上記変更後PDFを使用する。
