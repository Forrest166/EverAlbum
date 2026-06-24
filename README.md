# EverAlbum
This is an automatic album generator that organizes your own photos, especially suitable for large collections of 1,000–5,000 images. It intelligently clusters photos by month and visual style similarity, then creates beautifully arranged albums using more than 40 different photo layout styles.  **Note:** The original interface is in Chinese. 
----------------------------------------------------------------------------------------------------------------------------------------
EverAlbum is a smart album generation project with a `tkinter` interface. It currently consists of two main tracks:
- **Album Main Program**: Aggregates photos by timeline and location to generate an A4 `PDF`, with an optional export to `PPTX`.
- **Portrait Background Remover**: Uses `rembg` to remove backgrounds from selected portraits and saves the transparent PNGs to the album asset library for use as overlays on chapter pages.

The current code has completed the first round of modularization but still retains a practical constraint: the main logic for album generation is still concentrated in `[everalbum/album_app.py](/D:/Codex/EverAlbum/everalbum/album_app.py)`. For future maintenance, it is recommended to treat it as a "stable but heavy" core file.

## Directory Structure
```text
EverAlbum/
├─ photo_album_generator pro.py          # Main program compatibility launcher
├─ portrait_bg_remover.py                # Background remover tool compatibility launcher
├─ everalbum/
│  ├─ __init__.py
│  ├─ album_app.py                       # Album scanning, clustering, narrative, PDF/PPTX building, GUI
│  ├─ portrait_app.py                    # Portrait background removal GUI
│  └─ services/
│     ├─ config.py                       # AlbumBuildRequest configuration data model
│     ├─ narrative_engine.py             # Chapter copy / tab copy generation
│     ├─ portrait_assets.py              # Portrait asset library and manifest
│     ├─ portrait_removal.py             # rembg wrapper
│     └─ workspace.py                    # Workspace root directory / default asset library path
├─ portrait_elements/                    # Default portrait asset library (auto-created after running)
└─ SKILL.md                              # Skill document for future maintenance

---------------------------------------------------------------------------------------------
# Examples
<img width="1410" height="1380" alt="back cover example" src="https://github.com/user-attachments/assets/8094b3c2-7ed3-4b8c-94c9-7ce5c58ee026" />
<img width="826" height="1152" alt="example1" src="https://github.com/user-attachments/assets/8e297a40-ddc5-458f-bf46-63d45552d950" />
<img width="794" height="1128" alt="chapter" src="https://github.com/user-attachments/assets/d7027ae6-9afa-486a-8a27-190e5bc551df" />
<img width="806" height="1132" alt="example2" src="https://github.com/user-attachments/assets/a91de134-e11b-442b-a381-31e1463b1db0" />
<img width="806" height="1132" alt="example2" src="https://github.com/user-attachments/assets/68267531-e7ec-4458-ac14-9ece169e403e" />
<img width="802" height="1136" alt="example3" src="https://github.com/user-attachments/assets/e6477817-af8d-40bd-8ddf-6ca3237c291f" />
<img width="804" height="1134" alt="example4" src="https://github.com/user-attachments/assets/e56a34b2-a799-44ba-8195-5ad9e0534889" />
