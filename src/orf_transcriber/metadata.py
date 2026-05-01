"""Scrape lightweight metadata (title, description, date) from an ORF ON page.

orfondl itself doesn't expose this, but the public page has Open Graph and
JSON-LD tags we can read. This is best-effort — failures degrade to "Unknown".
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime

import requests
from bs4 import BeautifulSoup


@dataclass
class VideoMeta:
    title: str = "Unbekannter Titel"
    description: str = ""
    published: str = ""
    canonical_url: str = ""


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "de-AT,de;q=0.9,en;q=0.5",
}


def _format_date(raw: str) -> str:
    if not raw:
        return ""
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return raw


def fetch(url: str, timeout: float = 10.0) -> VideoMeta:
    meta = VideoMeta(canonical_url=url)
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException:
        return meta

    soup = BeautifulSoup(resp.text, "html.parser")

    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        meta.title = og_title["content"].strip()

    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        meta.description = og_desc["content"].strip()

    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href"):
        meta.canonical_url = canonical["href"].strip()

    for tag in soup.find_all("script", type="application/ld+json"):
        if not tag.string:
            continue
        try:
            data = json.loads(tag.string)
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            if not meta.title or meta.title == "Unbekannter Titel":
                if isinstance(item.get("name"), str):
                    meta.title = item["name"].strip()
            if not meta.description and isinstance(item.get("description"), str):
                meta.description = item["description"].strip()
            for key in ("uploadDate", "datePublished"):
                if isinstance(item.get(key), str):
                    meta.published = _format_date(item[key])
                    break

    return meta


_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_filename(title: str, fallback: str = "ORF-Video", max_len: int = 80) -> str:
    cleaned = _SAFE_RE.sub("_", title.strip()).strip("._-")
    if not cleaned:
        cleaned = fallback
    return cleaned[:max_len]
