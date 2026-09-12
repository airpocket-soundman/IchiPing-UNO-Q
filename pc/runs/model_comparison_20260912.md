# UNO Q model comparison (2026-09-12)

| model | training data | augmentation | ambient | start | morning (09:00 stable) | evening (19:35 -2.15%) | survey (20:44 -1.05%) | crowd (21:28 crowd -0.80%) | mean 32 |
|---|---|---|---|---|---|---|---|---|---|
| Original XL | original v21-v25 (FRDM) | recipe, CB5 | original passive | scratch | 20.8 / 59.4 | 35.9 / 68.8 | 9.1 / 49.7 | 11.6 / 50.0 | 19.3 |
| UNO Q provisional | original 160 WAVs | feature-aug | none | scratch | 12.5 / 56.2 | 37.2 / 77.8 | 18.8 / 59.4 | 10.3 / 50.9 | 19.7 |
| A | UNO Q s1 | feature-aug | none | scratch | 72.9 / 100.0 | 26.2 / 50.6 | 21.9 / 71.9 | 30.3 / 83.4 | 37.8 |
| B | UNO Q s2 | feature-aug | none | scratch | 53.1 / 100.0 | 12.5 / 26.2 | 19.7 / 66.6 | 20.9 / 67.2 | 26.6 |
| C | s1 + original | feature-aug | none | scratch | 77.1 / 100.0 | 41.9 / 81.2 | 33.4 / 66.2 | 39.1 / 81.9 | 47.9 |
| D | s1-2 | feature-aug | none | scratch | 74.0 / 100.0 | 12.5 / 26.6 | 31.2 / 75.0 | 36.2 / 79.7 | 38.5 |
| E | s1-2 + original | feature-aug | none | scratch | 80.2 / 100.0 | 40.0 / 74.4 | 48.1 / 90.6 | 52.5 / 88.4 | 55.2 |
| F | s1-2 | recipe, CB2 | none | scratch | 84.4 / 100.0 | 23.1 / 41.9 | 50.0 / 80.6 | 47.8 / 86.9 | 51.3 |
| G | s1-2 | recipe, CB2 | original passive | scratch | 84.4 / 100.0 | 17.8 / 42.5 | 34.4 / 69.1 | 40.0 / 79.1 | 44.1 |
| H | s1-2 + original | recipe, CB7 | none | scratch | 79.2 / 100.0 | 45.6 / 89.7 | 51.2 / 92.5 | 49.1 / 91.6 | 56.3 |
| J | s1-3 | recipe, CB3 | none | scratch | 84.4 / 100.0 | 32.8 / 66.6 | 70.3 / 100.0 | 58.4 / 97.2 | 61.5 |
| K | s1-4 | recipe, CB4 | none | scratch | 86.5 / 100.0 | 43.1 / 84.1 | 69.1 / 99.7 | 76.9 / 100.0 | 68.9 |
| N | s1-5 | recipe, CB5 | UNO Q room | scratch | 88.5 / 100.0 | 33.1 / 74.4 | 60.9 / 100.0 | 78.4 / 99.7 | 65.3 |
| M | s1-6 | recipe, CB6 | UNO Q room | scratch | 86.5 / 100.0 | 47.5 / 68.4 | 68.4 / 100.0 | 77.8 / 100.0 | 70.1 |
| P | s1-8 (s7/8 at 4.8%FS, x2.72) | recipe, CB8 | UNO Q room | scratch | 85.4 / 100.0 | 64.7 / 94.1 | 66.6 / 98.4 | 74.1 / 100.0 | 72.7 |
| Q | s1-5 + s7 (4.8%FS) | recipe, CB6 | UNO Q room | scratch | 88.5 / 100.0 | 43.1 / 89.4 | 61.3 / 99.4 | 84.1 / 100.0 | 69.2 |
| s5 only | s5 | recipe, CB1 | UNO Q room | scratch | 57.3 / 94.8 | 10.0 / 36.6 | 28.7 / 71.6 | 25.0 / 78.1 | 30.3 |
| s7 loud only | s7 (4.8%FS) | recipe, CB1 | UNO Q room | scratch | 25.0 / 67.7 | 33.1 / 80.0 | 38.4 / 85.3 | 32.2 / 72.2 | 32.2 |
| K+ambient | s1-4 | recipe, CB4 | UNO Q room + crowd | K, 20 ep | 88.5 / 100.0 | 45.0 / 80.6 | 70.3 / 99.4 | 77.5 / 100.0 | 70.3 |
| W | s1-4 | recipe, CB4, warp +-3% | UNO Q room + crowd | K+ambient, 20 ep | 89.6 / 100.0 | 56.9 / 93.8 | 82.8 / 100.0 | 80.9 / 100.0 | 77.6 |
| W5 | s1-4 | recipe, CB4, warp +-5% | UNO Q room + crowd | K+ambient, 20 ep | 89.6 / 100.0 | 59.4 / 95.0 | 78.4 / 100.0 | 81.6 / 100.0 | 77.2 |
| MW | s1-6 | recipe, CB6, warp +-3% | UNO Q room + crowd | M, 20 ep | 89.6 / 100.0 | 65.6 / 96.9 | 80.6 / 100.0 | 84.4 / 100.0 | 80.1 |
| PW | s1-8 | recipe, CB8, warp +-3% | UNO Q room + crowd | P, 20 ep | 91.7 / 100.0 | 81.9 / 100.0 | 74.7 / 100.0 | 81.9 / 100.0 | 82.5 |
Values: 32-state / 14-class (observable) accuracy in %. recipe = --aug-strong --spike-fix --feature-aug; CBn = cross-baseline over n sessions; warp = --freq-warp (temperature). Evaluation sets are never used for training.
