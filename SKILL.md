---
name: everalbum-maintainer
description: Maintain and extend the EverAlbum repository. Use when working on album generation, narrative text, event clustering, PDF/PPTX layout parity, portrait cutout integration, or the Tkinter GUIs in this repo.
---

# EverAlbum Maintainer

Use this skill when the task is to modify or extend the EverAlbum codebase.

Start with [`README.md`](./README.md). It contains the project overview, folder map, runtime dependencies, and the current behavioral rules that should not be broken casually.

## What This Repo Contains

- A smart album generator with a `tkinter` GUI
- A portrait background remover with a separate `tkinter` GUI
- Shared services for:
  - album build request config
  - narrative generation
  - portrait asset storage
  - portrait removal
  - workspace path resolution

## Entry Points

- Main launcher: `photo_album_generator pro.py`
- Portrait remover launcher: `portrait_bg_remover.py`
- Main package:
  - `everalbum/album_app.py`
  - `everalbum/portrait_app.py`

Preserve the launcher scripts unless the user explicitly asks to remove backward compatibility.

## First Steps

1. Read `README.md`.
2. Decide which surface the change belongs to:
   - narrative
   - event clustering
   - PDF layout
   - PPTX layout
   - portrait workflow
   - GUI only
3. Inspect only the relevant files first.
4. Before larger edits, understand whether both PDF and PPTX need to move together.

## File Map

- `everalbum/album_app.py`
  - the largest file in the repo
  - contains scanning, clustering, scoring, rendering, layout logic, and the main GUI
- `everalbum/services/narrative_engine.py`
  - event context modeling
  - chapter copy
  - page-note generation
  - album-wide de-duplication
- `everalbum/services/portrait_assets.py`
  - manages `portrait_elements/`
  - persists `manifest.json`
- `everalbum/services/portrait_removal.py`
  - lazy wrapper around `rembg`
- `everalbum/services/workspace.py`
  - canonical workspace root
  - default portrait library path
- `everalbum/portrait_app.py`
  - background remover GUI

## Important Working Rules

### Keep PDF and PPTX in sync

If the task touches any of the following, check both builders:

- chapter page composition
- page-top note badges
- photo layouts
- shaped image masking
- event metadata placement

In practice this usually means editing both:

- `AlbumBuilder`
- `PptxBuilder`

### Do not reintroduce noisy GPS-only titles

Current behavior:

- if an event has a real place name, it can be used as the chapter title
- if it only has coordinates, chapter pages should not fall back to a large GPS placeholder title like “途中坐标”

Preserve that unless the user asks for a different visual rule.

### Respect current event and month rules

Current album behavior:

- events with fewer than 5 photos are merged only within the same month
- months with fewer than 10 photos do not get a month divider page

If you change either rule, verify the impact on event count and month structure, not just whether the code runs.

### Output folders must not pollute later scans

`build_album()` now excludes cache folders and output folders from future scans.

If you change scan or output path logic, re-validate this behavior. It is easy to break.

### Generated artifacts are not source files

Ignore or treat as disposable:

- `*_render/`
- `*_cache/`
- generated `*.pdf`
- generated sample/test folders

Do not infer architecture from those artifacts. Read source files instead.

## Task-Specific Guidance

### Narrative changes

Start in `everalbum/services/narrative_engine.py`.

Watch for:

- exact duplicate page notes
- repeated openings / repeated first clauses
- oversized candidate pools that make generation too slow
- note extension behavior for very large events

After edits, validate both:

- exact-note duplication
- prefix-level repetition

### Layout changes

For any new layout or layout fix, review all of:

- `PacingEngine`
- `AlbumBuilder.LAYOUTS`
- `AlbumBuilder._render_layout`
- the concrete `_layout_*` implementation
- `PptxBuilder._slide_photos`

If the layout uses masks or non-rectangular images, verify that both PDF and PPTX still work.

### Event clustering changes

Work in `EventClusterer`.

After changes, inspect:

- raw event count
- merged event count
- count of tiny events left
- month photo counts
- whether month divider suppression still makes sense

### Portrait workflow changes

If the task involves cutouts, inspect:

- `everalbum/portrait_app.py`
- `everalbum/services/portrait_assets.py`
- `everalbum/services/portrait_removal.py`
- chapter-page portrait overlay logic in `album_app.py`

Preserve the default portrait library path from `workspace.py` unless the user asks to change it.

## Validation Workflow

### Fast checks

Run AST and import checks first:

```powershell
@'
from pathlib import Path
import ast
for rel in ['everalbum/album_app.py', 'everalbum/services/narrative_engine.py', 'everalbum/portrait_app.py']:
    ast.parse(Path(rel).read_text(encoding='utf-8'))
    print('AST OK', rel)
'@ | py -3 -X utf8 -
```

```powershell
@'
import importlib
for mod in ['everalbum.album_app', 'everalbum.portrait_app', 'everalbum.services.narrative_engine']:
    importlib.import_module(mod)
    print('IMPORT OK', mod)
'@ | py -3 -X utf8 -
```

### Real sample data

If `F:\Annual 2025` exists on the current machine, prefer using it as the smoke-test dataset because the user has already used it repeatedly in this workspace.

When generating test outputs:

- create a new folder under the photo source root
- use names like `codex_*_test`
- do not overwrite old sample outputs unless asked

### Visual verification

For layout or chapter-page changes:

- generate a small sample PDF first
- if `pdftoppm` is available, render a few pages to PNG
- inspect the resulting images rather than trusting terminal output alone

This matters because Windows console output can show mojibake even when the generated PDF is correct.

## Known Repo Realities

- `album_app.py` is still monolithic
- several source comments and some console strings appear garbled in terminal output
- the rendered PDF is a more reliable truth source than raw console text for Chinese copy
- the project has already been partially modularized, but not fully refactored

Treat the repo as stable-but-in-transition.

## Done Criteria

A maintenance task in this repo is usually only “done” when:

1. the code changes are implemented
2. AST/import checks pass
3. the relevant rendering path is validated
4. PDF/PPTX parity has been considered
5. no new scan pollution or obvious regression was introduced

## If You Need More Context

Read, in this order:

1. `README.md`
2. `everalbum/services/*.py`
3. `everalbum/album_app.py`

Avoid diving into the full `album_app.py` first unless the task is already clearly scoped there.
