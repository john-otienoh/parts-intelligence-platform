# Utility Scripts

This directory contains maintenance and administrative scripts for AutoIntel.

## Contents

- `seed_database.py` – Populates the database with sample marketplace data for development.
- `backup_db.sh` – Performs a PostgreSQL dump to a specified directory.
- `restore_db.sh` – Restores from a backup file.
- `generate_erd.py` – Generates an Entity‑Relationship Diagram of the warehouse schema.
- `cleanup_logs.py` – Archives or deletes log files older than N days.

## Usage

```bash
python scripts/seed_database.py --env development
bash scripts/backup_db.sh /backups/autointel_$(date +%F).sql
python scripts/generate_erd.py > docs/erd.png
```

Always run these scripts from the repository root and ensure the virtual environment is active.