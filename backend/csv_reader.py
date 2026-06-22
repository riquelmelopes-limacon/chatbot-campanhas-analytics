"""
csv_reader.py — Lê e interpreta o CSV exportado do Adobe Analytics Workspace.

Formato real do Adobe Analytics (confirmado com arquivo real):
  - Linhas com # são comentários/metadados
  - Cabeçalho: primeira célula vazia + nomes das métricas
  - 1ª linha de dados: SEMPRE os totais (nome = nome da dimensão, ex: "Nome Da Feature (v141)")
  - Demais linhas: uma feature por linha
  - Conversão: decimal bruto (0.009305 = 0.93%), precisa × 100
  - "Infinity": aceites > 0 com impressões = 0 → linha ignorada
"""

import csv
import io
import re
from pathlib import Path


# =============================================================================
# MAPEAMENTO DE COLUNAS
# =============================================================================
COLUMN_MAP = {
    "feature": [
        "nome da feature", "feature", "features",
        "hour of day", "hora do dia",
        "dimensão", "nome", "segment", "segmento", "page", "evar",
    ],
    "impressions": [
        "modulo de engajamento | impressoes",
        "modulo de engajamento | impressões",
        "impressoes", "impressões", "impressions",
    ],
    "accepts": [
        "modulo de engajamento | aceites/sucesso",
        "modulo de engajamento | aceites",
        "aceites/sucesso", "aceites", "accepts",
    ],
    "conversion": [
        "tx conversão - módulo",
        "tx conversao - modulo",
        "tx conversão", "tx conversao",
        "conversão", "conversao", "conversion rate", "taxa de conversão",
    ],
}

# Valores de dimensão que devem ser sempre excluídos do report
EXCLUDE_NAMES = {
    "unspecified", "nao especificado", "não especificado", "(not set)", "none",
}


def _find_header_row(lines: list) -> int:
    """
    Encontra a linha de cabeçalho das métricas.
    No CSV real do Adobe, é a linha com primeira célula vazia e métricas nas demais.
    """
    for i, line in enumerate(lines):
        if line.startswith("#") or not line.strip():
            continue
        try:
            cols = next(csv.reader([line]))
        except Exception:
            continue
        if len(cols) >= 3 and cols[0].strip() == "":
            non_empty = [c.strip() for c in cols[1:] if c.strip()]
            if len(non_empty) >= 2:
                return i
    return 0


def _normalize(text: str) -> str:
    import unicodedata
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _detect_columns(headers: list) -> dict:
    col_indices = {}
    for idx, header in enumerate(headers):
        normalized = _normalize(header)
        for key, possible_names in COLUMN_MAP.items():
            if key not in col_indices:
                for name in possible_names:
                    if _normalize(name) in normalized or normalized in _normalize(name):
                        col_indices[key] = idx
                        break
    return col_indices


def _parse_conversion(value: str) -> float | None:
    """
    Converte o valor de conversão para percentual (0–100).

    Adobe exporta como decimal bruto: 0.009305 → 0.93%
    Também pode vir como string "%": "0.93%" → 0.93
    "Infinity" → None (linha ignorada: aceites sem impressões)
    """
    value = value.strip()
    if not value or value.lower() in ("infinity", "inf", "-", ""):
        return None

    is_percent_string = "%" in value
    cleaned = re.sub(r"[^\d.,]", "", value)
    if not cleaned:
        return 0.0

    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned and len(cleaned) - cleaned.index(",") <= 3:
        cleaned = cleaned.replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")

    try:
        val = float(cleaned)
    except ValueError:
        return 0.0

    if is_percent_string:
        return round(val, 4)
    elif val <= 1.5:
        # Decimal bruto (ex: 0.009305) → converte para %
        return round(val * 100, 4)
    else:
        return round(val, 4)


def _parse_int(value: str) -> int:
    cleaned = re.sub(r"[^\d]", "", value)
    return int(cleaned) if cleaned else 0


def read_csv(filepath) -> list:
    """
    Lê o CSV do Adobe Analytics e retorna lista de features com métricas.

    Retorna:
        [{"name": "MOSAIC", "impressions": 5541, "accepts": 31, "conversion": 0.56}, ...]

    Exclui automaticamente:
        - 1ª linha de dados (totais do painel)
        - "Unspecified" e similares
        - Linhas com "Infinity" na conversão (impressões = 0)
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")

    content = None
    for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            content = filepath.read_text(encoding=encoding)
            break
        except UnicodeDecodeError:
            continue

    if content is None:
        raise ValueError("Não foi possível ler o arquivo.")

    lines = content.splitlines()
    header_row_idx = _find_header_row(lines)
    data_lines = lines[header_row_idx:]

    reader = csv.reader(io.StringIO("\n".join(data_lines)))
    rows = list(reader)

    if not rows:
        raise ValueError("CSV vazio ou sem dados reconhecíveis.")

    # Substitui célula vazia do cabeçalho por "feature"
    raw_headers = [h.strip() for h in rows[0]]
    headers = raw_headers[:]
    if headers[0] == "":
        headers[0] = "feature"

    col_indices = _detect_columns(headers)

    missing = [k for k in ("impressions", "accepts") if k not in col_indices]
    if missing:
        raise ValueError(
            f"Colunas não encontradas: {missing}\n"
            f"Cabeçalhos detectados: {raw_headers}\n"
            f"Ajuste o COLUMN_MAP em csv_reader.py."
        )

    has_conversion = "conversion" in col_indices
    has_feature    = "feature" in col_indices

    features = []
    totals_skipped = False  # A 1ª linha com dados reais é sempre os totais no Adobe

    for row in rows[1:]:
        if not any(cell.strip() for cell in row):
            continue

        # Pula sub-cabeçalhos extras (alguns exports têm 2 linhas de cabeçalho)
        if row[0].strip() == "":
            continue

        # Pula a 1ª linha de dados reais (totais do painel)
        if not totals_skipped:
            totals_skipped = True
            continue

        try:
            name = row[col_indices["feature"]].strip() if has_feature else f"Item {len(features)+1}"

            # Pula Unspecified e similares
            if _normalize(name) in EXCLUDE_NAMES:
                continue

            impressions = _parse_int(row[col_indices["impressions"]])
            accepts     = _parse_int(row[col_indices["accepts"]])

            if has_conversion:
                conversion = _parse_conversion(row[col_indices["conversion"]])
                # None = "Infinity" (aceites sem impressões) — mantém no ranking
                if conversion is None:
                    conversion = float("inf")
            else:
                conversion = round((accepts / impressions * 100), 4) if impressions > 0 else 0.0

            if name:
                features.append({
                    "name":        name,
                    "impressions": impressions,
                    "accepts":     accepts,
                    "conversion":  conversion,
                })
        except (IndexError, ValueError):
            continue

    return features
