"""Write deterministic gzip mirrors of the corpus and lexical JSON exports."""
import gzip
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public/data'
TREES = [DATA / 'text', DATA / 'lexical']


def main():
    count = 0
    raw_bytes = compressed_bytes = 0
    for tree in TREES:
        for source in sorted(tree.rglob('*.json')):
            target = source.with_name(source.name + '.gz')
            temporary = target.with_name(target.name + '.tmp')
            with source.open('rb') as original, temporary.open('wb') as output:
                with gzip.GzipFile(filename='', fileobj=output, mode='wb', compresslevel=9, mtime=0) as compressed:
                    shutil.copyfileobj(original, compressed)
            temporary.replace(target)
            count += 1
            raw_bytes += source.stat().st_size
            compressed_bytes += target.stat().st_size
    print(f'Compressed {count} JSON files: {raw_bytes / 1024 / 1024:.1f} MiB to '
          f'{compressed_bytes / 1024 / 1024:.1f} MiB')


if __name__ == '__main__':
    main()
