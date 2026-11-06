#!/usr/bin/env python3
"""Download every BookStack book visible to an account as Markdown.

Uses the regular website with an already logged-in session cookie.
Config (env vars or .env, see .env.example): BOOKSTACK_URL, BOOKSTACK_COOKIE, OUTPUT_DIR.

Usage: python3 bookstack_sync.py [output_dir]
"""
import getpass
import os
import re
import sys
import time

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from markdownify import markdownify as html_to_md

load_dotenv()

BASE_URL = os.environ.get("BOOKSTACK_URL", "").rstrip("/")
if not BASE_URL:
    raise SystemExit("BOOKSTACK_URL is missing, see .env.example")

raw_cookie = os.environ.get("BOOKSTACK_COOKIE", "").strip() or getpass.getpass(
    "Session cookie ('bookstack_session=xxxx' or just the value): "
).strip()
COOKIE_HEADER = raw_cookie if "=" in raw_cookie else f"bookstack_session={raw_cookie}"

SESSION = requests.Session()
SESSION.headers.update({"Cookie": COOKIE_HEADER, "User-Agent": "Mozilla/5.0"})

# Matches /books/<slug> only, not /books, /books/create or page links
BOOK_HREF = re.compile(r"^(?:https?://[^/]+)?/books/([^/?#]+)/?$")


def full_url(path_or_url):
    if path_or_url.startswith(("http://", "https://")):
        return path_or_url
    return f"{BASE_URL}{path_or_url}"


def get_soup(path):
    r = SESSION.get(full_url(path), timeout=30)
    r.raise_for_status()
    if "login" in r.url:
        raise SystemExit("Redirected to the login page: the session cookie is invalid or expired.")
    return BeautifulSoup(r.text, "html.parser")


def slugify(name):
    name = re.sub(r"[^a-z0-9]+", "-", name.strip().lower())
    return name.strip("-") or "untitled"


def list_books():
    """Return [(slug, href)] for all books, following pagination."""
    books = {}
    page = 1
    while True:
        soup = get_soup("/books" if page == 1 else f"/books?page={page}")
        added = 0
        for a in soup.select("a[href*='/books/']"):
            href = a.get("href", "")
            m = BOOK_HREF.match(href)
            if not m or m.group(1) == "create" or href in books:
                continue
            books[href] = m.group(1)
            added += 1
        if not added:
            break
        page += 1
        time.sleep(0.2)
    return [(slug, href) for href, slug in books.items()]


def list_pages(book_href):
    """Return [(chapter_name or None, page_href)] for a book."""
    soup = get_soup(book_href)
    results = []
    for chapter in soup.select(".page-list .chapter, .book-contents > .chapter"):
        title = chapter.select_one(".chapter-title, h4")
        title = title.get_text(strip=True) if title else None
        for a in chapter.select("a[href*='/page/']"):
            results.append((title, a["href"]))
    for a in soup.select(".page-list > a[href*='/page/'], .book-contents > a[href*='/page/']"):
        results.append((None, a["href"]))
    return results


def save_page(href, out_dir, index):
    # Markdown export may be disabled, so convert the rendered page ourselves
    url = full_url(href)
    r = SESSION.get(url, timeout=30)
    r.raise_for_status()

    content = BeautifulSoup(r.text, "html.parser").select_one(
        "#show-page-content, .page-content, .content-wrap"
    )
    if content is None:
        print(f"  !! {url}: page content not found, skipped")
        return

    name = slugify(href.rstrip("/").split("/")[-1])
    path = os.path.join(out_dir, f"{index:02d}-{name}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_to_md(str(content), heading_style="ATX"))
    print(f"  -> {path}")
    time.sleep(0.2)


def main():
    if len(sys.argv) > 2:
        print(__doc__)
        sys.exit(1)

    out_root = sys.argv[1] if len(sys.argv) == 2 else os.environ.get("OUTPUT_DIR", "./output")
    os.makedirs(out_root, exist_ok=True)

    books = list_books()
    print(f"{len(books)} book(s) found.")

    for slug, book_href in books:
        print(f"Book: {slug}")
        book_dir = os.path.join(out_root, slugify(slug))
        os.makedirs(book_dir, exist_ok=True)

        chapter_counts = {}
        for idx, (chapter, page_href) in enumerate(list_pages(book_href), start=1):
            if chapter:
                chapter_dir = os.path.join(book_dir, slugify(chapter))
                os.makedirs(chapter_dir, exist_ok=True)
                chapter_counts[chapter] = chapter_counts.get(chapter, 0) + 1
                save_page(page_href, chapter_dir, chapter_counts[chapter])
            else:
                save_page(page_href, book_dir, idx)

    print("\nDone. Existing files were overwritten, compare with your notes before merging.")


if __name__ == "__main__":
    main()
