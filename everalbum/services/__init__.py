"""Shared services for EverAlbum."""

from .config import AlbumBuildRequest
from .narrative_engine import NarrativeContext, NarrativeEngine, is_non_location_label
from .portrait_assets import PortraitAsset, PortraitAssetStore
from .portrait_removal import PortraitRemovalService, get_portrait_removal_service
from .workspace import get_default_portrait_library_path, get_workspace_root

__all__ = [
    "AlbumBuildRequest",
    "NarrativeContext",
    "NarrativeEngine",
    "PortraitAsset",
    "PortraitAssetStore",
    "PortraitRemovalService",
    "get_default_portrait_library_path",
    "get_portrait_removal_service",
    "get_workspace_root",
    "is_non_location_label",
]
