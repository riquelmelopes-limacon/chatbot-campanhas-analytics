"""
ticket_reader.py — Lê o CSV de Faixa de Preço e calcula o ticket médio do dia.

Estrutura do CSV:
    Coluna 0: Faixa Preço (v141) → valor do preço (ex: 6.99, 8.99...)
    Coluna 1: Aceites/Sucesso    → quantas vendas ocorreram naquele preço

Cálculo: média ponderada = Σ(preço × aceites) / Σ(aceites)
Isso garante que um preço com 20 vendas pese mais que um com 1 venda.
"""

import csv
import io
import re
from pathlib import Path


# Valores de dimensão que devem ser ignorados no cálculo
EXCLUDE_NAMES = {"unspecified", "nao especificado", "não especificado", "(not set)", "none"}


def _find_header_row(lines: list) -> int:
    """Encontra a linha de cabeçalho (primeira célula vazia + métrica)."""
    for i, line in enumerate(lines):
        if line.startswith("#") or not line.strip():
            continue
        try:
            cols = next(csv.reader([line]))
        except Exception:
            continue
        if len(cols) >= 2 and cols[0].strip() == "":
            if cols[1].strip():
                return i
    return 0


def _parse_price(value: str) -> float | None:
    """Converte string de preço para float. Retorna None se não for número."""
    value = value.strip().replace(",", ".")
    cleaned = re.sub(r"[^\d.]", "", value)
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def _parse_int(value: str) -> int:
    cleaned = re.sub(r"[^\d]", "", value)
    return int(cleaned) if cleaned else 0


def read_ticket_csv(filepath) -> dict:
    """
    Lê o CSV de faixa de preço e retorna o ticket médio ponderado.

    Retorna dict:
        {
            "average_ticket": 7.43,       # média ponderada
            "total_accepts":  130,         # total de aceites
            "total_revenue":  965.90,      # receita estimada do dia
            "price_breakdown": [           # detalhamento por faixa
                {"price": 6.99, "accepts": 20},
                ...
            ]
        }
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

    # Pula cabeçalho e linha de totais (1ª linha de dados)
    data_rows = rows[2:]

    price_breakdown = []
    total_weighted = 0.0
    total_accepts  = 0

    for row in data_rows:
        if not any(cell.strip() for cell in row):
            continue

        name = row[0].strip() if row else ""

        # Pula Unspecified e similares
        if name.lower() in EXCLUDE_NAMES:
            continue

        price = _parse_price(name)
        if price is None:
            continue  # linha sem preço válido

        accepts = _parse_int(row[1]) if len(row) > 1 else 0
        if accepts == 0:
            continue

        total_weighted += price * accepts
        total_accepts  += accepts
        price_breakdown.append({"price": price, "accepts": accepts})

    average_ticket  = round(total_weighted / total_accepts, 2) if total_accepts > 0 else 0.0
    total_revenue   = round(total_weighted, 2)

    # Ordena do preço mais vendido para o menos vendido
    price_breakdown.sort(key=lambda x: x["accepts"], reverse=True)

    return {
        "average_ticket":  average_ticket,
        "total_accepts":   total_accepts,
        "total_revenue":   total_revenue,
        "price_breakdown": price_breakdown,
    }
