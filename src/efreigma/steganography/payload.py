"""Shared EFR1 packet format for image and audio carriers."""

from collections.abc import Iterator
from hashlib import sha256
from hmac import compare_digest
import struct

from efreigma.exceptions import InvalidPayloadError

MAGIC = b"EFR1"
VERSION = 1
HEADER = struct.Struct(">4sBI32s")
HEADER_SIZE = HEADER.size


def make_packet(payload: bytes) -> bytes:
    return HEADER.pack(MAGIC, VERSION, len(payload), sha256(payload).digest()) + payload


def _read_bytes(channels: Iterator[int], count: int) -> bytes:
    result = bytearray(count)
    try:
        for index in range(count):
            value = 0
            for _ in range(8):
                value = (value << 1) | (next(channels) & 1)
            result[index] = value
    except StopIteration as error:
        raise InvalidPayloadError("Le message caché est tronqué.") from error
    return bytes(result)


def read_message(channels: Iterator[int], capacity: int) -> str:
    """Read bounded payload data, then validate digest and strict UTF-8."""
    magic, version, length, digest = HEADER.unpack(_read_bytes(channels, HEADER_SIZE))
    if magic != MAGIC:
        raise InvalidPayloadError("Aucun message Efreigma valide : signature absente ou invalide.")
    if version != VERSION:
        raise InvalidPayloadError("La version du message Efreigma n’est pas prise en charge.")
    if length == 0 or length > capacity:
        raise InvalidPayloadError("La longueur du message caché est invalide pour ce fichier.")
    payload = _read_bytes(channels, length)
    if not compare_digest(sha256(payload).digest(), digest):
        raise InvalidPayloadError("Le message caché est altéré : empreinte SHA-256 incorrecte.")
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise InvalidPayloadError("Le message caché ne contient pas un texte UTF-8 valide.") from error
