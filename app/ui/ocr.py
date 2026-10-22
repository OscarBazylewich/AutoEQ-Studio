"""Reading text in a picture with Windows' own text reader (Windows.Media.Ocr, through the winrt packages): the
tracer's axis labels. AutoEQ Local used Tesseract.js in the page; Windows has a reader built in, so nothing big is
shipped. It reads in the languages installed in Windows (English is enough for numbers).

words(rgb) -> [{"text", "x0", "y0", "x1", "y1"}] in the picture's pixels. Raises Unavailable when Windows can't read
text here (no text reader language installed, or the winrt packages missing): the tracer then asks for the values.
"""
import asyncio

import numpy as np


class Unavailable(RuntimeError):
    pass


_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        try:
            from winrt.windows.media.ocr import OcrEngine
        except ImportError as e:  # (setup installs them; a copy without them still traces, by typed values)
            raise Unavailable("Windows' text reader isn't installed with this copy (run setup again).") from e
        eng = OcrEngine.try_create_from_user_profile_languages()
        if eng is None:
            raise Unavailable("Windows has no text reader language installed (Settings > Time & language > "
                              "Language: add English with its optical character recognition).")
        _engine = eng
    return _engine


async def _read(rgb):
    from winrt.windows.graphics.imaging import BitmapPixelFormat, SoftwareBitmap
    from winrt.windows.storage.streams import DataWriter
    h, w = rgb.shape[:2]
    bgra = np.empty((h, w, 4), np.uint8)
    bgra[..., 0], bgra[..., 1], bgra[..., 2], bgra[..., 3] = rgb[..., 2], rgb[..., 1], rgb[..., 0], 255
    dw = DataWriter()
    dw.write_bytes(bgra.tobytes())
    bmp = SoftwareBitmap.create_copy_from_buffer(dw.detach_buffer(), BitmapPixelFormat.BGRA8, w, h)
    res = await _get_engine().recognize_async(bmp)
    out = []
    for line in res.lines:
        for wd in line.words:
            r = wd.bounding_rect
            if wd.text.strip():
                out.append({"text": wd.text.strip(), "x0": r.x, "y0": r.y, "x1": r.x + r.width, "y1": r.y + r.height})
    return out


def words(rgb):
    """The words in an RGB picture (a NumPy array, height x width x 3, uint8). Blocks while reading (call it off the
    window's thread)."""
    _get_engine()
    rgb = np.ascontiguousarray(rgb, dtype=np.uint8)
    if rgb.shape[0] < 40 or rgb.shape[1] < 40:  # (Windows' reader refuses tiny pictures: padded with the edge colour)
        ph, pw = max(0, 40 - rgb.shape[0]), max(0, 40 - rgb.shape[1])
        rgb = np.pad(rgb, ((0, ph), (0, pw), (0, 0)), mode="edge")
    return asyncio.run(_read(rgb))
