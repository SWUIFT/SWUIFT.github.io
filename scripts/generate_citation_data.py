#!/usr/bin/env python3
"""Generate website citation data and Markdown from CITATION.cff."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CITATION_PATH = ROOT / "CITATION.cff"
DATA_PATH = ROOT / "_data" / "citation.yml"
MARKDOWN_PATH = ROOT / "docs" / "_generated" / "citation.md"


def _required_string(mapping: dict[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key!r} must be a non-empty string in {CITATION_PATH}")
    return value.strip()


def _bibtex_escape(value: str) -> str:
    return value.replace("\\", r"\\").replace("&", r"\&")


def _author_join(names: list[str]) -> str:
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return f"{', '.join(names[:-1])}, and {names[-1]}"


def _load_citation() -> dict[str, Any]:
    loaded = yaml.safe_load(CITATION_PATH.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{CITATION_PATH} must contain a YAML mapping")
    return loaded


def _build_data(citation: dict[str, Any]) -> dict[str, Any]:
    title = _required_string(citation, "title")
    repository_code = _required_string(citation, "repository-code")
    website = _required_string(citation, "url")
    raw_authors = citation.get("authors")
    if not isinstance(raw_authors, list) or not raw_authors:
        raise ValueError(f"'authors' must be a non-empty list in {CITATION_PATH}")

    authors: list[dict[str, str]] = []
    for index, raw_author in enumerate(raw_authors, start=1):
        if not isinstance(raw_author, dict):
            raise ValueError(f"author {index} must be a mapping")
        given = _required_string(raw_author, "given-names")
        family = _required_string(raw_author, "family-names")
        authors.append(
            {
                "given_names": given,
                "family_names": family,
                "name": f"{given} {family}",
                "affiliation": _required_string(raw_author, "affiliation"),
                "orcid": _required_string(raw_author, "orcid"),
            }
        )

    bibtex_lines = [
        "@software{swuift,",
        "  author = {"
        + " and ".join(
            f"{_bibtex_escape(author['family_names'])}, {_bibtex_escape(author['given_names'])}"
            for author in authors
        )
        + "},",
        f"  title = {{{_bibtex_escape(title)}}},",
        f"  url = {{{website}}}",
    ]
    doi = citation.get("doi")
    if doi is not None:
        if not isinstance(doi, str) or not doi.strip():
            raise ValueError("'doi' must be a non-empty string when present")
        bibtex_lines[-1] += ","
        bibtex_lines.append(f"  doi = {{{doi.strip()}}}")
    bibtex_lines.append("}")

    data: dict[str, Any] = {
        "title": title,
        "repository_code": repository_code,
        "url": website,
        "authors": authors,
        "author_text": _author_join([author["name"] for author in authors]),
        "bibtex": "\n".join(bibtex_lines),
    }
    if doi is not None:
        data["doi"] = doi.strip()
    return data


def _render_data(data: dict[str, Any]) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=1000)


def _render_markdown(data: dict[str, Any]) -> str:
    linked_authors = [f"[{author['name']}]({author['orcid']})" for author in data["authors"]]
    lines = [
        "## How to cite SWUIFT",
        "",
        f"**Authors:** {_author_join(linked_authors)}",
        "",
        f"**Title:** {data['title']}",
        "",
        f"**Project website:** [{data['url']}]({data['url']})",
        "",
    ]
    if "doi" in data:
        lines.extend(
            (
                f"**DOI:** [{data['doi']}](https://doi.org/{data['doi']})",
                "",
            )
        )
    lines.extend(("### BibTeX", "", "```bibtex", data["bibtex"], "```", ""))
    return "\n".join(lines)


def _write_or_check(path: Path, expected: str, *, check: bool) -> None:
    if check:
        if not path.is_file() or path.read_text(encoding="utf-8") != expected:
            raise SystemExit(f"{path} is stale; run {Path(__file__).name}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(expected, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if generated files are stale.")
    args = parser.parse_args()

    data = _build_data(_load_citation())
    _write_or_check(DATA_PATH, _render_data(data), check=args.check)
    _write_or_check(MARKDOWN_PATH, _render_markdown(data), check=args.check)
    action = "Validated" if args.check else "Generated"
    print(f"{action} citation data for {len(data['authors'])} authors.")


if __name__ == "__main__":
    main()
