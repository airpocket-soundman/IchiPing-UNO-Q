# OWON compensation comparison — 2026-09-11 21:06 JST

User moved CH1 to the scope compensation output labeled 5 V / 1 kHz,
with compensation GND and x10 probe as instructed. CH2 not evaluated.
No UNO Q GPIO changes, audio playback, recording, or servo movement in this test.

OWON VDS1022I25070056, hardware V5.0.1 / FPGA5, API1.1.5;
base repo 0f91aa7 plus local GPIO/static capture changes.
Calibration hash unchanged:
f5987fd7ee31303933797a418b03cc03f9bfd389daca60914cfc636550e4e3e3.
DC, x10, 1.25 MS/s, 5000 points, CH1 rising 2.5 V API threshold, ONCE.

| Run (local-runs/) | API full range | CH1 p10 / p90 | p90-p10 | Edge frequency |
|---|---|---|---|---|
| compensation-20260911-range50 | 50 V | -0.20 / 2.40 V | 2.60 V | 1000 Hz |
| compensation-20260911-range20 | 20 V | 0.00 / 5.44 V | 5.44 V | 1000 Hz |
| compensation-20260911-range50-repeat | 50 V | -0.20 / 2.40 V | 2.60 V | 1000 Hz |

All three acquisitions succeeded and acknowledged stop. Frequency calculated from
sampled edges; internal frequency-meter outputs are not used.

This reproduces range-dependent disagreement independently of GPIO28. It does
not identify whether gain/configuration/probe behavior or another acquisition
issue is responsible. On 2026-09-10 the corresponding 50/20 ranges yielded
4.80/10.08 Vpp, so a fixed factor-of-two correction is not justified.
The compensation output's label is a nominal reference, not a traceable
calibration. Do not infer actual GPIO28 voltage from these readings or approve
SD wiring on that basis. Next compare official GUI versus API with matched
probe/range/coupling settings, then verify against an independent DC reference.
No flash, calibration writes, FPGA upload, or driver replacement performed.

## Follow-up: first acquisition is not settled (21:08–21:10 JST)

Official application VDS_C2 was launched using Windows app automation. After
starting acquisition, 5 V/div showed about 0.9–1 division amplitude, while
2 V/div showed about 2.3 divisions after the display updated. Both correspond
to roughly 4.6–4.8 Vpp visually, with displayed frequency 1 kHz. These are
screen estimates, not exported numerical measurements. Application then closed.

API AUTO acquisition now optionally discards initial frames (GPIO/compensation
only; never discard a short UNO Q audio event). At unchanged settings the first
frame differed from subsequent frames:

| Run | Range | First frame min/max span | Settled final p90-p10 |
|---|---|---|---|
| compensation-auto-settle50 | 50 V | 2.80 V | 4.80 V |
| compensation-auto-settle20 | 20 V | 5.76 V | 4.64 V |

Each final record is the seventh frame at 3 fetches/second; both frequencies
1000 Hz and stop acknowledged. First-frame min/max span and final percentile
span are different statistics; raw JSON retains the distinction. Subsequent
min/max spans were about 5.2–5.4 V (50 range) and 4.8–4.9 V (20 range).

This narrows the discrepancy to initial acquisition/settling behavior: the
factor-of-two mismatch disappears without changing voltage calibration. Exact
stale-buffer vs analog settling vs command sequencing cause is not yet isolated.
Previous single-first-frame GPIO28 High readings (1.1/2.2 V) must NOT be used as
its actual voltage. Reacquire GPIO after settings settle. A correct range remains
necessary for resolution, but changing range alone does not address stale or
unsettled first acquisition. This nominal compensation comparison does not
certify absolute voltage accuracy or CH2. No user wiring change is needed until
returning CH1 from compensation to GPIO28.
