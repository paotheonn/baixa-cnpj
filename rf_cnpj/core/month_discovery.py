"""Discovery of available RF CNPJ months."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import requests

from .downloader import NEXTCLOUD_SHARE_TOKEN, NEXTCLOUD_WEBDAV_URL

MONTH_RE = re.compile(r"(\d{4})-(\d{2})/?$")


def is_valid_month(value: str) -> bool:
    match = re.fullmatch(r"\d{4}-\d{2}", value)
    if not match:
        return False
    month = int(value[-2:])
    return 1 <= month <= 12


def parse_months_from_webdav(xml_content: bytes) -> list[str]:
    root = ET.fromstring(xml_content)
    namespaces = {"d": "DAV:"}
    months: set[str] = set()

    for response in root.findall(".//d:response", namespaces):
        href = response.find("d:href", namespaces)
        if href is None or href.text is None:
            continue
        match = MONTH_RE.search(href.text)
        if not match:
            continue
        month = f"{match.group(1)}-{match.group(2)}"
        if is_valid_month(month):
            months.add(month)
    return sorted(months)


class MonthDiscovery:
    """Queries the Receita Federal WebDAV share for available months."""

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()

    def fetch_available_months(self) -> list[str]:
        response = self.session.request(
            "PROPFIND",
            NEXTCLOUD_WEBDAV_URL,
            auth=(NEXTCLOUD_SHARE_TOKEN, ""),
            headers={"Depth": "1"},
            timeout=30,
        )
        response.raise_for_status()
        return parse_months_from_webdav(response.content)

    def latest_month(self) -> str | None:
        months = self.fetch_available_months()
        return months[-1] if months else None
