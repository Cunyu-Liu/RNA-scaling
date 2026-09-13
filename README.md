# rna-sc — RNA-LM transfer-learning mechanistic study (controlled family)

Controlled MLM encoder family (RNA-Sc-1M/10M/30M/100M) pretrained on the
frozen TokBench release22 80/80 split. Spec: RNA_LM_迁移学习机理研究 SPEC
(S0-S12). Code here; runs/artifacts in /mnt/cunyuliu/rna-sc.

## Layout
- rna_sc/model.py     — ALiBi MLM encoder (S1 recipe)
- rna_sc/config.py    — frozen run configs
- rna_sc/data.py      — split-streaming MLM batching (nt exposure)
- rna_sc/train.py     — training runner (manifest discipline)
- rna_sc/smoke.py     — acceptance A6 smoke tests
- rna_sc/ledger.py    — run registry (Z5)
- rna_sc/status.py    — training status monitor

## Env
Server: A100 cohort, conda env `toktokenbench` (torch 2.6.0+cu124).

## Quickstart
```bash
bash launch_wave1.sh                        # multi-GPU wave
python -m rna_sc.smoke --device 6           # A6 acceptance
python -m rna_sc.status                     # progress report
python -m rna_sc.ledger list
```

## Discipline (frozen)
- GPU-only training; cpu_fallback_count must stay 0.
- exposure in nt; budget 2.0B valid nt per model; ckpt every 100M nt.
- validation on `validation` split only; family_test/test untouched.
- every run in ledger.jsonl; no duplicate launches.
