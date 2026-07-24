import asyncio
import csv
import io
import re
import urllib.request
import urllib.error

# ─────────────────────────────────────────
# Sheet ID extraction
# ─────────────────────────────────────────

_ID_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9_-]+)")


def extract_sheet_id(url: str) -> str | None:
    m = _ID_RE.search(url)
    return m.group(1) if m else None


# ─────────────────────────────────────────
# CSV fetch
# ─────────────────────────────────────────

def _fetch_csv_sync(sheet_id: str) -> str:
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8")
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

# Labels that appear in the abilità column but are section headers, not abilities
_SKIP_ABILITA = {
    "", "abilità eroiche", "nome orologio", "  classe", "classe",
    "passive", "pv bar", "pm bar", "pi bar", "testo crisi",
    "vero", "falso", "true", "false",
}

# Column indices (0-based) in the CSV
_ABILITA_NAME_COL = 41   # column AP
_ABILITA_COUNT_COL = 46  # column AU

# Offset from a CLASSE label cell to: class name (+2), class level (+8)
_CLASSE_NAME_OFFSET = 2
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


# ─────────────────────────────────────────
# Main parser
# ─────────────────────────────────────────

def parse_character(csv_text: str) -> dict:
    """
    Parse a Fabula Ultima character sheet exported as CSV.
    Returns a dict with keys: nome, livello, identita, tema, origine,
                               classe, abilita, immagine.
    """
    grid = list(csv.reader(io.StringIO(csv_text)))

    # ── Simple fields ──────────────────────────────────────
    nome     = _find_value(grid, "NOME",      col_offset=2)
    livello  = _find_value(grid, "LVL",       col_offset=2, unique_neighbor="Identità")
    identita = _find_value(grid, "Identità",  col_offset=3)
    tema     = _find_value(grid, "Tema",      col_offset=2)
    origine  = _find_value(grid, "Origine",   col_offset=2)
    immagine = _find_value(grid, "IMAGE URL", col_offset=3)

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

    # ── Abilità eroiche ────────────────────────────────────
    abilita_list = []
    for r, row in enumerate(grid):
        if len(row) <= _ABILITA_NAME_COL:
            continue
        name = row[_ABILITA_NAME_COL].strip()
        if not name or name.lower() in _SKIP_ABILITA:
            continue
        count_raw = _cell(grid, r, _ABILITA_COUNT_COL)
        try:
            if int(count_raw) > 0:
                abilita_list.append(f"{name} (x{count_raw})")
        except ValueError:
            pass

    abilita = "\n".join(abilita_list)

    return {
        "nome":     nome     or "Sconosciuto",
        "livello":  livello  or "—",
        "identita": identita or "—",
        "tema":     tema     or "—",
        "origine":  origine  or "—",
        "classe":   classe   or "—",
        "abilita":  abilita,
        "immagine": immagine or None,
    }
