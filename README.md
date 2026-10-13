# Syriac Parallel Reader

A working, mobile-friendly Hebrew–Syriac parallel reader for **all 50 chapters of Genesis**. Built for static GitHub Pages hosting and installable/offline PWA use. Original interface and book icon; no proprietary Parallel Plus designs, code, or assets are included.

## Start locally

Requires Python 3.10+; Node 22+ is needed only for the test commands. The generated website is already included. No dependency installation or text download is required to read it.

```sh
cd parallel-reader
python3 -m http.server 4173 --bind 127.0.0.1 --directory public
```

Open http://127.0.0.1:4173/ in your browser. `npm run dev` runs the same server. Do not open `index.html` as a `file://` URL: module loading, JSON fetches and service workers need HTTP. HTTPS or localhost is required for service workers.

## What works

- 1,533 paired Hebrew/Syriac Genesis verse references, with a single shared scroll surface that prevents independent-column drift.
- Book/chapter/verse selectors, previous/next chapter, hash links such as `#Gen.12.3`, saved selected passage and reading preferences.
- Per-verse read checkoffs, chapter progress and a daily reading streak saved in the current browser on this device.
- Side-by-side layout, optional stacking **within each verse**, text-size adjustment, Hebrew cantillation toggle that retains vowels.
- Self-hosted Noto Serif Hebrew and Noto Sans Syriac (Estrangela); explicit `dir="rtl"`, language tags and isolated text regions.
- Tap/click/keyboard word selection; Hebrew lemma components, morphology codes, BDB glosses, lexical root groups and on-demand abridged BDB entries.
- Syriac source glosses, lexemes and morphology, including component selection for attached prefixes. Complete displayed Syriac words stay in a single shaping run.
- Same-lemma occurrences in both languages; supplied Hebrew root occurrences. Counts are tokens, with verse references deduplicated for navigation.
- Optional Sefaria online lookup for Hebrew: matching headwords/dictionary names and links. Bundled study works independently of Sefaria, with an internet connection.
- Manifest, 192/512 PNG icons, project-relative paths, content-versioned service worker, offline chapter/font cache and update lifecycle.

The initial offline package is approximately **6.9 MiB**. Wait for “Genesis available offline” before disconnecting. All Genesis chapters and fonts are cached, including chapters you have not opened. BDB, lexical glosses and occurrence lists are served online and excluded from persistent offline caching. Consonant transliteration works offline. Install from the browser menu; on iOS/iPadOS use Share → Add to Home Screen. The in-app browser may not offer installation even though the manifest works in a normal browser.

## GitHub Pages

1. Create a GitHub repository and put the **contents of this `parallel-reader` directory at the repository root**, including `.github`, `public`, scripts, tests and `sources.lock.json`. Commit the generated `public/data`, fonts and `release.js`. Do not commit `sources/` or `node_modules/`.
2. Use `main` as the branch, or update the workflow's branch filter.
3. Under Settings → Pages → Build and deployment, select **GitHub Actions**.
4. Push to `main` or run the included Deploy reader workflow. It runs the unit/data checks, regenerates the offline inventory, uploads only `public/`, and deploys it.
5. Open `https://YOUR-ACCOUNT.github.io/YOUR-REPOSITORY/`. Test a direct `#Gen.50.26` link and install/offline behavior in your target mobile browser.

The workflow deploys already committed exports; it does not silently fetch newer datasets. No backend, runtime secret, database or build-time Node bundler is needed. The navigation bar stays pinned during passage scrolling; the study panel header keeps its close control visible during internal scrolling. All asset URLs, manifest paths and service-worker scope are relative to the deployed project directory. Hash routing avoids Pages 404s. Keep source at the repository root rather than nesting it one level deeper, unless you adjust the workflow paths.

## Rebuild and verify

For a fresh checkout, fetch the pinned source revisions first:

```sh
python3 scripts/fetch_sources.py
npm run build
npm test
```

`fetch_sources.py` uses the exact repository revisions in `sources.lock.json`, preserves downloaded notices and checks SHA-256. It does not update a lock already present. Source caches remain local and ignored by Git. The exporter uses only Python's standard library: no Text-Fabric installation is needed for this specific TF feature subset.

`npm run build` exports chapters, lexical index, BDB shards, lemma/root occurrence indexes and an alignment coverage report, then generates icons and a release inventory. After any public app/data/font edit, run `python3 scripts/build_site.py` so the service worker gets a new content-derived release. The worker intentionally waits for existing tabs to close before activation. During local editing, close all tabs/PWA windows for that origin and reopen, or clear this site's service worker/cache in browser developer tools. Do not mistake an old offline release for the latest source files.

`npm test` checks location bounds, accent preservation, component selection, source-provider behavior, all Genesis references, every lexical/occurrence pointer, BDB coverage, Syriac grouping, Hebrew punctuation and offline inventory completeness.

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
    chapters/Gen.1.json … Gen.50.json
    lexicon/index.json               Compact lemma metadata
    lexicon/bdb/a.json …              BDB shards, loaded only when requested
    occurrences.json                Genesis lemma/root inverted indexes
    alignment-report.json
    sources.lock.json               Upstream revisions + file checksums
scripts/
  fetch_sources.py                   Reproducible source acquisition
  build_data.py                      OSIS/TF preprocessing
  build_site.py                      Icon + cache inventory generation
tests/                               Integrity, helper and browser checks
.github/workflows/pages.yml           Static Pages deployment
sources.lock.json                    Committed source lock
notices/                             Preserved upstream README/license files
sources/                             Ignored original downloads
```

Runtime: catalog → one chapter JSON; first word selection → lemma index and occurrences; expanded BDB → one static letter shard. The entire BDB is not parsed into memory at startup. Lexical endpoints use network-only service-worker handling and are excluded from the offline inventory. JSON fetches are memoized during the session; service-worker caches are persistent and separate from application memory. Remote Sefaria calls occur only on explicit click and are not cached. Source XML and remote definition HTML are never inserted into the live DOM.

A row has a canonical ID (`Gen.1.1`), a reference-match status and independent Hebrew/Syriac token arrays. Tokens contain displayed text, trailing punctuation/spacing, source ID, lemma IDs and morphology. Syriac tokens additionally preserve their constituent source annotations. Lexicon keys are namespaced (`he:1254a`, `syr:BRJ`) to avoid conflating unrelated lexeme systems. Roots are source-supplied Hebrew lexical etymologies, not a derived triliteral guess; occurrence groups use the actual root-entry ID so homonymous roots stay distinct. Sefaria matches are not automatically treated as exact lemma/Strong-ID equivalents.

## Data choices and license boundaries

Read the full [sources and licensing notice](public/SOURCES.html), which is also available in the app. Exact input URLs, commits and hashes are in `sources.lock.json`.

| Candidate | Use in this MVP | License/provenance decision |
| --- | --- | --- |
| [Open Scriptures morphhb](https://github.com/openscriptures/morphhb) | Hebrew WLC Genesis, lemmas, morphology | WLC public domain; annotation CC BY 4.0. Commercially reusable Hebrew path with attribution. |
| [Open Scriptures HebrewLexicon](https://github.com/openscriptures/HebrewLexicon) | Glosses, lexical roots, transliterations, abridged BDB | Structured edition CC BY 4.0; underlying 1906 BDB public domain. Plain-text derivative, limited to entries used in Genesis. |
| [ETCBC Syriac Corpus v0.9](https://github.com/ETCBC/syriac/tree/v0.9) | Annotated Peshitta Genesis | Edition-derived consonantal text plus lexemes/glosses/morphology. Current repository LICENSE says MIT, while separate upstream Peshitta text notice restricts text to CC BY-NC. **Treat bundled Syriac as noncommercial and seek clarification before broader/commercial reuse.** Do not equate the software LICENSE with unrestricted text rights. |
| [ETCBC/peshitta](https://github.com/ETCBC/peshitta) | Investigated for full-OT expansion | Full OT plain text/TF available; [explicit text notice](https://github.com/ETCBC/peshitta/blob/master/docs/about.md) says CC BY-NC, with MIT conversion code. Provides no guarantee of the annotated-corpus lexical coverage. |
| [ETCBC/BHSA](https://github.com/ETCBC/bhsa) | Investigated, not bundled | Strong Hebrew TF analyses, but data CC BY-NC 4.0. Would add a restriction without solving a Genesis requirement better than OSHB. Treat BHSA separately from its MIT tooling. |
| [Sefaria](https://developers.sefaria.org/reference/get-words) | Optional online metadata lookup | Excellent extension point; licenses vary by resource/version. No blanket API reuse license. Full entries require a resource-specific policy. |
| Noto fonts | Both bundled | OFL 1.1; notices preserved; no remote font dependency. |

App code is MIT. That does **not** relicense bundled third-party data. The Syriac restriction means the combined prototype should not be described as an unrestricted commercially reusable dataset. Attribution remains accessible offline. The separate annotated-repository licensing discrepancy is recorded rather than hidden or “resolved” by selecting the more permissive file.

## Full-OT expansion and remaining gaps

1. Add OSHB book adapters and either the full ETCBC Peshitta text or separately vetted editions. The current exporter intentionally fixes Genesis; merely adding catalog entries does not load other books.
2. Replace identity-reference matching with reviewed mapping records that support missing, split, merged and differently numbered verses. All Genesis labels match; no complete philological equivalence audit has been performed. There is no word-to-word alignment.
3. Annotated Syriac v0.9 is an evolving corpus with incomplete OT coverage. For books without verified annotations, show surface-form lookup explicitly and do not claim lemma/root concordance. Add a licensed Syriac lexicon provider after evaluating entry rights and source-ID mappings (e.g. CAL or historical dictionary transcriptions). No CAL dictionary content is bundled or scraped.
4. Syriac is consonantal: no vowels/syame reconstruction, no automatic Syriac roots or cognates. Hebrew qere is shown as a note; display switching and a qere-based concordance remain future work. Full BDB typography and scholarly abbreviation expansion remain incomplete.
5. The optional Sefaria provider currently returns metadata/links. Full BDB definitions and linked commentaries should be loaded on demand only after checking per-resource licensing, sanitizing remote HTML, and verifying mapping/CORS. Sefaria text v3 can supply version-specific Hebrew text, but changing editions must preserve token alignment and select a specific version, not an unstable default.
6. Split full-OT concordances by language/book/lemma prefix; add a web worker or IndexedDB index if needed. Offer per-book offline downloads rather than precaching the full OT. Keep bounds and missing-data cases explicit. The 6.9 MiB Genesis cache is not a full-OT cache strategy.
7. Test actual installed Android/iOS PWAs, browser storage eviction, assistive technology and print/copy workflows before production launch. Browser-provided installation varies. No public repository was created or deployment performed in this handoff.

Word study includes an unvocalized consonant transliteration of the selected Hebrew or Syriac word, plus source-provided vocalized Hebrew lemma transliteration where available. This is a spelling aid, not a pronunciation guide. No passage-level transliteration toggle is included. Syriac vowel/reading reconstruction requires a separate verified source.
