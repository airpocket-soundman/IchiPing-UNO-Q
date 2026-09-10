#!/usr/bin/env python3
"""Render recorded scope samples as SVG; no hardware access or data smoothing."""
import argparse
import csv
import json
from html import escape
from pathlib import Path


def render(source, output, zoom_start=2, zoom_end=7):
    with source.open(encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    times = [float(row['time_s']) * 1e6 for row in rows]
    report = json.loads(source.with_name('report.json').read_text(encoding='utf-8'))
    wiring = report.get('wiring', {'CH1': 'GPIO98', 'CH2': 'GPIO99'})
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" viewBox="0 0 1200 760">',
             '<rect width="1200" height="760" fill="#111827"/>',
             '<g font-family="Segoe UI, sans-serif" fill="#e5e7eb">',
             '<text x="65" y="36" font-size="23">UNO Q — recorded unloaded I2S / 実測保存波形</text>',
             f'<text x="65" y="64" font-size="15">{escape(source.parent.name)} | CH1={escape(wiring["CH1"])} / CH2={escape(wiring["CH2"])} | probes x10, DC</text>',
             '<text x="65" y="89" font-size="15" fill="#fbbf24">API voltage scale UNVERIFIED / 電圧値は未検証。音声・理想波形ではありません。</text>']
    for top, xmin, xmax, title in [(140, min(times), max(times), 'Full capture / 全取得区間'),
                                  (450, zoom_start, zoom_end, 'Detail / 拡大 (no smoothing)')]:
        left, width, height, ymin, ymax = 85, 1060, 205, -.2, 3.2
        parts.append(f'<text x="65" y="{top-18}" font-size="18">{title}</text>')
        for tick in range(6):
            x = left + width*tick/5
            t = xmin+(xmax-xmin)*tick/5
            parts.append(f'<path d="M{x},{top}v{height}" stroke="#374151"/>')
            parts.append(f'<text x="{x}" y="{top+height+25}" text-anchor="middle" font-size="13">{t:.1f} us</text>')
        for value in [0, 1, 2, 3]:
            y = top+height-(value-ymin)/(ymax-ymin)*height
            parts.append(f'<path d="M{left},{y}h{width}" stroke="#374151"/>')
            parts.append(f'<text x="{left-12}" y="{y+4}" text-anchor="end" font-size="13">{value} V*</text>')
        for key, color in [('CH1_v', '#fb7185'), ('CH2_v', '#facc15')]:
            points = ' '.join(f'{left+(t-xmin)/(xmax-xmin)*width:.2f},{top+height-(float(r[key])-ymin)/(ymax-ymin)*height:.2f}'
                              for t, r in zip(times, rows) if xmin <= t <= xmax)
            parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="1.2"/>')
    for ch, x, color in [('CH1', 85, '#fb7185'), ('CH2', 550, '#facc15')]:
        freq = report['channels'][ch]['frequency_hz_from_edges']
        label = f'{freq/1e6:.6f} MHz' if freq else 'frequency not identified'
        if report['channels'][ch].get('bclk_undersampled_do_not_interpret'):
            label = 'UNDERSAMPLED — not valid BCLK waveform'
        parts.append(f'<text x="{x}" y="725" fill="{color}" font-size="17">{ch}: {label}</text>')
    parts.append('</g></svg>')
    with output.open('x', encoding='utf-8') as stream:
        stream.write('\n'.join(parts))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--zoom-start', type=float, default=2)
    parser.add_argument('--zoom-end', type=float, default=7)
    args = parser.parse_args()
    if args.zoom_end <= args.zoom_start:
        parser.error('zoom-end must exceed zoom-start')
    render(args.source, args.output, args.zoom_start, args.zoom_end)
