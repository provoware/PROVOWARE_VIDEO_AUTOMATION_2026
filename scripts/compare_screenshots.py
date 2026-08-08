#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from videobatch_fast.visual_regression import compare_visual, create_difference_image


def main() -> int:
    parser = argparse.ArgumentParser(description='Zwei UI-Screenshots robust und viewport-normalisiert vergleichen.')
    parser.add_argument('baseline', type=Path, help='SOLL-/Referenzbild')
    parser.add_argument('actual', type=Path, help='IST-/aktuelles Bild')
    parser.add_argument('--id', default='manual-comparison')
    parser.add_argument('--output', type=Path, default=Path('diagnostics/manual_visual_compare'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    result = compare_visual(args.id, args.baseline, args.actual)
    diff = args.output / f'{args.id}_diff.png'
    if args.baseline.is_file() and args.actual.is_file():
        create_difference_image(args.baseline, args.actual, diff)
    payload = asdict(result)
    payload['difference_image'] = str(diff) if diff.is_file() else ''
    json_path = args.output / f'{args.id}.json'
    txt_path = args.output / f'{args.id}.txt'
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    txt_path.write_text(
        '\n'.join([
            f'Bildvergleich: {args.id}',
            f'Status: {"BESTANDEN" if result.passed else "ABWEICHUNG"}',
            f'SOLL: {result.baseline} · {result.baseline_size[0]}×{result.baseline_size[1]}',
            f'IST: {result.actual} · {result.actual_size[0]}×{result.actual_size[1]}',
            f'Mittlere Differenz: {result.mean_difference:.4f}',
            f'RMSE: {result.rmse:.4f}',
            f'Geänderte Fläche: {result.changed_pixel_ratio:.2%}',
            f'Kantendifferenz: {result.edge_difference:.4f}',
            f'dHash-Abstand: {result.dhash_distance}',
            f'Seitenverhältnis-Abweichung: {result.aspect_ratio_delta:.2%}',
            f'Differenzbereich relativ: {result.difference_bbox}',
            f'Bewertung: {result.message}',
        ]) + '\n',
        encoding='utf-8',
    )
    print(txt_path)
    print(json_path)
    if diff.is_file():
        print(diff)
    return 0 if result.passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
