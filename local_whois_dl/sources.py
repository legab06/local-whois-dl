from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RIPE_SPLIT_BASE = "https://ftp.ripe.net/ripe/dbase/split"
NRO_DELEGATED_URL = (
    "https://ftp.ripe.net/pub/stats/ripencc/nro-stats/latest/nro-delegated-stats"
)


@dataclass(frozen=True, slots=True)
class Source:
    key: str
    label: str
    filename: str
    url: str
    kind: Literal["gzip", "nro"]
    max_bytes: int


_MIB = 1024 * 1024

SOURCES: tuple[Source, ...] = (
    Source(
        key="ripe_organisation",
        label="RIPE organisations",
        filename="ripe.db.organisation.gz",
        url=f"{RIPE_SPLIT_BASE}/ripe.db.organisation.gz",
        kind="gzip",
        max_bytes=100 * _MIB,
    ),
    Source(
        key="ripe_aut_num",
        label="RIPE ASN",
        filename="ripe.db.aut-num.gz",
        url=f"{RIPE_SPLIT_BASE}/ripe.db.aut-num.gz",
        kind="gzip",
        max_bytes=100 * _MIB,
    ),
    Source(
        key="ripe_inetnum",
        label="RIPE réseaux IPv4",
        filename="ripe.db.inetnum.gz",
        url=f"{RIPE_SPLIT_BASE}/ripe.db.inetnum.gz",
        kind="gzip",
        max_bytes=600 * _MIB,
    ),
    Source(
        key="ripe_inet6num",
        label="RIPE réseaux IPv6",
        filename="ripe.db.inet6num.gz",
        url=f"{RIPE_SPLIT_BASE}/ripe.db.inet6num.gz",
        kind="gzip",
        max_bytes=250 * _MIB,
    ),
    Source(
        key="ripe_route",
        label="RIPE routes IPv4",
        filename="ripe.db.route.gz",
        url=f"{RIPE_SPLIT_BASE}/ripe.db.route.gz",
        kind="gzip",
        max_bytes=150 * _MIB,
    ),
    Source(
        key="ripe_route6",
        label="RIPE routes IPv6",
        filename="ripe.db.route6.gz",
        url=f"{RIPE_SPLIT_BASE}/ripe.db.route6.gz",
        kind="gzip",
        max_bytes=100 * _MIB,
    ),
    Source(
        key="nro_delegated",
        label="NRO couverture mondiale",
        filename="nro-delegated-stats",
        url=NRO_DELEGATED_URL,
        kind="nro",
        max_bytes=250 * _MIB,
    ),
)

ALLOWED_DOWNLOAD_HOSTS = frozenset({"ftp.ripe.net"})
