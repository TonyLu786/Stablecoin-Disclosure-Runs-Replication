# Reproducibility

## Environment

The project is tested with Python 3.10. Required Python packages are listed in `requirements.txt`.

```powershell
python -m pip install -r requirements.txt
python scripts\check_public_release.py
python scripts\run_public_replication.py --mode smoke
```

## Main Replication Paths

- `scripts/run_public_replication.py --mode smoke`: verifies key files and reports row counts.
- `scripts/run_public_replication.py --mode analysis`: reruns baseline, event-window, robustness, and multi-issuer diagnostic scripts.
- `scripts/run_public_replication.py --mode all`: runs the smoke and analysis stages.

## Determinism

The included public package defaults to offline reproduction from derived CSV files already included in the repository. Network-based source collection is intentionally not part of the public smoke path.
