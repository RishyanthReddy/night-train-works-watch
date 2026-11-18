"""Bounded HTTPS transport for explicitly selected provider endpoints."""

import gzip
from http.client import HTTPSConnection, HTTPException
from io import BytesIO
import os
from urllib.parse import urlsplit
from xml.etree import ElementTree
import zlib


def credential(name):
    value = os.environ.get(name)
    if value is None or not value or any(not 33 <= ord(char) <= 126 for char in value):
        raise ValueError(f"{name}_missing_or_invalid")
    return value


def read_one(url, allowed_hosts, *, headers=None, limit, allow_redirect=False):
    target = urlsplit(url)
    if (target.scheme != "https" or target.netloc not in allowed_hosts
            or target.fragment or not target.path.startswith("/")):
        raise ValueError("provider_url_not_allowed")
    path = target.path + ("?" + target.query if target.query else "")
    connection = HTTPSConnection(target.hostname, timeout=45)
    try:
        connection.request("GET", path, headers={"Accept-Encoding": "gzip", **(headers or {})})
        response = connection.getresponse()
        if allow_redirect and response.status in (301, 302, 303, 307, 308):
            location = response.getheader("Location")
            if not location:
                raise ValueError("provider_redirect_missing_location")
            return None, location
        if response.status != 200:
            raise ValueError(f"provider_http_{response.status}")
        content_encoding = (response.getheader("Content-Encoding") or "").strip().lower()
        raw = response.read(limit + 1)
    except (HTTPException, OSError):
        raise ValueError("provider_transport_failed") from None
    finally:
        connection.close()
    if len(raw) > limit:
        raise ValueError("provider_response_too_large")
    if content_encoding == "gzip" or (not content_encoding and raw.startswith(b"\x1f\x8b")):
        try:
            with gzip.GzipFile(fileobj=BytesIO(raw)) as compressed:
                raw = compressed.read(limit + 1)
        except (OSError, EOFError, zlib.error):
            raise ValueError("provider_invalid_gzip") from None
    elif content_encoding not in ("", "identity"):
        raise ValueError("provider_content_encoding_unsupported")
    if len(raw) > limit:
        raise ValueError("provider_response_too_large")
    return raw, None


def check_xml(raw):
    """The supported provider documents use UTF-8 and no entity declarations."""
    if b"\0" in raw or b"<!DOCTYPE" in raw or b"<!ENTITY" in raw:
        raise ValueError("provider_xml_declaration_not_allowed")


def parse_xml(raw):
    check_xml(raw)
    try:
        return ElementTree.fromstring(raw)
    except (ElementTree.ParseError, LookupError):
        raise ValueError("provider_xml_invalid") from None
