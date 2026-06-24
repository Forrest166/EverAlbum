from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from PIL import Image

from .workspace import get_default_portrait_library_path


@dataclass(slots=True)
class PortraitAsset:
    name: str
    path: str
    source_path: str = ""
    width: int = 0
    height: int = 0
    created_at: str = ""
    tags: list[str] = field(default_factory=list)


class PortraitAssetStore:
    def __init__(self, root_dir: str | Path | None = None):
        self.root_dir = Path(root_dir or get_default_portrait_library_path()).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.root_dir / "manifest.json"

    def _slugify(self, text: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", text.strip()).strip("_")
        return slug or "portrait"

    def _load_manifest(self) -> list[dict]:
        if not self.manifest_path.exists():
            return []
        try:
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save_manifest(self, items: list[dict]):
        self.manifest_path.write_text(
            json.dumps(items, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_assets(self) -> list[PortraitAsset]:
        manifest = self._load_manifest()
        assets: list[PortraitAsset] = []
        known = set()

        for raw in manifest:
            asset = PortraitAsset(**raw)
            if Path(asset.path).exists():
                assets.append(asset)
                known.add(str(Path(asset.path).resolve()))

        for path in sorted(self.root_dir.glob("*.png")):
            resolved = str(path.resolve())
            if resolved in known:
                continue
            try:
                with Image.open(path) as img:
                    width, height = img.size
            except Exception:
                width = height = 0
            assets.append(
                PortraitAsset(
                    name=path.stem,
                    path=resolved,
                    width=width,
                    height=height,
                    created_at=datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                    tags=["auto-discovered"],
                )
            )

        assets.sort(key=lambda item: item.created_at or item.name, reverse=True)
        self._save_manifest([asdict(item) for item in assets])
        return assets

    def open_image(self, asset: PortraitAsset) -> Image.Image:
        return Image.open(asset.path).convert("RGBA")

    def save_asset(
        self,
        image: Image.Image,
        source_path: str = "",
        name: str = "",
        tags: list[str] | None = None,
    ) -> PortraitAsset:
        base = self._slugify(name or Path(source_path).stem or "portrait")
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = self.root_dir / f"{base}_{stamp}.png"
        image.save(out_path, "PNG")

        asset = PortraitAsset(
            name=out_path.stem,
            path=str(out_path.resolve()),
            source_path=source_path,
            width=image.width,
            height=image.height,
            created_at=datetime.now().isoformat(timespec="seconds"),
            tags=list(tags or ["portrait", "cutout"]),
        )

        items = [asdict(item) for item in self.list_assets()]
        items = [item for item in items if item["path"] != asset.path]
        items.insert(0, asdict(asset))
        self._save_manifest(items)
        return asset
