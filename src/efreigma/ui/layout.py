"""Shared classroom shell and static illustrations."""

from pathlib import Path
import json

import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parents[3]


def artwork(kind: str) -> str:
    return (ROOT / "assets" / f"{kind}.svg").read_text(encoding="utf-8")


def render_header() -> None:
    styles = (ROOT / "assets" / "classroom.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{styles}</style>", unsafe_allow_html=True)
    st.markdown('''<div class="class-header">
      <div class="class-logo" aria-label="Efreigma"><span>E</span><span>f</span><span>r</span><span>e</span><span>i</span><span>g</span><span>m</span><span>a</span><span>.</span></div>
      <div class="class-stamp">LE CLUB DES SECRETS</div>
    </div>''', unsafe_allow_html=True)
    home, image, audio, video = st.columns(4, gap="small")
    with home:
        st.page_link("views/home.py", label="La classe", icon="🏠")
    with image:
        st.page_link("views/image.py", label="Atelier image", icon="🎨")
    with audio:
        st.page_link("views/audio.py", label="Atelier audio", icon="🎵")
    with video:
        st.page_link("views/video.py", label="Atelier vidéo", icon="🎬")


def render_hero(kind: str) -> None:
    if kind == "image":
        kicker = "✏️ À vos pixels, prêts…"
        title = "Un secret dans<br>ton <em>image.</em>"
        description = "Un petit mot passé en douce, version numérique.<br>Glisse ton message dans un PNG et laisse les pixels garder le secret."
        supplies = "<span>PNG uniquement</span><span>Accents &amp; emojis bienvenus</span>"
        lesson = (
            "<strong>Pour cacher :</strong> le texte devient des bits (0 et 1), glissés dans le dernier bit "
            "des canaux rouge, vert et bleu des pixels du PNG.<br>"
            "<strong>Pour retrouver :</strong> on relit ces bits dans le même ordre, on vérifie l’intégrité "
            "du message et on reconstitue le texte.<br>"
            "<em>Le message est dissimulé, sans chiffrement : on l’extrait, on ne le déchiffre pas.</em>"
        )
    elif kind == "audio":
        kicker = "♪ Monte le son, garde le secret…"
        title = "Un petit mot<br>dans le <em>son.</em>"
        description = "Les cassettes aussi ont leurs petits secrets.<br>Cache un texte dans un WAV, puis retrouve-le entre les notes."
        supplies = "<span>WAV PCM uniquement</span><span>Mono &amp; stéréo</span><span>8 · 16 · 24 · 32 bits</span>"
        lesson = (
            "<strong>Pour cacher :</strong> le texte devient des bits (0 et 1), glissés dans le dernier bit "
            "des valeurs numériques du son, les échantillons du WAV.<br>"
            "<strong>Pour retrouver :</strong> on relit ces bits dans le même ordre, on vérifie l’intégrité "
            "du message et on reconstitue le texte.<br>"
            "<em>Le message est dissimulé, sans chiffrement : on l’extrait, on ne le déchiffre pas.</em>"
        )
    elif kind == "video":
        kicker = "🎬 Silence, ça tourne…"
        title = "Un secret<br>dans le <em>film.</em>"
        description = "La classe fait son cinéma.<br>Glisse un petit mot dans les images d’un clip et retrouve-le après le générique."
        supplies = "<span>Clips de 30 s maximum</span><span>Sortie MKV sans perte</span><span>Le son est conservé</span>"
        lesson = (
            "<strong>Pour cacher :</strong> les bits du texte sont glissés dans le dernier bit des canaux "
            "rouge, vert et bleu des pixels, image après image. Le MKV sans perte conserve ces bits.<br>"
            "<strong>Pour retrouver :</strong> on parcourt les images du MKV dans le même ordre, on relit "
            "les bits et on vérifie l’intégrité du message avant de reconstituer le texte.<br>"
            "<em>Le message est dissimulé, sans chiffrement : on l’extrait, on ne le déchiffre pas.</em>"
        )
    else:
        kicker = "✏️ Bienvenue dans la classe des secrets"
        title = "Choisis ton<br><em>atelier.</em>"
        description = "Une image, un morceau, un petit film.<br>Pose ton cartable et choisis où glisser ton petit mot."
        supplies = ""
        lesson = "Aujourd’hui : des secrets dans les images, les sons et les films."
    illustration = artwork(kind if kind in ("audio", "video") else "image")
    supplies_block = f'<div class="class-supplies">{supplies}</div>' if supplies else ""
    st.markdown(f'''<div class="class-hero"><div>
      <div class="class-kicker">{kicker}</div><h1>{title}</h1>
      <div class="class-description">{description}</div>
    </div>{illustration}</div>{supplies_block}
    <div class="class-lesson"><small>AU TABLEAU · LA LEÇON DU JOUR</small>{lesson}</div>''', unsafe_allow_html=True)


def render_footer(page_path: str = "") -> None:
    st.markdown('<div class="class-footer"><span>Efreigma — Efrei Cybersécurity &amp; Ethical Hacking</span><span>Fin du cours. Gardez vos petits mots ! ✏️</span></div>', unsafe_allow_html=True)
    transition = (ROOT / "assets" / "page-transition.js").read_text(encoding="utf-8")
    ready_path = json.dumps("/" + page_path)
    script = json.dumps(f"{transition}\nwindow.efreigmaTransition.ready({ready_path});")
    components.html(
        '<script>(() => { const script = parent.document.createElement("script"); '
        f'script.textContent = {script}; '
        'parent.document.head.appendChild(script); script.remove(); })();</script>',
        height=0, scrolling=False,
    )
