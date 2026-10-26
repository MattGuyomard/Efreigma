from io import BytesIO
import struct
from zlib import crc32

from PIL import Image
import pytest

from efreigma import InvalidImageError, extract_message, get_capacity, hide_message
from efreigma.utils import validators


@pytest.mark.parametrize("data", [b"", b"not a PNG", b"\x89PNG\r\n\x1a\n", None])
@pytest.mark.parametrize("operation", [get_capacity, extract_message, lambda data: hide_message(data, "test")])
def test_bad_files(data, operation):
    with pytest.raises(InvalidImageError):
        operation(data)


def test_corrupt_and_truncated_png(png_factory):
    source = png_factory()
    corrupt = bytearray(source)
    corrupt[29] ^= 1  # IHDR checksum
    for data in (bytes(corrupt), source[:40], source[:-20]):
        with pytest.raises(InvalidImageError):
            get_capacity(data)


def test_non_png_with_image_content():
    output = BytesIO()
    Image.new("RGB", (32, 32)).save(output, "JPEG")
    with pytest.raises(InvalidImageError, match="PNG"):
        get_capacity(output.getvalue())


@pytest.mark.parametrize("mode", ["L", "LA", "P", "1", "I;16"])
def test_unsupported_modes(png_factory, mode):
    with pytest.raises(InvalidImageError, match="8 bits"):
        get_capacity(png_factory(mode))


def test_16_bit_rgb_header_rejected(png_factory):
    data = bytearray(png_factory())
    data[24] = 16
    data[29:33] = struct.pack(">I", crc32(data[12:29]))
    with pytest.raises(InvalidImageError, match="8 bits"):
        get_capacity(bytes(data))


def test_apng_rejected():
    output = BytesIO()
    first = Image.new("RGB", (32, 32), "red")
    second = Image.new("RGB", (32, 32), "blue")
    first.save(output, "PNG", save_all=True, append_images=[second], duration=100)
    with pytest.raises(InvalidImageError, match="animés"):
        get_capacity(output.getvalue())


def test_rgb_transparency_requires_rgba():
    output = BytesIO()
    Image.new("RGB", (32, 32), "red").save(output, "PNG", transparency=(255, 0, 0))
    with pytest.raises(InvalidImageError, match="canal alpha"):
        get_capacity(output.getvalue())


def test_file_limit_checked_before_open(monkeypatch):
    monkeypatch.setattr(validators, "MAX_FILE_BYTES", 8)
    with pytest.raises(InvalidImageError, match="20 Mio"):
        get_capacity(b"\x89PNG\r\n\x1a\nX")


def test_pixel_limit_before_decode(png_factory, monkeypatch):
    source = png_factory(size=(10, 10))
    monkeypatch.setattr(validators, "MAX_PIXELS", 99)
    monkeypatch.setattr(Image.Image, "load", lambda *_: pytest.fail("Pixels should not be decoded"))
    with pytest.raises(InvalidImageError, match="pixels"):
        get_capacity(source)


def test_decompression_bomb_converted(png_factory, monkeypatch):
    source = png_factory()
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 600)
    with pytest.raises(InvalidImageError, match="volumineuse"):
        get_capacity(source)


def test_pixel_limit_boundary(png_factory, monkeypatch):
    monkeypatch.setattr(validators, "MAX_PIXELS", 1024)
    assert get_capacity(png_factory()) == 343
