"""Regenerate the optional SQL Editor bundle from the canonical source files."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
names = ("schema.sql", "constraints.sql", "indexes.sql", "rls.sql", "seed.sql")
parts = ["-- Generated from the five organized source files. Paste this whole file into Supabase SQL Editor.\n-- Rebuild with: python scripts/build_setup.py\nbegin;\n\n"]
for name in names:
    parts.append("-- backend/sql/" + name + "\n" + (root / "sql" / name).read_text(encoding="utf-8") + "\n")
parts.append("\ncommit;\n")
(root / "sql" / "setup.sql").write_text("".join(parts), encoding="utf-8")
print("Updated sql/setup.sql")
