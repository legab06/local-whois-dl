from __future__ import annotations

import gzip
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import requests

from .sources import ALLOWED_DOWNLOAD_HOSTS, Source

CHUNK_SIZE = 1024 * 1024
USER_AGENT = "local-whois-dl/1 (+https://github.com/legab06/local-whois-dl)"
ProgressCallback = Callable[[int, int | None], None]


class DownloadError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DownloadedFile:
    source: Source
    path: Path
    size_bytes: int
    sha256: str
    last_modified: str | None
    etag: str | None
    dataset_date: str | None


def _validate_final_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_DOWNLOAD_HOSTS:
        raise DownloadError(f"redirection vers une destination non autorisée : {url}")


def _validate_gzip(path: Path) -> None:
    with path.open("rb") as handle:
        if handle.read(2) != b"\x1f\x8b":
            raise DownloadError(f"{path.name} n'est pas un fichier gzip")

    try:
        with gzip.open(path, "rb") as handle:
            if not handle.read(512):
                raise DownloadError(f"{path.name} est vide après décompression")
    except (OSError, EOFError) as exc:
        raise DownloadError(f"{path.name} est un gzip invalide : {exc}") from exc


def _validate_nro(path: Path) -> str:
    try:
        with path.open("rt", encoding="utf-8", errors="strict") as handle:
            for _ in range(100):
                line = handle.readline()
                if line == "":
                    break
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                fields = [field.strip() for field in line.split("|")]
                if (
                    len(fields) != 7
                    or fields[0] not in {"2", "2.3"}
                    or fields[1] != "nro"
                    or not fields[2].isdigit()
                    or not fields[3].isdigit()
                    or len(fields[5]) != 8
                    or not fields[5].isdigit()
                ):
                    raise DownloadError("en-tête NRO delegated-extended invalide")
                return fields[5]
    except UnicodeDecodeError as exc:
        raise DownloadError("le fichier NRO n'est pas du texte UTF-8 valide") from exc

    raise DownloadError("en-tête NRO delegated-extended absent")


def validate_source(source: Source, path: Path) -> str | None:
    if not path.is_file() or path.stat().st_size == 0:
        raise DownloadError(f"{source.filename} est absent ou vide")
    if source.kind == "gzip":
        _validate_gzip(path)
        return None
    if source.kind == "nro":
        return _validate_nro(path)
    raise DownloadError(f"type de source inconnu : {source.kind}")


def download_source(
    source: Source,
    destination: Path,
    progress: ProgressCallback | None = None,
) -> DownloadedFile:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(f".{destination.name}.part")
    partial.unlink(missing_ok=True)

    digest = hashlib.sha256()
    downloaded = 0
    total: int | None = None

    try:
        with requests.get(
            source.url,
            stream=True,
            allow_redirects=True,
            timeout=(15, 180),
            headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"},
        ) as response:
            response.raise_for_status()
            _validate_final_url(response.url)

            raw_length = response.headers.get("Content-Length")
            if raw_length:
                try:
                    total = int(raw_length)
                except ValueError:
                    total = None
                if total is not None and total > source.max_bytes:
                    raise DownloadError(
                        f"{source.filename} dépasse la limite autorisée "
                        f"({total} octets > {source.max_bytes})"
                    )

            with partial.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if not chunk:
                        continue
                    downloaded += len(chunk)
                    if downloaded > source.max_bytes:
                        raise DownloadError(
                            f"{source.filename} dépasse la limite autorisée"
                        )
                    digest.update(chunk)
                    handle.write(chunk)
                    if progress is not None:
                        progress(downloaded, total)

            if total is not None and downloaded != total:
                raise DownloadError(
                    f"téléchargement incomplet de {source.filename} "
                    f"({downloaded}/{total} octets)"
                )

            os.replace(partial, destination)
            dataset_date = validate_source(source, destination)
            return DownloadedFile(
                source=source,
                path=destination,
                size_bytes=downloaded,
                sha256=digest.hexdigest(),
                last_modified=response.headers.get("Last-Modified"),
                etag=response.headers.get("ETag"),
                dataset_date=dataset_date,
            )
    except requests.RequestException as exc:
        raise DownloadError(f"échec du téléchargement de {source.filename} : {exc}") from exc
    finally:
        partial.unlink(missing_ok=True)
