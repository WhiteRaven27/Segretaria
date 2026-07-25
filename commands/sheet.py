import asyncio
import csv
import io
import re
import urllib.request
import urllib.error

# ─────────────────────────────────────────
# Constants
# ─────────────────────────────────────────

# Dimensione massima risposta: 5 MB
_MAX_RESPONSE_BYTES = 5 * 1024 * 1024
# Numero massimo di righe CSV da processare
_MAX_CSV_ROWS = 100

# ─────────────────────────────────────────
# Sheet ID extraction
# ─────────────────────────────────────────

_ID_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9_-]+)")


def extract_sheet_id(url: str) -> str | None:
    m = _ID_RE.search(url)
    return m.group(1) if m else None


def normalize_hex(value: str | None) -> str | None:
    """Validate and normalise a hex colour string. Returns upper-case #RRGGBB or None.
    Accepts #RGB, #RRGGBB, RGB, RRGGBB."""
    if not value:
        return None
    value = value.strip()
    raw = value.lstrip("#")
    if not re.match(r"^(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", raw):
        return None
    if len(raw) == 3:
        raw = "".join(c * 2 for c in raw)
    return f"#{raw.upper()}"


# ─────────────────────────────────────────
# CSV fetch (con limite di dimensione)
# ─────────────────────────────────────────

def _fetch_csv_sync(sheet_id: str) -> str:
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read(_MAX_RESPONSE_BYTES + 1)
            if len(raw) > _MAX_RESPONSE_BYTES:
                raise ValueError(
                    "Il foglio è troppo grande (max 5 MB). "
                    "Riduci il numero di righe o colonne."
                )
            return raw.decode("utf-8")
    except urllib.error.HTTPError as e:
        raise ValueError(
            f"Impossibile accedere al foglio (HTTP {e.code}). "
            "Assicurati che la condivisione sia impostata su "
            "'Chiunque abbia il link può visualizzare'."
        )
    except urllib.error.URLError as e:
        raise ValueError(f"Errore di rete: {e.reason}")


async def fetch_csv(sheet_id: str) -> str:
    """Fetch the first sheet of a Google Spreadsheet as CSV (non-blocking)."""
    return await asyncio.to_thread(_fetch_csv_sync, sheet_id)


# ─────────────────────────────────────────
# Parsing helpers
# ─────────────────────────────────────────

# Words that are labels/headers, not ability names
_SKIP_ABILITA = {
    "", "abilità eroiche", "nome orologio", "  classe", "classe",
    "passive", "pv bar", "pm bar", "pi bar", "testo crisi",
    "vero", "falso", "true", "false", "nome", "lvl", "livello",
    "identità", "origine", "tema", "image url", "pronomi",
}

# Abilità eroiche: exact (row_0idx, col_start_0idx, col_end_0idx inclusive)
# Rows are 0-based (spreadsheet row 10 → index 9)
# Columns: AP=41, AU=46, BJ=61, BO=66
_ABILITA_BLOCKS = [
    (9,  41, 46),   # AP10:AU10
    (17, 41, 46),   # AP18:AU18
    (25, 41, 46),   # AP26:AU26
    (33, 41, 46),   # AP34:AU34
    (19, 61, 66),   # BJ20:BO20
    (26, 61, 66),   # BJ27:BO27
    (33, 61, 66),   # BJ34:BO34
]

# Tema: M8:Q8 → row index 7, cols 12–16
_TEMA_ROW   = 7
_TEMA_START = 12   # M
_TEMA_END   = 16   # Q

# Offset from a CLASSE label to: class name (+2), class level (+8)
_CLASSE_NAME_OFFSET  = 2
_CLASSE_LEVEL_OFFSET = 8


def _cell(grid: list[list[str]], r: int, c: int) -> str:
    try:
        return grid[r][c].strip()
    except (IndexError, TypeError):
        return ""


def _find_value(
    grid: list[list[str]],
    label: str,
    col_offset: int = 2,
    row_offset: int = 0,
    unique_neighbor: str | None = None,
) -> str:
    """
    Find the first cell matching `label` (case-insensitive, stripped).
    Optionally require that the same row also contains `unique_neighbor`.
    Return the cell at (row + row_offset, col + col_offset).
    """
    label_l = label.lower().strip()
    for r, row in enumerate(grid):
        for c, cell in enumerate(row):
            if cell.strip().lower() != label_l:
                continue
            if unique_neighbor:
                row_text = " ".join(row).lower()
                if unique_neighbor.lower() not in row_text:
                    continue
            return _cell(grid, r + row_offset, c + col_offset)
    return ""


def _scan_row_range(grid: list[list[str]], row: int, c_start: int, c_end: int) -> list[str]:
    """Return all non-empty, non-numeric, non-label strings in grid[row][c_start:c_end+1]."""
    if row >= len(grid):
        return []
    results = []
    row_data = grid[row]
    for c in range(c_start, min(c_end + 1, len(row_data))):
        val = row_data[c].strip()
        if not val:
            continue
        if val.lower() in _SKIP_ABILITA:
            continue
        # skip pure numbers and single-char values that are likely checkboxes/flags
        if val.replace(".", "").replace(",", "").isdigit():
            continue
        if len(val) <= 1:
            continue
        results.append(val)
    return results


# ─────────────────────────────────────────
# Main parser
# ─────────────────────────────────────────

def parse_character(csv_text: str) -> dict:
    """
    Parse a Fabula Ultima character sheet exported as CSV.
    Returns a dict with keys: nome, livello, identita, tema, origine,
                               classe, abilita, immagine.
    """
    grid = list(csv.reader(io.StringIO(csv_text)))[:_MAX_CSV_ROWS + 1]

    # ── Simple fields ──────────────────────────────────────
    nome     = _find_value(grid, "NOME",      col_offset=2)
    livello  = _find_value(grid, "LVL",       col_offset=2, unique_neighbor="Identità")
    identita = _find_value(grid, "Identità",  col_offset=3)
    origine  = _find_value(grid, "Origine",   col_offset=2)
    immagine = _find_value(grid, "IMAGE URL", col_offset=3)

    # ── Tema: scan M8:Q8 (row 7, cols 12–16) ──────────────
    tema = ""
    for c in range(_TEMA_START, min(_TEMA_END + 1, len(grid[_TEMA_ROW]) if _TEMA_ROW < len(grid) else 0)):
        val = _cell(grid, _TEMA_ROW, c)
        if val and val.lower() not in _SKIP_ABILITA and not val.replace(".", "").isdigit():
            tema = val
            break

    # ── Classes ────────────────────────────────────────────
    classi = []
    for r, row in enumerate(grid):
        for c, cell in enumerate(row):
            if cell.strip().lower() not in ("classe", "  classe"):
                continue
            class_name  = _cell(grid, r, c + _CLASSE_NAME_OFFSET)
            class_level = _cell(grid, r, c + _CLASSE_LEVEL_OFFSET)
            if not class_name:
                continue
            try:
                if int(class_level) > 0:
                    classi.append(f"{class_name} (Lv.{class_level})")
            except ValueError:
                pass

    classe = ", ".join(classi) if classi else ""

    # ── Abilità eroiche: fixed cell blocks ─────────────────
    abilita_list = []
    seen = set()
    for (row, c_start, c_end) in _ABILITA_BLOCKS:
        for name in _scan_row_range(grid, row, c_start, c_end):
            if name not in seen:
                seen.add(name)
                abilita_list.append(name)

    abilita = "\n".join(abilita_list)

    return {
        "nome":     nome     or "Sconosciuto",
        "identita": identita or "—",
        "tema":     tema     or "—",
        "origine":  origine  or "—",
        "livello":  livello  or "—",
        "classe":   classe   or "—",
        "abilita":  abilita,
        "immagine": immagine or None,
    }
