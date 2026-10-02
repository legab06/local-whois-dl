from __future__ import annotations

import json
import shutil
import tempfile
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .downloader import DownloadedFile, download_source
from .sources import SOURCES, Source

BUNDLE_FORMAT = "whoami-ipdb-sources"
BUNDLE_FORMAT_VERSION = 1
WORKDIR_PREFIX = "local-whois-dl-"


@dataclass(frozen=True, slots=True)
class BundleProgress:
    source: Source
    source_index: int
    source_count: int
    downloaded_bytes: int
    total_bytes: int | None

    @property
    def fraction(self) -> float:
        local = (
            min(self.downloaded_bytes / self.total_bytes, 1.0)
            if self.total_bytes
            else 0.0
        )
        return min(((self.source_index - 1) + local) / self.source_count, 1.0)


@dataclass(frozen=True, slots=True)
class BundleResult:
    archive_path: Path
    archive_size_bytes: int
    generated_at: str
    manifest: dict[str, object]


ProgressCallback = Callable[[BundleProgress], None]


def _manifest_entry(item: DownloadedFile) -> dict[str, object]:
    entry: dict[str, object] = {
        "key": item.source.key,
        "filename": item.source.filename,
        "url": item.source.url,
        "size_bytes": item.size_bytes,
        "sha256": item.sha256,
    }
    if item.last_modified:
        entry["last_modified"] = item.last_modified
    if item.etag:
        entry["etag"] = item.etag
    if item.dataset_date:
        entry["dataset_date"] = item.dataset_date
    return entry


def build_manifest(
    downloads: list[DownloadedFile], generated_at: str
) -> dict[str, object]:
    return {
        "format": BUNDLE_FORMAT,
        "format_version": BUNDLE_FORMAT_VERSION,
        "generated_at": generated_at,
        "compatible_with": {
            "application": "$whoami - Lookup",
            "ipdb_source_bundle": 1,
        },
        "sources": [_manifest_entry(item) for item in downloads],
    }


def build_bundle(
    workdir: Path,
    progress: ProgressCallback | None = None,
) -> BundleResult:
    workdir.mkdir(parents=True, exist_ok=True)
    source_dir = workdir / "sources"
    source_dir.mkdir(parents=True, exist_ok=True)

    downloads: list[DownloadedFile] = []
    source_count = len(SOURCES)

    try:
        for index, source in enumerate(SOURCES, start=1):
            def on_download(
                downloaded: int,
                total: int | None,
                *,
                current_source: Source = source,
                current_index: int = index,
            ) -> None:
                if progress is not None:
                    progress(
                        BundleProgress(
                            source=current_source,
                            source_index=current_index,
                            source_count=source_count,
                            downloaded_bytes=downloaded,
                            total_bytes=total,
                        )
                    )

            item = download_source(
                source,
                source_dir / source.filename,
                progress=on_download,
            )
            downloads.append(item)
            if progress is not None:
                progress(
                    BundleProgress(
                        source=source,
                        source_index=index,
                        source_count=source_count,
                        downloaded_bytes=item.size_bytes,
                        total_bytes=item.size_bytes,
                    )
                )

        generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        manifest = build_manifest(downloads, generated_at)
        manifest_path = workdir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        date_part = generated_at[:10]
        archive_path = workdir / f"whoami-whois-{date_part}.zip"
        with zipfile.ZipFile(
            archive_path,
            "w",
            allowZip64=True,
        ) as archive:
            for item in downloads:
                compression = (
                    zipfile.ZIP_STORED
                    if item.source.filename.endswith(".gz")
                    else zipfile.ZIP_DEFLATED
                )
                archive.write(
                    item.path,
                    arcname=item.source.filename,
                    compress_type=compression,
                )
            archive.write(
                manifest_path,
                arcname="manifest.json",
                compress_type=zipfile.ZIP_DEFLATED,
            )

        return BundleResult(
            archive_path=archive_path,
            archive_size_bytes=archive_path.stat().st_size,
            generated_at=generated_at,
            manifest=manifest,
        )
    finally:
        shutil.rmtree(source_dir, ignore_errors=True)
        (workdir / "manifest.json").unlink(missing_ok=True)


def create_workdir() -> Path:
    return Path(tempfile.mkdtemp(prefix=WORKDIR_PREFIX))


def cleanup_stale_workdirs(max_age_seconds: int = 6 * 60 * 60) -> None:
    root = Path(tempfile.gettempdir())
    cutoff = time.time() - max_age_seconds
    for path in root.glob(f"{WORKDIR_PREFIX}*"):
        try:
            if path.is_dir() and path.stat().st_mtime < cutoff:
                shutil.rmtree(path, ignore_errors=True)
        except OSError:
            continue
