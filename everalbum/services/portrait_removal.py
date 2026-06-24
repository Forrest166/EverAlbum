import io

from PIL import Image


class PortraitRemovalService:
    def __init__(self):
        self._remove_fn = None

    @property
    def ready(self) -> bool:
        return self._remove_fn is not None

    def ensure_ready(self):
        if self._remove_fn is not None:
            return
        from rembg import remove

        dummy = Image.new("RGB", (1, 1), (128, 128, 128))
        buf = io.BytesIO()
        dummy.save(buf, "PNG")
        remove(buf.getvalue())
        self._remove_fn = remove

    def remove_bytes(self, data: bytes) -> bytes:
        self.ensure_ready()
        return self._remove_fn(data)

    def remove_image(self, image: Image.Image) -> Image.Image:
        buf = io.BytesIO()
        image.save(buf, "PNG")
        out = self.remove_bytes(buf.getvalue())
        return Image.open(io.BytesIO(out)).convert("RGBA")


_SERVICE = PortraitRemovalService()


def get_portrait_removal_service() -> PortraitRemovalService:
    return _SERVICE

