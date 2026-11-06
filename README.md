# bookstack-sync

Downloads every book of a BookStack instance visible to your account and converts it to Markdown. Uses the website (not the API) with your session cookie.

## Setup

```
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit BOOKSTACK_URL
```

## Usage

```
python3 bookstack_sync.py            # writes to OUTPUT_DIR (default ./output)
python3 bookstack_sync.py ./other    # explicit output folder
```

If `BOOKSTACK_COOKIE` is empty you are prompted for it. To get it: logged-in browser, dev tools, storage tab, `bookstack_session` cookie.

## Notes

- One folder per book (named after the URL slug), one subfolder per chapter, one `NN-slug.md` file per page.
- Existing files are overwritten: sync into a dedicated folder, then compare with your notes.
- The HTML selectors (`.page-list`, `#show-page-content`, ...) may need tweaks depending on the instance theme.
- `.env` and `output/` are git-ignored. Never commit a cookie.
