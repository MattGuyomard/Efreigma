from io import BytesIO
import wave

from PIL import Image
import pytest


@pytest.fixture
def png_factory():
    def make(mode="RGB", size=(32, 32)):
        image = Image.new(mode, size)
        if mode in ("RGB", "RGBA"):
            image.putdata([
                ((i * 17) % 256, (i * 31) % 256, (i * 47) % 256)
                + (((i * 13) % 256,) if mode == "RGBA" else ())
                for i in range(size[0] * size[1])
            ])
        output = BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()
    return make


@pytest.fixture
def wav_factory():
    def make(channels=1, width=2, frames=4096, rate=44100):
        output = BytesIO()
        with wave.open(output, "wb") as audio:
            audio.setnchannels(channels)
            audio.setsampwidth(width)
            audio.setframerate(rate)
            audio.writeframes(bytes((index * 17 + 5) % 256 for index in range(frames * channels * width)))
        return output.getvalue()
    return make
