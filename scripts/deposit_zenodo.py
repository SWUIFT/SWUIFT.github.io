#!/usr/bin/env python3
"""Publish a new version of the existing SWUIFT Zenodo record.

Creates a new version of concept 10.5281/zenodo.22184758. Never POSTs to
/api/deposit/depositions without /actions/, which would mint a second concept DOI.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

HOST = "https://zenodo.org"
CONCEPT_ID = "22184758"
LICENSE_KEYS = frozenset({"license"})
DOI_KEYS = frozenset({"doi", "prereserve_doi"})


def _headers(token: str, content_type: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if content_type is not None:
        headers["Content-Type"] = content_type
    return headers


def _request(
    method: str,
    url: str,
    *,
    token: str | None = None,
    data: bytes | None = None,
    content_type: str | None = None,
) -> Any:
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers=_headers(token, content_type) if token else {},
    )
    try:
        with urllib.request.urlopen(request) as response:
            body = response.read()
            if not body:
                return None
            if "json" in (response.headers.get_content_type() or ""):
                return json.loads(body.decode())
            return body
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise SystemExit(f"{method} {url} failed: HTTP {error.code}\n{detail}") from error


def _load_metadata(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    for key in LICENSE_KEYS:
        if key in loaded:
            raise SystemExit(f"{path} must not contain {key!r}; license fields are frozen")
    for related in loaded.get("related_identifiers") or []:
        if not isinstance(related, dict):
            continue
        relation = str(related.get("relation", "")).lower()
        identifier = str(related.get("identifier", ""))
        if relation == "isversionof" and CONCEPT_ID in identifier:
            raise SystemExit("refusing to hand-write IsVersionOf for the concept DOI")
        if "utkrshkmr/SWUIFT" in identifier:
            raise SystemExit("stale repository URL still present in related_identifiers")
    return loaded


def _preserved_license(draft_metadata: dict[str, Any]) -> str | None:
    license_field = draft_metadata.get("license")
    if isinstance(license_field, str) and license_field.strip():
        return license_field.strip()
    if isinstance(license_field, dict):
        license_id = license_field.get("id")
        if isinstance(license_id, str) and license_id.strip():
            return license_id.strip()
    return None


def _creators_without_affiliations(creators: Any) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    if not isinstance(creators, list):
        raise SystemExit("creators must be a list")
    for creator in creators:
        if not isinstance(creator, dict):
            raise SystemExit("each creator must be an object")
        entry = {key: value for key, value in creator.items() if key != "affiliation"}
        cleaned.append(entry)
    return cleaned


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, default=Path(".zenodo.json"))
    parser.add_argument("--concept-id", default=CONCEPT_ID)
    parser.add_argument("--file", type=Path, required=True, help="archive to upload")
    args = parser.parse_args()

    token = os.environ.get("ZENODO_ACCESS_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "ZENODO_ACCESS_TOKEN is empty. Add the repository secret, with "
            "deposit:write and deposit:actions, then re-run."
        )
    if args.concept_id != CONCEPT_ID:
        raise SystemExit(f"refusing concept id {args.concept_id!r}; expected {CONCEPT_ID}")
    archive = args.file if args.file.is_absolute() else Path.cwd() / args.file
    if not archive.is_file():
        raise SystemExit(f"upload file does not exist: {archive}")

    metadata = _load_metadata(args.metadata)
    metadata["creators"] = _creators_without_affiliations(metadata.get("creators"))
    metadata.pop("notes", None)

    latest = _request("GET", f"{HOST}/api/records/{args.concept_id}")
    if not isinstance(latest, dict) or "id" not in latest:
        raise SystemExit("could not resolve the latest published version of the concept record")
    latest_id = latest["id"]
    print(f"Latest published version id: {latest_id}")

    newversion = _request(
        "POST",
        f"{HOST}/api/deposit/depositions/{latest_id}/actions/newversion",
        token=token,
    )
    if not isinstance(newversion, dict):
        raise SystemExit("newversion response was not JSON")
    draft_url = newversion.get("links", {}).get("latest_draft")
    if not isinstance(draft_url, str) or not draft_url:
        raise SystemExit("newversion response missing links.latest_draft")

    draft = _request("GET", draft_url, token=token)
    if not isinstance(draft, dict):
        raise SystemExit("draft GET was not JSON")
    draft_metadata = draft.get("metadata")
    if not isinstance(draft_metadata, dict):
        raise SystemExit("draft metadata missing")

    license_id = _preserved_license(draft_metadata)
    payload_metadata = {
        key: value for key, value in metadata.items() if key not in LICENSE_KEYS | DOI_KEYS
    }
    if license_id is not None:
        payload_metadata["license"] = license_id

    updated = _request(
        "PUT",
        draft_url,
        token=token,
        data=json.dumps({"metadata": payload_metadata}).encode(),
        content_type="application/json",
    )
    if not isinstance(updated, dict):
        raise SystemExit("metadata PUT was not JSON")

    draft = _request("GET", draft_url, token=token)
    if not isinstance(draft, dict):
        raise SystemExit("draft GET after metadata PUT was not JSON")

    files = draft.get("files")
    if isinstance(files, list):
        for deposited in files:
            if not isinstance(deposited, dict):
                continue
            file_links = deposited.get("links")
            file_url = file_links.get("self") if isinstance(file_links, dict) else None
            if isinstance(file_url, str) and file_url:
                _request("DELETE", file_url, token=token)

    links = draft.get("links")
    if not isinstance(links, dict):
        raise SystemExit("draft missing links")
    bucket = links.get("bucket")
    if not isinstance(bucket, str) or not bucket:
        raise SystemExit("draft missing links.bucket")
    encoded_name = urllib.parse.quote(archive.name)
    with archive.open("rb") as stream:
        _request(
            "PUT",
            f"{bucket}/{encoded_name}",
            token=token,
            data=stream.read(),
            content_type="application/octet-stream",
        )

    publish_url = links.get("publish")
    if not isinstance(publish_url, str) or not publish_url:
        publish_url = f"{draft_url.rstrip('/')}/actions/publish"
    published = _request("POST", publish_url, token=token)
    if not isinstance(published, dict):
        raise SystemExit("publish response was not JSON")
    published_metadata = published.get("metadata")
    doi = published.get("doi")
    if not doi and isinstance(published_metadata, dict):
        doi = published_metadata.get("doi")
    print(f"Published Zenodo version DOI: {doi}")
    print(f"Concept DOI remains 10.5281/zenodo.{CONCEPT_ID}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
