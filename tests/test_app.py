from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from efreigma import extract_message, hide_message

APP = Path(__file__).resolve().parents[1] / "app.py"


def image_app():
    return AppTest.from_file(str(APP)).run().switch_page("views/image.py").run()


def test_app_starts_with_operations_disabled():
    app = image_app()
    assert not app.exception
    assert [tab.label for tab in app.tabs] == ["Cacher un message", "Extraire un message"]
    assert app.button(key="hide_button").disabled
    assert app.button(key="extract_button").disabled


def test_app_hide_and_extract_in_fresh_session(png_factory):
    source = png_factory("RGBA")
    message = "Démonstration 🔐\nExactement ce texte."
    with patch("streamlit.file_uploader", side_effect=lambda label, **kwargs:
               BytesIO(source) if kwargs["key"] == "hide_upload" else None):
        app = image_app()
        app.text_area(key="secret_text").input(message).run()
        app.button(key="hide_button").click().run()
        assert not app.exception
        result = app.session_state["hidden_png"]
        assert extract_message(result) == message
        # Editing the text invalidates the previously generated download.
        app.text_area(key="secret_text").input("autre message").run()
        assert "hidden_png" not in app.session_state
    with patch("streamlit.file_uploader", side_effect=lambda label, **kwargs:
               BytesIO(result) if kwargs["key"] == "extract_upload" else None):
        fresh = image_app()
        fresh.button(key="extract_button").click().run()
        assert not fresh.exception
        assert fresh.code[0].value == message
        assert fresh.session_state["extracted_message"] == message


def test_app_invalid_upload():
    with patch("streamlit.file_uploader", return_value=BytesIO(b"broken PNG")):
        app = image_app()
        assert not app.exception
        assert len(app.error) == 2
        assert app.button(key="hide_button").disabled
        assert app.button(key="extract_button").disabled


def test_app_extract_error_clears_old_result(png_factory):
    current = hide_message(png_factory(), "message")
    with patch("streamlit.file_uploader", side_effect=lambda label, **kwargs:
               BytesIO(current) if kwargs["key"] == "extract_upload" else None):
        app = image_app()
        app.button(key="extract_button").click().run()
        assert app.code[0].value == "message"
        current = png_factory()
        app.button(key="extract_button").click().run()
        assert not app.exception
        assert app.error
        assert not app.code
        assert "extracted_message" not in app.session_state
