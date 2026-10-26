from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from efreigma import extract_audio_message

APP = Path(__file__).resolve().parents[1] / "app.py"


def audio_app():
    return AppTest.from_file(str(APP)).run().switch_page("views/audio.py").run()


def test_home_and_workshop_navigation():
    app = AppTest.from_file(str(APP)).run()
    assert not app.exception
    assert app.session_state["_workshop_page"] == "home"
    assert not app.tabs
    assert len(app.get("page_link")) == 7
    for page, route in [("views/image.py", "image"), ("views/audio.py", "audio"), ("views/video.py", "video"), ("views/home.py", "home")]:
        app.switch_page(page).run()
        assert not app.exception
        assert app.session_state["_workshop_page"] == route


def test_audio_disabled_before_upload():
    app = audio_app()
    assert not app.exception
    assert app.button(key="audio_hide_button").disabled
    assert app.button(key="audio_extract_button").disabled


def test_audio_hide_and_extract_new_session(wav_factory):
    source = wav_factory(channels=2, width=3)
    message = "Un petit mot dans le son 🔐\nÉté à Efrei."
    with patch("streamlit.file_uploader", side_effect=lambda label, **kwargs:
               BytesIO(source) if kwargs["key"] == "audio_hide_upload" else None):
        app = audio_app()
        app.text_area(key="audio_secret_text").input(message).run()
        app.button(key="audio_hide_button").click().run()
        assert not app.exception
        result = app.session_state["hidden_wav"]
        assert extract_audio_message(result) == message
        assert app.get("audio")
        assert app.get("download_button")
        app.text_area(key="audio_secret_text").input("nouveau texte").run()
        assert "hidden_wav" not in app.session_state
    with patch("streamlit.file_uploader", side_effect=lambda label, **kwargs:
               BytesIO(result) if kwargs["key"] == "audio_extract_upload" else None):
        fresh = audio_app()
        fresh.button(key="audio_extract_button").click().run()
        assert not fresh.exception
        assert fresh.code[0].value == message
        assert fresh.session_state["extracted_audio_message"] == message


def test_audio_invalid_upload():
    with patch("streamlit.file_uploader", return_value=BytesIO(b"ID3 mp3")):
        app = audio_app()
        assert not app.exception
        assert len(app.error) == 2
        assert app.button(key="audio_hide_button").disabled
        assert app.button(key="audio_extract_button").disabled


def test_page_change_discards_previous_results(wav_factory):
    with patch("streamlit.file_uploader", side_effect=lambda label, **kwargs:
               BytesIO(wav_factory()) if kwargs["key"] == "audio_hide_upload" else None):
        app = audio_app()
        app.text_area(key="audio_secret_text").input("secret audio").run()
        app.button(key="audio_hide_button").click().run()
        assert "hidden_wav" in app.session_state
        app.switch_page("views/image.py").run()
        assert not app.exception
        assert "hidden_wav" not in app.session_state
        assert not app.code
        assert not app.get("download_button")
