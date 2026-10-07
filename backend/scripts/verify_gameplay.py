"""Read-only migration checks. Never prints content, employee data or credentials."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database import supabase


def main():
    failed = False
    for table in ('jumble_content', 'jumble_runtime'):
        try:
            supabase.from_(table).select('game_id').limit(1).execute()
            print(f'{table}: available')
        except Exception:
            print(f'{table}: unavailable; apply sql/gameplay.sql and check the backend connection')
            failed = True
    try:
        buckets = supabase.storage.list_buckets()
        bucket = next((b for b in buckets if b.id == 'jumble-grid'), None)
        if not bucket or bucket.public:
            print('jumble-grid: missing or not private; review sql/gameplay.sql')
            failed = True
        else:
            print('jumble-grid: private bucket available')
    except Exception:
        print('jumble-grid: bucket check failed')
        failed = True
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())
