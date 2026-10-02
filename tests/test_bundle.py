from __future__ import annotations

import gzip
from pathlib import Path
from urllib.parse import urlparse

import pytest

from local_whois_dl.bundle import BUNDLE_FORMAT, build_manifest
from local_whois_dl.downloader import DownloadError, DownloadedFile, validate_source
from local_whois_dl.sources import ALLOWED_DOWNLOAD_HOSTS, SOURCES, Source


def test_all_sources_are_https_and_whitelisted() -> None:
    assert len(SOURCES) == 7
    assert len({source.filename for source in SOURCES}) == len(SOURCES)

    for source in SOURCES:
        parsed = urlparse(source.url)
        assert parsed.scheme == "https"
        assert parsed.hostname in ALLOWED_DOWNLOAD_HOSTS


def test_expected_whoami_ripe_filenames_are_present() -> None:
    names = {source.filename for source in SOURCES}
    assert {
        "ripe.db.organisation.gz",
        "ripe.db.aut-num.gz",
        "ripe.db.inetnum.gz",
        "ripe.db.inet6num.gz",
        "ripe.db.route.gz",
        "ripe.db.route6.gz",
    } <= names


def test_validates_gzip_source(tmp_path: Path) -> None:
    source = Source(
        key="test",
        label="test",
        filename="test.gz",
        url="https://ftp.ripe.net/test.gz",
        kind="gzip",
        max_bytes=1024 * 1024,
    )
    path = tmp_path / source.filename
    with gzip.open(path, "wb") as handle:
        handle.write(b"inetnum: 192.0.2.0 - 192.0.2.255\n")

    assert validate_source(source, path) is None


def test_rejects_non_gzip_source(tmp_path: Path) -> None:
    source = Source(
        key="test",
        label="test",
        filename="test.gz",
        url="https://ftp.ripe.net/test.gz",
        kind="gzip",
        max_bytes=1024 * 1024,
    )
    path = tmp_path / source.filename
    path.write_text("not gzip", encoding="utf-8")

    with pytest.raises(DownloadError):
        validate_source(source, path)


def test_extracts_nro_dataset_date(tmp_path: Path) -> None:
    source = Source(
        key="nro",
        label="NRO",
        filename="nro-delegated-stats",
        url="https://ftp.ripe.net/nro-delegated-stats",
        kind="nro",
        max_bytes=1024 * 1024,
    )
    path = tmp_path / source.filename
    path.write_text(
        "2.3|nro|123|3|20261001|20261001|+0000\n"
        "nro|*|asn|*|1|summary\n",
        encoding="utf-8",
    )

    assert validate_source(source, path) == "20261001"


def test_manifest_contains_hashes_and_compatibility(tmp_path: Path) -> None:
    source = SOURCES[0]
    path = tmp_path / source.filename
    path.write_bytes(b"x")
    item = DownloadedFile(
        source=source,
        path=path,
        size_bytes=1,
        sha256="a" * 64,
        last_modified="Thu, 01 Oct 2026 22:00:00 GMT",
        etag=None,
        dataset_date=None,
    )

    manifest = build_manifest([item], "2026-10-02T07:00:00+00:00")

    assert manifest["format"] == BUNDLE_FORMAT
    assert manifest["format_version"] == 1
    assert manifest["compatible_with"]["application"] == "$whoami - Lookup"
    assert manifest["sources"][0]["sha256"] == "a" * 64
