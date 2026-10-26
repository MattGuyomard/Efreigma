"""EFR1: sequential RGB least-significant bits, bytes stored MSB first."""

from collections.abc import Iterator
from io import BytesIO

from efreigma.exceptions import InvalidMessageError, InvalidPayloadError
from efreigma.utils.validators import encode_message, load_png

from efreigma.steganography.payload import HEADER, HEADER_SIZE, MAGIC, VERSION, make_packet, read_message


def _capacity(width: int, height: int) -> int:
    return max(0, width * height * 3 // 8 - HEADER_SIZE)


def _channel_indices(length: int, stride: int) -> Iterator[int]:
    for base in range(0, length, stride):
        yield base
        yield base + 1
        yield base + 2


def get_capacity(image_bytes: bytes) -> int:
    """Maximum UTF-8 payload bytes, after the 41-byte header (zero if too small)."""
    with load_png(image_bytes) as image:
        return _capacity(*image.size)


def hide_message(image_bytes: bytes, message: str) -> bytes:
    """Return a new lossless PNG containing nonempty text, without encryption.

    Dimensions and alpha samples are preserved. Metadata is not copied.
    Raise EfreigmaError subclasses on invalid images, text or capacity.
    """
    payload = encode_message(message)
    with load_png(image_bytes) as image:
        capacity = _capacity(*image.size)
        if len(payload) > capacity:
            raise InvalidMessageError(
                f"Le message occupe {len(payload)} octets UTF-8 ; capacité : {capacity} octets."
            )
        packet = make_packet(payload)
        pixels = bytearray(image.tobytes())
        indices = _channel_indices(len(pixels), len(image.getbands()))
        for value in packet:
            for shift in range(7, -1, -1):
                index = next(indices)
                pixels[index] = (pixels[index] & 0xFE) | ((value >> shift) & 1)
        image.frombytes(bytes(pixels))
        output = BytesIO()
        # Metadata is deliberately discarded; RGBA alpha is in the pixels.
        image.info.clear()
        image.save(output, format="PNG")
        return output.getvalue()


def extract_message(image_bytes: bytes) -> str:
    """Validate signature, version, length, digest and UTF-8; return exact text.

    Extraction uses only the PNG bytes, never application/session state.
    """
    with load_png(image_bytes) as image:
        if image.width * image.height * 3 < HEADER_SIZE * 8:
            raise InvalidPayloadError("L’image est trop petite pour contenir un en-tête Efreigma.")
        pixels = image.tobytes()
        channels = (pixels[index] for index in _channel_indices(len(pixels), len(image.getbands())))
        return read_message(channels, _capacity(*image.size))
