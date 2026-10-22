"""Build a normalized SQLite prototype from the generated static JSON corpus."""
import json
import gzip
import os
import shutil
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public/data'
DEFAULT_OUTPUT = DATA / 'reader-prototype.sqlite'
DEFAULT_COMPRESSED_OUTPUT = DATA / 'reader-prototype.sqlite.gz'


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def create_schema(db):
    db.executescript('''
        PRAGMA foreign_keys = ON;
        PRAGMA user_version = 1;
        CREATE TABLE witness (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            language TEXT NOT NULL,
            source TEXT NOT NULL
        ) WITHOUT ROWID;
        CREATE TABLE book (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            position INTEGER NOT NULL UNIQUE
        ) WITHOUT ROWID;
        CREATE TABLE chapter (
            book_id TEXT NOT NULL REFERENCES book(id),
            number INTEGER NOT NULL,
            PRIMARY KEY (book_id, number)
        ) WITHOUT ROWID;
        CREATE TABLE verse (
            ref TEXT PRIMARY KEY,
            book_id TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            number INTEGER NOT NULL,
            alignment TEXT NOT NULL,
            FOREIGN KEY (book_id, chapter) REFERENCES chapter(book_id, number),
            UNIQUE (book_id, chapter, number)
        ) WITHOUT ROWID;
        CREATE TABLE token (
            id INTEGER PRIMARY KEY,
            ref TEXT NOT NULL REFERENCES verse(ref),
            witness_id TEXT NOT NULL REFERENCES witness(id),
            position INTEGER NOT NULL,
            source_id TEXT NOT NULL,
            text TEXT NOT NULL,
            after_text TEXT NOT NULL,
            morphology_code TEXT,
            variant TEXT,
            UNIQUE (ref, witness_id, position)
        );
        CREATE TABLE lemma (
            id TEXT PRIMARY KEY,
            headword TEXT,
            gloss TEXT,
            transliteration TEXT,
            root TEXT,
            root_id TEXT,
            bdb_id TEXT,
            source TEXT,
            license TEXT
        ) WITHOUT ROWID;
        CREATE TABLE token_component (
            token_id INTEGER NOT NULL REFERENCES token(id),
            position INTEGER NOT NULL,
            lemma_id TEXT NOT NULL REFERENCES lemma(id),
            text TEXT,
            PRIMARY KEY (token_id, position)
        ) WITHOUT ROWID;
        CREATE TABLE morphology_feature (
            token_id INTEGER NOT NULL,
            component_position INTEGER NOT NULL,
            name TEXT NOT NULL,
            value TEXT NOT NULL,
            PRIMARY KEY (token_id, component_position, name),
            FOREIGN KEY (token_id, component_position)
                REFERENCES token_component(token_id, position)
        ) WITHOUT ROWID;
        CREATE TABLE bdb_entry (
            id TEXT PRIMARY KEY,
            body TEXT NOT NULL,
            status TEXT,
            source TEXT,
            license TEXT
        ) WITHOUT ROWID;
        CREATE TABLE metadata (
            name TEXT PRIMARY KEY,
            value_json TEXT NOT NULL
        ) WITHOUT ROWID;
        CREATE INDEX token_witness_ref_position
            ON token(witness_id, ref, position);
        CREATE INDEX token_component_lemma
            ON token_component(lemma_id, token_id);
        CREATE INDEX lemma_root
            ON lemma(root_id);
    ''')


def build(output=DEFAULT_OUTPUT):
    catalog = json.loads((DATA / 'catalog.json').read_text())
    lexicon = json.loads((DATA / 'lexical/index.json').read_text())
    alignment = json.loads((DATA / 'alignment-report.json').read_text())
    sources_lock = json.loads((DATA / 'sources.lock.json').read_text())

    output = Path(output)
    compressed_output = output.with_suffix(output.suffix + '.gz')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + '.tmp')
    compressed_temporary = compressed_output.with_name(compressed_output.name + '.tmp')
    temporary.unlink(missing_ok=True)
    compressed_temporary.unlink(missing_ok=True)
    counts = {'books': len(catalog['books']), 'chapters': 0, 'verses': 0,
              'tokens': 0, 'components': 0, 'lemmas': len(lexicon), 'bdb_entries': 0}

    try:
        db = sqlite3.connect(temporary)
        db.execute('PRAGMA journal_mode = OFF')
        db.execute('PRAGMA synchronous = OFF')
        create_schema(db)
        with db:
            db.executemany('INSERT INTO witness VALUES (?, ?, ?, ?)', [
                ('he', 'Hebrew', 'he', 'Open Scriptures MorphHB / WLC'),
                ('syr', 'Syriac', 'syr', 'ETCBC Peshitta'),
            ])
            for lemma_id, entry in lexicon.items():
                db.execute('INSERT INTO lemma VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', (
                    lemma_id, entry.get('headword'), entry.get('gloss'),
                    entry.get('transliteration'), entry.get('root'), entry.get('rootId'),
                    entry.get('bdb'), entry.get('source'), entry.get('license')))
            for position, book in enumerate(catalog['books']):
                db.execute('INSERT INTO book VALUES (?, ?, ?, ?)',
                           (book['id'], book['name'], book['slug'], position))
                for chapter in book['chapters']:
                    db.execute('INSERT INTO chapter VALUES (?, ?)', (book['id'], int(chapter)))
                    counts['chapters'] += 1
                    path = DATA / 'text' / book['slug'] / f'{chapter}.json'
                    rows = json.loads(path.read_text())
                    for row in rows:
                        db.execute('INSERT INTO verse VALUES (?, ?, ?, ?, ?)', (
                            row['id'], book['id'], int(chapter), row['verse'], row['alignment']))
                        counts['verses'] += 1
                        for witness_id in ('he', 'syr'):
                            for position, word in enumerate(row[witness_id]):
                                cursor = db.execute('''INSERT INTO token
                                    (ref, witness_id, position, source_id, text, after_text,
                                     morphology_code, variant)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', (
                                    row['id'], witness_id, position, word['id'], word['text'],
                                    word.get('after', ''), word.get('morphology'), word.get('variant')))
                                token_id = cursor.lastrowid
                                counts['tokens'] += 1
                                lemmas = word.get('lemmas', [])
                                parts = word.get('parts', [])
                                for component_position, lemma_id in enumerate(lemmas):
                                    part = parts[component_position] if component_position < len(parts) else {}
                                    db.execute('INSERT INTO token_component VALUES (?, ?, ?, ?)', (
                                        token_id, component_position, lemma_id, part.get('text')))
                                    counts['components'] += 1
                                    for name, value in part.get('morphology', {}).items():
                                        db.execute('INSERT INTO morphology_feature VALUES (?, ?, ?, ?)', (
                                            token_id, component_position, name,
                                            value if isinstance(value, str) else encode(value)))

            for shard in sorted((DATA / 'lexical/bdb').glob('*.json')):
                entries = json.loads(shard.read_text())
                for entry_id, entry in entries.items():
                    db.execute('INSERT INTO bdb_entry VALUES (?, ?, ?, ?, ?)', (
                        entry_id, entry['body'], entry.get('status'), entry.get('source'),
                        entry.get('license')))
                    counts['bdb_entries'] += 1

            metadata = {
                'schemaVersion': 1,
                'scope': catalog.get('scope'),
                'provenance': catalog.get('provenance'),
                'alignmentReport': alignment,
                'sourcesLock': sources_lock,
                'occurrenceScopes': {
                    book['id']: json.loads((DATA / 'lexical/occurrences' / f"{book['id']}.json").read_text()).get('scope')
                    for book in catalog['books']
                },
            }
            db.executemany('INSERT INTO metadata VALUES (?, ?)',
                           [(name, encode(value)) for name, value in metadata.items()])
        db.execute('VACUUM')
        db.close()
        with output.open('rb') as source, compressed_temporary.open('wb') as target:
            with gzip.GzipFile(filename='', fileobj=target, mode='wb', compresslevel=9, mtime=0) as compressed:
                shutil.copyfileobj(source, compressed)
        os.replace(temporary, output)
        os.replace(compressed_temporary, compressed_output)
    except Exception:
        temporary.unlink(missing_ok=True)
        compressed_temporary.unlink(missing_ok=True)
        raise

    print(f"Built {output.relative_to(ROOT) if output.is_relative_to(ROOT) else output}: "
          f"{counts['books']} books, {counts['chapters']} chapters, {counts['verses']} verses, "
          f"{counts['tokens']} tokens, {counts['components']} components, "
          f"{counts['lemmas']} lemmas, {counts['bdb_entries']} BDB entries "
          f"({output.stat().st_size / 1024 / 1024:.1f} MiB raw, "
          f"{compressed_output.stat().st_size / 1024 / 1024:.1f} MiB gzip)")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    build(parser.parse_args().output)
