"""Validate actual PNG contents before allocating pixel buffers."""

from io import BytesIO
import warnings

from PIL import Image, UnidentifiedImageError

from efreigma.exceptions import InvalidImageError, InvalidMessageError

MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 4_000_000
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def load_png(image_bytes: bytes) -> Image.Image:
    """Return loaded RGB/RGBA pixels; reject other modes, APNG and 16-bit PNG.

    Both compressed bytes and decoded dimensions are bounded. The returned
    image owns its pixels and has no dependency on the input stream.
    """
    if not isinstance(image_bytes, bytes) or not image_bytes:
        raise InvalidImageError("Le fichier image est vide ou invalide.")
    if len(image_bytes) > MAX_FILE_BYTES:
        raise InvalidImageError("Le fichier dépasse la limite de 20 Mio.")
    if not image_bytes.startswith(PNG_SIGNATURE):
        raise InvalidImageError("Importez un véritable fichier PNG.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(image_bytes)) as candidate:
                if candidate.format != "PNG":
                    raise InvalidImageError("Importez un véritable fichier PNG.")
                if candidate.width * candidate.height > MAX_PIXELS:
                    raise InvalidImageError("L’image dépasse la limite de 4 millions de pixels.")
                # IHDR stores bit depth at byte 24. Pillow can silently reduce
                # 16-bit RGB to 8 bits, so check the original encoded depth.
                if candidate.mode not in ("RGB", "RGBA") or image_bytes[24] != 8:
                    raise InvalidImageError("Seuls les PNG RGB ou RGBA 8 bits sont pris en charge.")
                if candidate.mode == "RGB" and "transparency" in candidate.info:
                    raise InvalidImageError("Pour une image transparente, utilisez un PNG RGBA avec canal alpha.")
                if getattr(candidate, "is_animated", False):
                    raise InvalidImageError("Les PNG animés (APNG) ne sont pas pris en charge.")
                candidate.verify()
            with Image.open(BytesIO(image_bytes)) as loaded:
                loaded.load()
                return loaded.copy()
    except InvalidImageError:
        raise
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as error:
        raise InvalidImageError("L’image est trop volumineuse pour être traitée.") from error
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, IndexError, EOFError) as error:
        raise InvalidImageError("Le fichier PNG est corrompu ou illisible.") from error


def encode_message(message: str) -> bytes:
    """Require nonempty UTF-8 text, preserving whitespace and Unicode exactly."""
    if not isinstance(message, str) or not message:
        raise InvalidMessageError("Saisissez un message non vide.")
    try:
        return message.encode("utf-8")
    except UnicodeEncodeError as error:
        raise InvalidMessageError("Le message contient des caractères Unicode invalides.") from error
