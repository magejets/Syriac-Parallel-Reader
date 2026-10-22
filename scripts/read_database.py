"""Run a read-only SQL query against the gzipped SQLite prototype."""
import argparse
import gzip
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database', type=Path, help='Path to reader-prototype.sqlite.gz')
    parser.add_argument('sql', nargs='?', default="SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
                        help='Read-only SQL query (defaults to listing tables)')
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix='reader-db-') as temp_dir:
        decoded = Path(temp_dir) / 'reader.sqlite'
        with gzip.open(args.database, 'rb') as source, decoded.open('wb') as target:
            shutil.copyfileobj(source, target)
        db = sqlite3.connect(f'file:{decoded}?mode=ro', uri=True)
        db.row_factory = sqlite3.Row
        cursor = db.execute(args.sql)
        rows = [dict(row) for row in cursor.fetchall()]
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        db.close()


if __name__ == '__main__':
    main()
