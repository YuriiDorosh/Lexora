#!/usr/bin/env python3
"""
Diagnostic script for Anki .apkg files.

Usage (from the host):
    docker cp /path/to/deck.apkg anki_service:/tmp/deck.apkg
    docker exec anki_service python3 /app/diag_apkg.py /tmp/deck.apkg

Prints:
  - All files in the zip with sizes and magic bytes
  - For each .anki2 / .anki21 file: whether it is SQLite or Zstd-compressed
  - If SQLite: all table names, row count of `notes`, and the first 5 `flds` values
  - Contents of `col.models` (truncated)
"""

import json
import os
import sqlite3
import sys
import tempfile
import zipfile

ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
SQLITE_MAGIC = b"SQLite format 3\x00"


def magic_label(data: bytes) -> str:
    if data[:4] == ZSTD_MAGIC:
        return "ZSTD-COMPRESSED"
    if data[:16] == SQLITE_MAGIC:
        return "SQLite"
    return f"UNKNOWN ({data[:8].hex()})"


def probe_sqlite(data: bytes, label: str):
    """Try to open `data` as a SQLite database and print schema info."""
    if data[:4] == ZSTD_MAGIC:
        print(f"  → {label}: Zstd-compressed. Attempting decompression...")
        try:
            import zstandard

            data = zstandard.ZstdDecompressor().decompress(data, max_output_size=512 * 1024 * 1024)
            print(f"    Decompressed OK → {len(data):,} bytes  magic={data[:4].hex()}")
        except ImportError:
            print("    ✗ zstandard package not installed — cannot decompress")
            print("      Install with: pip install zstandard")
            return
        except Exception as exc:
            print(f"    ✗ Decompression failed: {exc}")
            return

    if data[:16] != SQLITE_MAGIC:
        print(f"  → {label}: NOT a SQLite file after decompression — magic={data[:8].hex()}")
        return

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        conn = sqlite3.connect(tmp_path)
        cur = conn.cursor()

        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]
        print(f"  → {label}: valid SQLite — tables: {tables}")

        if "notes" in tables:
            cur.execute("SELECT COUNT(*) FROM notes")
            count = cur.fetchone()[0]
            print(f"    notes row count: {count}")

            cur.execute("SELECT flds FROM notes LIMIT 5")
            for i, (flds,) in enumerate(cur.fetchall(), 1):
                preview = flds[:120].replace("\x1f", " | ")
                print(f"    row {i}: {preview!r}")
        else:
            print("    notes table NOT FOUND")

        if "col" in tables:
            cur.execute("SELECT models FROM col LIMIT 1")
            row = cur.fetchone()
            if row:
                try:
                    models = json.loads(row[0])
                    for mid, m in models.items():
                        flds = [f["name"] for f in m.get("flds", [])]
                        print(f'    col.models[{mid}] name={m.get("name")!r} fields={flds}')
                except Exception as exc:
                    print(f"    col.models parse error: {exc}  raw={str(row[0])[:200]}")

        conn.close()
    except Exception as exc:
        print(f"  → {label}: SQLite error: {exc}")
    finally:
        os.unlink(tmp_path)


def main(apkg_path: str):
    print(f"\n=== Anki .apkg diagnostic: {apkg_path} ===\n")
    print(f"File size: {os.path.getsize(apkg_path):,} bytes\n")

    try:
        with zipfile.ZipFile(apkg_path, "r") as zf:
            names = zf.namelist()
            print(f"Zip contents ({len(names)} entries):")
            for name in sorted(names):
                info = zf.getinfo(name)
                data_preview = zf.read(name, pwd=None)[:8] if info.file_size < 10_000_000 else b""
                magic = magic_label(data_preview) if data_preview else "(too large to preview)"
                print(f"  {name:<40} {info.file_size:>12,} bytes  [{magic}]")

            print()
            # --- Probe DB files ---
            for db_name in ("collection.anki21", "collection.anki2", "collection.anki21b"):
                if db_name in names:
                    data = zf.read(db_name)
                    probe_sqlite(data, db_name)
                    print()

            # --- Media map ---
            if "media" in names:
                try:
                    media = json.loads(zf.read("media").decode("utf-8"))
                    print(f"media map: {len(media)} entries")
                    for k, v in list(media.items())[:5]:
                        print(f"  {k} → {v}")
                    if len(media) > 5:
                        print(f"  ... and {len(media) - 5} more")
                except Exception as exc:
                    print(f"media map parse error: {exc}")

    except zipfile.BadZipFile as exc:
        print(f"✗ Not a valid zip: {exc}")

    print("\n=== End diagnostic ===\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} /path/to/deck.apkg")
        sys.exit(1)
    main(sys.argv[1])
