"""Shared hiding/extraction flow, with independent state for each medium."""

import streamlit as st

from efreigma import (
    EfreigmaError, extract_audio_message, extract_message, get_audio_capacity,
    get_capacity, hide_audio_message, hide_message,
)
from efreigma.utils.audio_validators import load_wav


def clear_result(key: str) -> None:
    st.session_state.pop(key, None)


def preview(data: bytes, audio: bool, caption: str) -> None:
    if audio:
        st.caption(caption)
        st.audio(data, format="audio/wav")
    else:
        st.image(data, caption=caption, width=500)


def render_workshop(audio: bool = False) -> None:
    prefix = "audio_" if audio else ""
    extension = "wav" if audio else "png"
    format_name = "WAV" if audio else "PNG"
    hidden_key = "hidden_wav" if audio else "hidden_png"
    extracted_key = "extracted_audio_message" if audio else "extracted_message"
    capacity_fn = get_audio_capacity if audio else get_capacity
    hide_fn = hide_audio_message if audio else hide_message
    extract_fn = extract_audio_message if audio else extract_message
    hide_tab, extract_tab = st.tabs(["Cacher un message", "Extraire un message"])
    with hide_tab:
        st.subheader("01. Glisse ton petit mot ✉️")
        st.caption(f"Choisis {'un son' if audio else 'une image'}, écris ton secret, puis récupère ton {format_name}.")
        source = st.file_uploader(f"{'Audio WAV original' if audio else 'Image PNG originale'}", type=[extension],
                                  key=prefix + "hide_upload", on_change=clear_result, args=(hidden_key,))
        message = st.text_area("Message secret", placeholder="Écris ton message ici…",
                               height=150, key=prefix + "secret_text", on_change=clear_result, args=(hidden_key,))
        source_bytes = None
        capacity = 0
        valid_source = False
        if source is not None:
            source_bytes = source.getvalue()
            try:
                capacity = capacity_fn(source_bytes)
                valid_source = True
                preview(source_bytes, audio, "Audio original" if audio else "Image originale")
                if audio:
                    info = load_wav(source_bytes)
                    st.caption(f"{info.sample_rate:,} Hz · {info.channels} canal(aux) · {info.sample_width * 8} bits · {info.frames / info.sample_rate:.2f} s")
            except EfreigmaError as error:
                st.error(str(error))
        try:
            used = len(message.encode("utf-8"))
            valid_text = True
        except UnicodeEncodeError:
            used = 0
            valid_text = False
            st.error("Le message contient des caractères Unicode invalides.")
        if valid_source:
            left, right = st.columns(2)
            left.metric("Espace disponible", f"{capacity:,} octets")
            right.metric("Taille du message", f"{used:,} octets")
            st.progress(min(used / capacity, 1.0) if capacity else 0.0)
            if capacity == 0:
                st.warning("Ce fichier est trop petit pour contenir un message Efreigma.")
            elif used > capacity:
                st.error("Le message dépasse la capacité du fichier. Réduisez le texte ou utilisez un support plus grand.")
            st.caption("Certains caractères, comme les emojis, prennent plus de place.")
        if st.button("Cacher le message", type="primary", key=prefix + "hide_button",
                     disabled=not (valid_source and valid_text and 0 < used <= capacity)):
            clear_result(hidden_key)
            try:
                with st.spinner("Insertion du message…"):
                    st.session_state[hidden_key] = hide_fn(source_bytes, message)
            except EfreigmaError as error:
                st.error(str(error))
        if hidden_key in st.session_state:
            st.success(f"Message dissimulé. Téléchargez le {format_name} pour le conserver et l’extraire plus tard.")
            preview(st.session_state[hidden_key], audio, f"{format_name} contenant le message")
            st.download_button(f"Télécharger le {format_name}", data=st.session_state[hidden_key],
                               file_name=f"efreigma-secret.{extension}", mime="audio/wav" if audio else "image/png",
                               key=prefix + "download_carrier")
    with extract_tab:
        st.subheader("02. Écoute le petit secret 🔎" if audio else "02. Lis entre les pixels 🔎")
        st.caption(f"Importe le {format_name} Efreigma pour retrouver son petit mot.")
        carrier = st.file_uploader(f"{format_name} contenant un message", type=[extension], key=prefix + "extract_upload",
                                   on_change=clear_result, args=(extracted_key,))
        carrier_bytes = None
        valid_carrier = False
        if carrier is not None:
            carrier_bytes = carrier.getvalue()
            try:
                capacity_fn(carrier_bytes)
                valid_carrier = True
                preview(carrier_bytes, audio, "Audio à analyser" if audio else "Image à analyser")
            except EfreigmaError as error:
                st.error(str(error))
        if st.button("Extraire", type="primary", key=prefix + "extract_button", disabled=not valid_carrier):
            clear_result(extracted_key)
            try:
                with st.spinner("Vérification et extraction…"):
                    st.session_state[extracted_key] = extract_fn(carrier_bytes)
            except EfreigmaError as error:
                st.error(str(error))
        if extracted_key in st.session_state:
            st.success("Message extrait et intégrité vérifiée.")
            st.caption("Utilisez l’icône de copie du bloc ci-dessous pour copier le message.")
            st.code(st.session_state[extracted_key], language=None, wrap_lines=True)
            st.download_button("Télécharger le texte", data=st.session_state[extracted_key].encode("utf-8"),
                               file_name="efreigma-message.txt", mime="text/plain; charset=utf-8", key=prefix + "download_text")
    with st.expander("📎 Le petit rappel du prof"):
        st.caption("WAV PCM entier mono/stéréo · 8/16/24/32 bits · 192 kHz maximum · 20 Mio maximum" if audio else
                   "PNG RGB/RGBA 8 bits · 20 Mio maximum · 4 millions de pixels maximum")
        st.info("Le LSB ne chiffre pas votre message. SHA-256 vérifie son intégrité ; une modification du fichier peut le détruire.")
        if audio:
            st.caption("Gardez le WAV original : conversion MP3, changement de volume, rééchantillonnage ou montage peuvent effacer le message. Pour une altération sonore plus discrète, privilégiez le PCM 16 bits ou plus.")
