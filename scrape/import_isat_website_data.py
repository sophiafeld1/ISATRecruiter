"""
Import local ISAT website markdown data into Postgres.

- Each top-level H1 section (`# Heading`) becomes one row in `pages`.
- Links from `data_isat_website/links.txt` are inserted into `urls`
  as (description, url).
"""
import os
import re
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.db_write import LinkDatabase


DATA_DIR = os.path.join(project_root, "data_isat_website")


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug or "section"


def _split_by_h1(md_text: str):
    sections = []
    current_title = None
    current_lines = []
    for line in md_text.splitlines():
        if line.startswith("# "):
            if current_title is not None:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = line[2:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_title is not None:
        sections.append((current_title, "\n".join(current_lines).strip()))
    return sections


def import_markdown_sections(db: LinkDatabase):
    md_files = [
        fn for fn in sorted(os.listdir(DATA_DIR))
        if fn.lower().endswith(".md")
    ]
    total = 0
    for fn in md_files:
        path = os.path.join(DATA_DIR, fn)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        sections = _split_by_h1(text)
        for idx, (title, body) in enumerate(sections, start=1):
            section_text = f"# {title}\n\n{body}".strip()
            page_url = f"local://data_isat_website/{fn}#{idx}-{_slugify(title)}"
            db.upsert_page(url=page_url, text=section_text, links=None)
            total += 1
    print(f"Imported {total} H1 sections into pages.")


def import_links(db: LinkDatabase):
    links_path = os.path.join(DATA_DIR, "links.txt")
    if not os.path.isfile(links_path):
        print("No links.txt found; skipping urls import.")
        return

    with open(links_path, encoding="utf-8") as f:
        lines = [ln.strip() for ln in f.readlines() if ln.strip()]

    total = 0
    i = 0
    while i < len(lines) - 1:
        desc = lines[i].rstrip(":").strip()
        url = lines[i + 1].strip()
        if url.startswith("http://") or url.startswith("https://"):
            db.upsert_url(description=desc, url=url)
            total += 1
            i += 2
        else:
            i += 1
    print(f"Imported {total} links into urls.")


def main():
    db = LinkDatabase()
    try:
        import_markdown_sections(db)
        import_links(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()

