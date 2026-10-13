# Verification record

## October 11 follow-up

The offline policy has changed: all Genesis texts and fonts are cached (about 6.9 MiB), while BDB/lexical indexes and concordances are network-only. Consonant transliteration works without those resources. The prior offline lexical checks below describe the earlier release, not the current policy.

The follow-up adds sticky book/chapter/verse navigation and a sticky word-study header. Browser checking at phone width confirmed the navigation stays at the top during verse scrolling, and the close button remains visible after scrolling the panel more than 550 pixels. Seven Node tests and six data tests pass, including new transliteration examples and exclusion of lexical assets from the offline inventory.

The final copied project was served directly from `/Users/masonjlewis/Documents/Code Experiments/Syriac_Reader`. At phone width, the pinned navigation ended at approximately 206 pixels and the selected verse began at 222 pixels, clearing the bar. After 558 pixels of internal study scrolling, the close button remained inside the panel header. With the server stopped and the page reloaded, Genesis 50 still opened; new lexical requests displayed the connection-required message while the selected Syriac word and consonant transliteration remained available. The destination was initially empty, and all 143 copied non-dependency files were checksum-verified against the working project.

Verified locally on October 11, 2026. The prototype has not been deployed to a public GitHub repository or installed as an OS-level mobile app.

## Passed checks

- Six Node tests: bounded passage links, vowel-preserving accent removal, verse deduplication, prefix-aware component choice, static BDB provider and Sefaria metadata adapter.
- Six Python checks: 50 chapters/1,533 references, every lemma/occurrence/BDB pointer, Syriac component reconstruction, consecutive Hebrew punctuation, distinct homonymous roots and complete offline inventory.
- Browser interaction in the Codex in-app browser at desktop and 390-pixel phone viewports: paired verse layout, chapter/verse controls, Hebrew BDB expansion, Syriac component study, same-lemma and root occurrence lists, concordance jump to Genesis 5:5, stacked layout and help dialog.
- Fresh project-subpath loading, including relative fonts, JSON, manifest and service worker. Final preview is served under `/reader-preview/`; the repository-path check also used `/parallel-reader/public/`.
- Offline verification: stopped the HTTP server completely, opened previously unread Genesis 50, selected 50:26, reloaded the page, loaded Syriac lexical information and expanded a previously unopened Hebrew BDB shard. Then restored the server.
- Optional real Sefaria lookup: a Hebrew ברא query with Genesis 1:1 context returned three lexical matches in the browser. Results showed metadata and external links; no remote definition content was saved.
- At a 320-pixel viewport and maximum 40-pixel text setting, Genesis 41 had no page overflow or word fragments wider than their text container. Long words wrap without splitting their source string into separate DOM components.
- Hebrew accent switch removed cantillation while retaining vowel marks.
- All 16 Genesis qere notes were associated in the source with a preceding ketiv word. The exported reader shows the written form and supplies the qere in study notes.
- JavaScript syntax checks passed for the main app, service worker and providers.

Screenshots are supplied separately as `reader-desktop.jpg` and `reader-mobile.jpg` in the output folder.

## Not yet verified

- OS-level PWA installation on real iOS/Android devices, storage eviction and low-memory behavior.
- Complete screen-reader/keyboard audit and print/copy workflows.
- A complete scholarly audit of every paired verse or lexical analysis. Reference coverage is not semantic equivalence.
- Live GitHub Actions deployment. The supplied workflow and relative-path strategy still need a first run in the destination account.
- The optional `tests/browser.mjs` regression script is supplied but was not executed here; browser checks above were performed through the connected browser controls. It uses a separately installed Playwright Chromium when you run it.

The licensing discrepancy between the annotated Syriac repository's MIT file and its edition-derived text rights remains documented in `public/SOURCES.html`. This record does not resolve the discrepancy or grant broader rights.
