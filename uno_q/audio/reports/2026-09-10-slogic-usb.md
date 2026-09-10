# SLogic16U3 USB認識調査 — 2026-09-10

状態: 通常モードはWindows PnPに未列挙、DFUモードのみ認識実績あり。
このUSB認識調査中は波形取得・UNO Q信号出力・ファーム更新・ハブリセット・ドライバー変更を行っていない（先行するOWON測定は別レポート）。

- PC: kuma、Windows。ユーザーはハブ経由。PC直結は手が届かず不可。
- ユーザー確認済み配線: 白D0=98/BCLK、白D1=99/WS、白D2=101/DIN、黒=GND。
  アンプ・マイク未接続。オシロCH1=99/CH2=101。
- 通常モードで青のみ→MODE後に水色/紫点滅、DFUを検出。
  VID/PID 359f:30f1、Microsoft WinUSB 10.0.26100.8972、ProblemCode=0。
- MODEで通常へ戻すと青、PnPからDFU消失、通常機器は現れない。
  後にユーザーは水色点灯を報告したが、全PnP差分でも通常機器未確認。
  LED報告とOS列挙が食い違い、原因未特定。
- DFUの履歴は親ハブ05e3:0608 / USBROOT(0)#USB(9)#USB(2)と、
  045b:0209 / USBROOT(0)#USB(8)#USB(3)の2経路。
  DFUはUSB2なので、これだけでは通常モードのUSB3経路の成否を判定しない。
- USBXHCI Operationalは有効だが0件、直近Kernel-PnP System検索にも原因を示す記録なし。
  setupapi.dev.logに359f/SLogic一致なし。ドライバー障害がないと保証するものではない。
- pnputil /scan-devicesはAccess is denied。管理者の再スキャンは未実施。

ソフト: SLogic-1.1.0-windows-x86_64.zip、公式一覧で79.97MB、2026-09-09更新。
公式ダウンロード画面のCAPTCHAをユーザーが完了し、ダウンロード・展開済み。
配置: C:/Users/yamas/Downloads/windows-x86_64-ucrt。
PulseView / SLogicView / sigrok-cliの3つのEXEは同梱SHA256SUMSと一致。
同梱hashとの一致は取得整合性の確認であり独立した真正性保証ではない。CLIは電子署名なし。
release-1.1.0、build 2026-09-08、libsigrok revision 0c36240d8dbb2b2e06f9a9ba9d889a9be752536c。
CLI起動確認: sigrok-cli0.8.0 / libsigrok0.6.0 / libusb1.0.30。
対応driver sipeed-slogic-analyzerを確認し、同driver指定--scanを実施。検出0台。
Windows PnPでも通常SLogicは未検出。ソフト起動準備はできたが、実機測定は未成立。
GUIは未起動、取得は未開始。USBドライバーの変更なし。
プラグインZIPは取得/導入しない。今回の用途はロジアナアプリ/CLI。

## 中断時点・別PCへの引き継ぎ（2026-09-10 JST）

ユーザーがMODEを押した後、現在のハブ経路でも再度DFUの正常認識を確認した。

- 表示名: SLogic DFU、Status OK、Service WINUSB、ProblemCode 0。
- InstanceId: `USB\VID_359F&PID_30F1\6&EF384D4&0&3`。
- 親: `USB\VID_045B&PID_0209\5&30741cdd&0&8`。
- LocationPath: `PCIROOT(0)#PCI(1400)#USBROOT(0)#USB(8)#USB(3)`。
- 結論: この経路のUSB2/DFUは成立。USB3/通常モードの測定接続は未成立。
  ケーブル・ハブ・上流USB3経路・機器側USB3回路・通常ファームのどれが原因かは未特定。
  DFUの認識だけで通常側のドライバー正常やファーム破損を断定しない。
- 中断時はDFUモード。ユーザーが別PCで試す予定。ファーム書換えはしていない。

別PCではまずUNO Qの測定線から切り離したロジアナ単体を付属ケーブルでUSB3ポートに接続し、
MODEを必要に応じて通常モードへ戻して、LEDとOSの列挙名・VID/PIDを記録する。
上記ポータブル版を展開後、PowerShellで次を実行する（発音・UNO Q操作なし）。

```powershell
Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match 'VID_359F' } | Format-List Status,Class,FriendlyName,InstanceId
& .\sigrok-cli-SLogic-windows-x86_64-ucrt.exe --driver sipeed-slogic-analyzer --scan -l 4
```

通常名は公式資料でSLogic16 U3。通常モードとDFUそれぞれの認識結果、PC/OS、ポート、
ハブの有無を比較する。別PCで正常なら元PC経路を優先調査、同じ症状なら共通のケーブル／
機器側を優先調査するが、それだけで故障部位は確定しない。DFUでは波形測定できない。

認識回復後はアンプ・マイク未接続のまま98/BCLK・99/WS・101/DINの3信号同時取得へ進む。
OWONで一致した短区間だけでなく、負値・完全なサイン周期・欠落・終端を検証する。
発音経路有効化前から500msの独立リセット期限を維持し、音響合格とは区別する。

参照:
- https://wiki.sipeed.com/hardware/en/logic_analyzer/slogic16u3/Hardware_Specification.html
- https://wiki.sipeed.com/hardware/en/logic_analyzer/slogic16u3/FAQ.html
- https://dl.sipeed.com/shareURL/SLogic
