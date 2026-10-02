from __future__ import annotations

import shutil
from pathlib import Path

import streamlit as st

from local_whois_dl.bundle import (
    BundleProgress,
    build_bundle,
    cleanup_stale_workdirs,
    create_workdir,
)
from local_whois_dl.sources import SOURCES

st.set_page_config(
    page_title="$whoami — WHOIS Database Builder",
    page_icon="🌐",
    layout="centered",
)

cleanup_stale_workdirs()


def human_size(value: int) -> str:
    size = float(value)
    for unit in ("o", "Kio", "Mio", "Gio"):
        if size < 1024 or unit == "Gio":
            return f"{size:.1f} {unit}" if unit != "o" else f"{int(size)} {unit}"
        size /= 1024
    return f"{value} o"


def clear_previous_bundle() -> None:
    workdir = st.session_state.pop("workdir", None)
    st.session_state.pop("archive_path", None)
    st.session_state.pop("archive_size", None)
    st.session_state.pop("generated_at", None)
    if workdir:
        shutil.rmtree(workdir, ignore_errors=True)


st.title("$whoami — WHOIS Database Builder")
st.caption("Prépare les données réseau officielles nécessaires à la base IP locale de $whoami.")

st.info(
    "Le bundle contient les 6 dumps RIPE détaillés utilisés par $whoami "
    "ainsi que le rapport mondial NRO. Le téléchargement représente plusieurs "
    "centaines de Mo et peut prendre un moment."
)

with st.expander("Sources téléchargées", expanded=False):
    for source in SOURCES:
        st.markdown(f"- **{source.filename}** — {source.label}")
    st.caption("Toutes les URLs sont figées dans l'application et utilisent ftp.ripe.net en HTTPS.")

progress_bar = st.empty()
current_file = st.empty()

if st.button("Préparer le bundle WHOIS", type="primary", use_container_width=True):
    clear_previous_bundle()
    workdir = create_workdir()
    st.session_state["workdir"] = str(workdir)

    bar = progress_bar.progress(0.0, text="Initialisation…")

    def report(event: BundleProgress) -> None:
        total = (
            f" / {human_size(event.total_bytes)}"
            if event.total_bytes is not None
            else ""
        )
        current_file.caption(
            f"{event.source_index}/{event.source_count} — "
            f"{event.source.label} — {human_size(event.downloaded_bytes)}{total}"
        )
        bar.progress(
            event.fraction,
            text=f"Téléchargement de {event.source.filename}",
        )

    try:
        with st.status("Téléchargement et validation des sources…", expanded=True) as status:
            result = build_bundle(workdir, progress=report)
            status.update(
                label="Bundle WHOIS prêt",
                state="complete",
                expanded=False,
            )

        bar.progress(1.0, text="Bundle prêt")
        current_file.empty()
        st.session_state["archive_path"] = str(result.archive_path)
        st.session_state["archive_size"] = result.archive_size_bytes
        st.session_state["generated_at"] = result.generated_at
    except Exception as exc:
        shutil.rmtree(workdir, ignore_errors=True)
        st.session_state.pop("workdir", None)
        bar.empty()
        current_file.empty()
        st.error(f"Impossible de préparer le bundle : {exc}")

archive_value = st.session_state.get("archive_path")
if archive_value:
    archive_path = Path(archive_value)
    if archive_path.is_file():
        archive_size = int(st.session_state.get("archive_size", archive_path.stat().st_size))
        generated_at = st.session_state.get("generated_at", "")
        st.success(
            f"Archive prête — {human_size(archive_size)}"
            + (f" — générée le {generated_at}" if generated_at else "")
        )
        with archive_path.open("rb") as archive:
            st.download_button(
                "Télécharger le bundle pour $whoami",
                data=archive,
                file_name=archive_path.name,
                mime="application/zip",
                type="primary",
                use_container_width=True,
            )

st.divider()
st.caption(
    "Aucune requête utilisateur n'est transformée en commande système. "
    "Les fichiers sont téléchargés depuis une liste blanche, contrôlés, "
    "hachés en SHA-256 puis regroupés dans une archive avec manifeste."
)
