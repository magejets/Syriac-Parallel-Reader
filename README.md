# Syriac Parallel Reader

A mobile-friendly Hebrew–Syriac parallel reader for **all 39 books of the Jewish canon**. Text is served as static chapter files; word-study indexes load on demand. Original interface and book icon; no proprietary Parallel Plus designs, code, or assets are included.

## Start locally

Requires Python 3.10+; Node 22+ is needed only for the test commands. The generated website is already included. No dependency installation or text download is required to read it.

```sh
cd parallel-reader
python3 -m http.server 4173 --bind 127.0.0.1 --directory public
```

Open http://127.0.0.1:4173/ in your browser. `npm run dev` runs the same server. Do not open `index.html` as a `file://` URL: module loading, JSON fetches and service workers need HTTP. HTTPS or localhost is required for service workers.

## What works

- The complete Hebrew text and ETCBC Peshitta text, paired by reference with explicit missing-source notes where reference labels do not match.
- Book/chapter/verse selectors, previous/next chapter, hash links such as `#Gen.12.3`, saved selected passage and reading preferences.
- Per-verse read checkoffs, chapter progress and a daily reading streak saved in the current browser on this device.
- Side-by-side layout, optional stacking **within each verse**, text-size adjustment, Hebrew cantillation toggle that retains vowels.
- Self-hosted Noto Serif Hebrew and Noto Sans Syriac (Estrangela); explicit `dir="rtl"`, language tags and isolated text regions.
- Tap/click/keyboard word selection; Hebrew lemma components, morphology codes, BDB glosses, lexical root groups and on-demand abridged BDB entries.
- Syriac word glosses, lexemes and morphology where the existing annotated corpus aligns exactly with the full text. Other Syriac words remain readable and are identified as unanalyzed.
- Same-lemma occurrences in both languages; supplied Hebrew root occurrences. Counts are tokens, with verse references deduplicated for navigation.
- Optional Sefaria online lookup for Hebrew: matching headwords/dictionary names and links. Bundled study works independently of Sefaria, with an internet connection.
- Manifest, 192/512 PNG icons, project-relative paths and a content-versioned service worker. The reader shell may be cached, while chapters and study data load online.

Passages, lexical indexes and occurrence lists load when connected. The service worker caches only the reader shell and fonts, not Bible text. The app remains installable, but passage reading is not available offline.

## GitHub Pages

1. Create a GitHub repository and put the **contents of this `parallel-reader` directory at the repository root**, including `.github`, `public`, scripts, tests and `sources.lock.json`. Commit the generated `public/data`, fonts and `release.js`. Do not commit `sources/` or `node_modules/`.
2. Use `main` as the branch, or update the workflow's branch filter.
3. Under Settings → Pages → Build and deployment, select **GitHub Actions**.
4. Push to `main` or run the included Deploy reader workflow. It runs the unit/data checks, regenerates the offline inventory, uploads only `public/`, and deploys it.
5. Open `https://YOUR-ACCOUNT.github.io/YOUR-REPOSITORY/`. Test a direct `#Mal.4.6` link and confirm passages load online.

The workflow deploys already committed exports; it does not silently fetch newer datasets. No backend, runtime secret, database or build-time Node bundler is needed. The navigation bar stays pinned during passage scrolling; the study panel header keeps its close control visible during internal scrolling. All asset URLs, manifest paths and service-worker scope are relative to the deployed project directory. Hash routing avoids Pages 404s. Keep source at the repository root rather than nesting it one level deeper, unless you adjust the workflow paths.

## Rebuild and verify

For a fresh checkout, fetch the pinned source revisions first:

```sh
python3 scripts/fetch_sources.py
npm run build
npm test
```

`fetch_sources.py` uses the exact repository revisions in `sources.lock.json`, preserves downloaded notices and checks SHA-256. It does not update a lock already present. Source caches remain local and ignored by Git. The exporter uses only Python's standard library: no Text-Fabric installation is needed for this specific TF feature subset.

`npm run build` exports chapters, lexical indexes, the SQLite prototype and compressed delivery files, then generates icons and a release inventory. The reader loads `.json.gz` mirrors for text and lexical data when native browser decompression is available, and falls back to plain JSON otherwise. `npm run build:database` rebuilds the SQLite prototype; `npm run build:compressed-json` rebuilds the compressed JSON mirrors. Query the compressed prototype locally with `python3 scripts/read_database.py public/data/reader-prototype.sqlite.gz "SELECT ref, count(*) FROM token GROUP BY ref LIMIT 5"`. Database and corpus files are not included in the service worker's offline cache. After any public app/data/font edit, run `python3 scripts/build_site.py` so the service worker gets a new content-derived release. The worker intentionally waits for existing tabs to close before activation. During local editing, close all tabs/PWA windows for that origin and reopen, or clear this site's service worker/cache in browser developer tools. Do not mistake an old offline release for the latest source files.

`npm test` checks navigation, lexical and occurrence pointers for all books, BDB coverage, Syriac text/annotations, Hebrew punctuation and the shell-only cache inventory.

Optional repeatable browser smoke tests:

```sh
npm ci
npx playwright install chromium
npm run test:browser
```

Run the local server first, or set `READER_URL` to a served project path. The browser test script is supplied for future regression runs; see `VERIFICATION.md` for checks actually performed in this handoff. It does not contact Sefaria.

## Architecture and repository

```text
public/
  index.html, styles.css, app.js     Reader and lexical panel
  core.js                           Pure navigation/token helpers
  providers.js                      Static BDB + optional Sefaria adapter
  manifest.webmanifest, sw.js        PWA lifecycle and scoped cache
  release.js                        Generated hash + offline asset list
  SOURCES.html                      User-visible attribution and data terms
  fonts/, icons/                    Self-hosted OFL fonts and original icons
  data/
    catalog.json                    Corpus/book/chapter/verse availability
    text/{book}/{chapter}.json       Chapter data, grouped by lowercase book name
    text/{book}/{chapter}.json.gz    Gzip mirror used by the reader
    lexical/index.json               Compact lemma metadata
    lexical/bdb/a.json …             BDB shards, loaded only when requested
    lexical/occurrences/{Book}.json  Per-book lemma/root indexes, loaded on demand
    lexical/**/*.json.gz             Gzip mirrors; readable JSON remains available
    reader-prototype.sqlite          Normalized SQLite export; JSON remains available
    reader-prototype.sqlite.gz       Gzip copy for compact transfer
    alignment-report.json
    sources.lock.json               Upstream revisions + file checksums
scripts/
  fetch_sources.py                   Reproducible source acquisition
  build_data.py                      OSIS/TF preprocessing
  build_database.py                  SQLite prototype exporter (Python stdlib)
  compress_json.py                   Gzip mirrors for corpus and lexical data
  read_database.py                   Read-only SQL access to the gzip copy
  build_site.py                      Icon + cache inventory generation
tests/                               Integrity, helper and browser checks
.github/workflows/pages.yml           Static Pages deployment
sources.lock.json                    Committed source lock
notices/                             Preserved upstream README/license files
sources/                             Ignored original downloads
```

Runtime: catalog → one chapter JSON; first word selection → lexical index and that book’s occurrence shard; expanded BDB → one static letter shard. The complete BDB is not parsed into memory at startup. Chapter, lexical and occurrence data are fetched on demand and are excluded from the shell cache. JSON fetches are memoized during the session; service-worker caches are persistent and separate from application memory. Remote Sefaria calls occur only on explicit click and are not cached. Source XML and remote definition HTML are never inserted into the live DOM.

A row has a canonical ID (`Gen.1.1`), a reference-match status and independent Hebrew/Syriac token arrays. Tokens contain displayed text, trailing punctuation/spacing, source ID, lemma IDs and morphology. Syriac tokens additionally preserve their constituent source annotations. Lexicon keys are namespaced (`he:1254a`, `syr:BRJ`) to avoid conflating unrelated lexeme systems. Roots are source-supplied Hebrew lexical etymologies, not a derived triliteral guess; occurrence groups use the actual root-entry ID so homonymous roots stay distinct. Sefaria matches are not automatically treated as exact lemma/Strong-ID equivalents.

## Data choices and license boundaries

Read the full [sources and licensing notice](public/SOURCES.html), which is also available in the app. Exact input URLs, commits and hashes are in `sources.lock.json`.

| Candidate | Use in this MVP | License/provenance decision |
| --- | --- | --- |
| [Open Scriptures morphhb](https://github.com/openscriptures/morphhb) | Hebrew WLC, all 39 books, lemmas, morphology | WLC public domain; annotation CC BY 4.0. Commercially reusable Hebrew path with attribution. |
| [Open Scriptures HebrewLexicon](https://github.com/openscriptures/HebrewLexicon) | Glosses, lexical roots, transliterations, abridged BDB | Structured edition CC BY 4.0; underlying 1906 BDB public domain. Plain-text derivative, limited to entries encountered in the corpus. |
| [ETCBC Peshitta](https://github.com/ETCBC/peshitta/tree/v0.5) | Full Peshitta Old Testament text | Plain text and Text-Fabric data are CC BY-NC; conversion code is MIT. This project uses it noncommercially and retains the source notice. |
| [ETCBC Syriac Corpus v0.9](https://github.com/ETCBC/syriac/tree/v0.9) | Optional word-level analysis | Adds lexemes, glosses and morphology only where verse and word forms match the complete text. |
| [Sefaria](https://developers.sefaria.org/reference/get-words) | Optional online metadata lookup | Excellent extension point; licenses vary by resource/version. No blanket API reuse license. Full entries require a resource-specific policy. |
| Noto fonts | Both bundled | OFL 1.1; notices preserved; no remote font dependency. |

App code is MIT. That does **not** relicense bundled third-party data. The Syriac text is used noncommercially under the ETCBC Peshitta notice. Attribution and source terms are available in the bundled sources page.

## Full-canon scope and remaining limits

The reader exports all 39 Hebrew books and the complete ETCBC Peshitta Old Testament as static chapter JSON. Navigation includes the union of both source reference sets, so every verse from both inputs is retained. A Syriac verse is displayed beside a Hebrew verse only when the source reference labels match; 207 Hebrew references have no exact Syriac label, and 78 Syriac-only references appear as Syriac-only rows. Some differences may reflect versification, so these labels are not a reviewed equivalence map. The two texts have no word-to-word alignment.

Word-level Syriac glosses, lexemes and morphology are retained only for tokens that match the existing annotated ETCBC corpus exactly. The remaining Syriac words stay readable without invented analyses. Per-book occurrence indexes load only when a word is selected. The service worker does not cache Bible chapters, lexicons or concordances.

Syriac remains consonantal in this export; no vowels, roots, or cognates are inferred. Hebrew qere is shown as a note. The optional Sefaria provider returns metadata and links; resource licenses vary, and full external dictionary entries are not bundled. The BDB transcription is abridged.

Word study includes an unvocalized consonant transliteration of the selected Hebrew or Syriac word, plus source-provided vocalized Hebrew lemma transliteration where available. This is a spelling aid, not a pronunciation guide. No passage-level transliteration toggle is included. Syriac vowel/reading reconstruction requires a separate verified source.
