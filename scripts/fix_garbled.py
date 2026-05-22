"""Fix remaining garbled text in UI files."""
import pathlib

BASE = pathlib.Path("src/midas/ui")

# Each entry: (rel_path, old_bytes, new_bytes)
FIXES: list[tuple[str, bytes, bytes]] = [
    # watchlist_page.py — PUA char after 確認刪除 in dialog title
    (
        "pages/watchlist_page.py",
        b"\xe7\xa2\xba\xe8\xaa\x8d\xe5\x88\xaa\xe9\x99\xa4\xee\xa8\x92",
        "確認刪除".encode("utf-8"),
    ),
]

for rel, old, new in FIXES:
    path = BASE / rel
    raw = path.read_bytes()
    if old in raw:
        path.write_bytes(raw.replace(old, new))
        print(f"Fixed {rel}")
    else:
        print(f"NOT FOUND in {rel}: {old!r}")
        idx = raw.find(b"askyesno")
        if idx >= 0:
            print(f"  Context: {raw[idx:idx+120]!r}")
