"""Import a real employee CSV using the application's privileged singleton client."""
import argparse
import csv
import io
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database import supabase
from app.utils.name_normalizer import normalize_name


def import_employees(csv_content: str, client=None):
    client = client if client is not None else supabase
    reader = csv.DictReader(io.StringIO(csv_content.lstrip("\ufeff")))
    required = {"employee_name", "employee_code", "team"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError("CSV must include employee_name,employee_code,team")
    teams = client.from_("teams").select("id,name,slug").execute().data
    lookup = {normalize_name(value): team["id"] for team in teams for value in (team["name"], team["slug"])}
    employees = client.from_("employees").select("employee_code,normalized_name").execute().data
    codes = {e["employee_code"] for e in employees if e.get("employee_code")}
    names = {e["normalized_name"] for e in employees}
    successful, errors = 0, []
    for row in reader:
        number = reader.line_num
        try:
            if None in row or any(row.get(key) is None for key in required):
                raise ValueError("Malformed CSV row")
            name = row["employee_name"].strip()
            code = row["employee_code"].strip() or None
            normalized = normalize_name(name)
            if not normalized or len(name) > 100:
                raise ValueError("Invalid employee name")
            if code and len(code) > 50:
                raise ValueError("Employee code is too long")
            team_id = lookup.get(normalize_name(row["team"]))
            if not team_id:
                raise ValueError("Unknown team")
            if code and code in codes:
                raise ValueError("Duplicate employee code")
            if not code and normalized in names:
                raise ValueError("Duplicate employee name requires an employee code")
            client.from_("employees").insert({
                "name": name, "normalized_name": normalized, "employee_code": code,
                "team_id": team_id, "is_active": True,
            }).execute()
            successful += 1
            if code:
                codes.add(code)
            names.add(normalized)
        except ValueError as exc:
            errors.append(f"Row {number} - {exc}")
        except Exception as exc:
            reason = "Duplicate employee code" if str(getattr(exc, "code", "")) == "23505" else "Database insert failed"
            errors.append(f"Row {number} - {reason}")
    return {"successful": successful, "failed": len(errors), "errors": errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path)
    args = parser.parse_args()
    try:
        result = import_employees(args.csv_file.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Import failed: {exc}\n")
    except Exception:
        parser.exit(1, "Import failed: database unavailable; verify schema and backend environment.\n")
    print(f"Import complete\n\nSuccessful: {result['successful']}\nFailed: {result['failed']}")
    if result["errors"]:
        print("\nErrors:\n" + "\n".join(result["errors"]))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
