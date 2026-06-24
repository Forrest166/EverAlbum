from dataclasses import dataclass
from typing import Callable


@dataclass(slots=True)
class AlbumBuildRequest:
    folder_list: list[str]
    pdf_path: str
    pptx_path: str | None = None
    album_title: str = "我的相册"
    palette_name: str = "四季自动"
    time_gap_hours: float = 6.0
    geo_radius_km: float = 30.0
    max_per_event: int = 30
    score_photos: bool = True
    resolve_geo: bool = True
    export_pptx: bool = True
    max_workers: int = 4
    cache_dir: str | None = None
    portrait_assets_dir: str | None = None
    enable_portrait_elements: bool = False
    progress_cb: Callable[[int], None] | None = None
    log_cb: Callable[[str], None] | None = None

