"""T2.1.2 corpus 3-point curve (red-team fix A): 10M x {c1Mcs, c5Mcs, full}.

All three arms: same model (RNA-Sc-10M, seed 17), same 2.0B-nt budget,
same probe protocol. The ONLY differences are corpus size/composition:
  - c1Mcs : 1M seqs / 190,917 clusters (~0.9B nt unique, ~2.2 epochs)
  - c5Mcs : 5M seqs / 975,339 clusters (~2.4B nt unique, ~0.83 epochs)
  - full  : 14.13M seqs / 3.02M clusters (~14.1B nt unique, 0.14 epochs)

Epoch-coverage differences are EXPLICIT (axis annotation), never claimed
as matched. Composition shift documented in corpus_diversity.md.
Output: figs/fig_corpus3.png/.pdf + evidence/corpus3.json
"""
from __future__ import annotations

import json
import os
from collections import defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

EVAL = '/mnt/cunyuliu/rna-sc/eval/probe_results.jsonl'
OUT = '/mnt/cunyuliu/rna-sc/evidence/corpus3.json'
FIG = '/mnt/cunyuliu/rna-sc/figs/fig_corpus3'

ARMS = [
    ('c1Mcs', 'RNA-Sc-10M_s17_c1Mcs', 0.90, 2.22, '#DD8452'),
    ('c5Mcs', 'RNA-Sc-10M_s17_c5Mcs', 2.40, 0.83, '#4C72B0'),
    ('full',  'RNA-Sc-10M_s17',       14.13, 0.14, '#55A868'),
]


def main():
    rows = {a: {} for a, _, _, _, _ in ARMS}
    for line in open(EVAL):
        d = json.loads(line)
        if d.get('n_train', 0) < 20000:
            continue
        for a, run, _, _, _ in ARMS:
            if d['run'] == run and (a != 'full' or d.get('ckpt_nt', 0) >= 1_900_000_000):
                rows[a][d['layer']] = d['f1_macro']
    res = {}
    for a, run, nt_uniq, epochs, color in ARMS:
        if not rows[a]:
            print('[corpus3]', a, 'not probed yet')
            continue
        L = max(rows[a]) + 1
        best = max(rows[a], key=rows[a].get)
        bands = {'early': [], 'middle': [], 'late': []}
        for li, f in rows[a].items():
            r = li / (L - 1)
            bands['early' if r <= 0.33 else ('middle' if r <= 0.66 else 'late')].append(f)
        res[a] = {
            'nt_unique_B': nt_uniq, 'epochs': epochs,
            'best_layer': best, 'best_rel': round(best / (L - 1), 3),
            'best_f1': round(rows[a][best], 4),
            'band_early': round(sum(bands['early']) / max(1, len(bands['early'])), 4),
            'band_middle': round(sum(bands['middle']) / max(1, len(bands['middle'])), 4),
            'band_late': round(sum(bands['late']) / max(1, len(bands['late'])), 4),
        }
    if len(res) < 3:
        print('[corpus3] incomplete:', list(res))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, 'w'), indent=2)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    xs = [res[a]['nt_unique_B'] for a in res]
    ys = [res[a]['best_f1'] for a in res]
    es = [res[a]['epochs'] for a in res]
    ax = axes[0]
    ax.plot(xs, ys, marker='o', ms=8, color='#444')
    for a in res:
        ax.annotate('%s\n%.2f ep' % (a, res[a]['epochs']),
                    (res[a]['nt_unique_B'], res[a]['best_f1']),
                    textcoords='offset points', xytext=(8, 6), fontsize=8)
    ax.set_xscale('log')
    ax.set_xlabel('unique corpus nt (B, log)')
    ax.set_ylabel('best-layer macro-F1')
    ax.set_title('Corpus 3-point (10M model, 2.0B nt budget)')
    ax = axes[1]
    rels = [res[a]['best_rel'] for a in res]
    ax.plot(xs, rels, marker='*', ms=12, color='#8172B3')
    for a in res:
        ax.annotate(a, (res[a]['nt_unique_B'], res[a]['best_rel']),
                    textcoords='offset points', xytext=(6, 6), fontsize=9)
    ax.set_xscale('log')
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel('unique corpus nt (B, log)')
    ax.set_ylabel('best-layer rel_depth')
    ax.set_title('best-layer position vs corpus size')
    fig.tight_layout()
    fig.savefig(FIG + '.png', dpi=180)
    fig.savefig(FIG + '.pdf')
    print('[corpus3] saved figs/fig_corpus3.png/.pdf; arms:', list(res))
    for a in res:
        print('  %s: F1=%.4f best rel=%.3f' % (a, res[a]['best_f1'], res[a]['best_rel']))


if __name__ == '__main__':
    main()
