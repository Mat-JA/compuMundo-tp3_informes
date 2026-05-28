"""
Hit 3 (cont.) — Análisis de resultados de Locust
=================================================
Lee todos los archivos CSV generados por run_experiments.sh y produce:
  1. Tabla Markdown con p50/p95/p99, throughput y tasa de error
  2. Archivo results_summary.csv para graficar en Grafana / Excel

Uso:
    python3 analyze_results.py results/workers_4
    python3 analyze_results.py results/  # analiza todos los runs
"""

from __future__ import annotations

import csv
import os
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ScenarioResult:
    size_kb: int
    users: int
    workers: int
    # métricas de la fila E2E (latencia end-to-end real)
    p50_ms: Optional[float] = None
    p95_ms: Optional[float] = None
    p99_ms: Optional[float] = None
    # métricas del endpoint POST /api/images
    upload_p50_ms: Optional[float] = None
    upload_p95_ms: Optional[float] = None
    # throughput global
    req_per_sec: Optional[float] = None
    error_pct: Optional[float] = None
    total_requests: int = 0
    total_failures: int = 0


def parse_stats_file(csv_path: Path) -> dict[str, dict]:
    """Lee un archivo _stats.csv de Locust y devuelve un dict por Name."""
    rows = {}
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows[row["Name"]] = row
    return rows


def parse_tag(filename: str) -> tuple[int, int, int]:
    """Extrae (size_kb, users, workers) del nombre de archivo."""
    m = re.search(r"size(\d+)kb_u(\d+)_w(\d+)", filename)
    if not m:
        raise ValueError(f"No se pudo parsear el tag de: {filename}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def _safe_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def analyze_directory(results_dir: Path) -> list[ScenarioResult]:
    results = []

    stats_files = sorted(results_dir.rglob("*_stats.csv"))
    if not stats_files:
        print(f"[WARN] No se encontraron archivos *_stats.csv en {results_dir}")
        return []

    for stats_file in stats_files:
        try:
            size_kb, users, workers = parse_tag(stats_file.name)
        except ValueError as e:
            print(f"[SKIP] {e}")
            continue

        rows = parse_stats_file(stats_file)
        result = ScenarioResult(size_kb=size_kb, users=users, workers=workers)

        # Fila E2E (latencia real del procesamiento completo)
        e2e_key = next((k for k in rows if "e2e" in k.lower()), None)
        if e2e_key:
            e2e = rows[e2e_key]
            result.p50_ms = _safe_float(e2e.get("50%", "0"))
            result.p95_ms = _safe_float(e2e.get("95%", "0"))
            result.p99_ms = _safe_float(e2e.get("99%", "0"))

        # Upload endpoint
        upload_key = next((k for k in rows if "POST" in k and "images" in k), None)
        if upload_key:
            up = rows[upload_key]
            result.upload_p50_ms = _safe_float(up.get("50%", "0"))
            result.upload_p95_ms = _safe_float(up.get("95%", "0"))

        # Aggregated row
        agg = rows.get("Aggregated", {})
        result.req_per_sec = _safe_float(agg.get("Requests/s", "0"))
        result.total_requests = int(_safe_float(agg.get("Request Count", "0")))
        result.total_failures = int(_safe_float(agg.get("Failure Count", "0")))
        if result.total_requests > 0:
            result.error_pct = (result.total_failures / result.total_requests) * 100

        results.append(result)

    return sorted(results, key=lambda r: (r.workers, r.size_kb, r.users))


def print_markdown_table(results: list[ScenarioResult]) -> None:
    header = (
        "| Workers | Size (KB) | Users | E2E p50 (ms) | E2E p95 (ms) | E2E p99 (ms) "
        "| Upload p50 (ms) | Req/s | Error % |"
    )
    sep = "|" + "|".join(["-" * (len(h) + 2) for h in header.split("|")[1:-1]]) + "|"
    print("\n## Tabla de resultados — Hit 3 (cont.)\n")
    print(header)
    print(sep)
    for r in results:
        def fmt(v):
            return f"{v:.0f}" if v is not None else "—"
        print(
            f"| {r.workers:7d} | {r.size_kb:9d} | {r.users:5d} "
            f"| {fmt(r.p50_ms):12s} | {fmt(r.p95_ms):12s} | {fmt(r.p99_ms):12s} "
            f"| {fmt(r.upload_p50_ms):15s} | {fmt(r.req_per_sec):5s} "
            f"| {f'{r.error_pct:.1f}' if r.error_pct is not None else '—':7s} |"
        )
    print()


def write_csv_summary(results: list[ScenarioResult], output_path: Path) -> None:
    fields = [
        "workers", "size_kb", "users",
        "e2e_p50_ms", "e2e_p95_ms", "e2e_p99_ms",
        "upload_p50_ms", "upload_p95_ms",
        "req_per_sec", "error_pct",
        "total_requests", "total_failures",
    ]
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in results:
            writer.writerow({
                "workers": r.workers,
                "size_kb": r.size_kb,
                "users": r.users,
                "e2e_p50_ms": r.p50_ms,
                "e2e_p95_ms": r.p95_ms,
                "e2e_p99_ms": r.p99_ms,
                "upload_p50_ms": r.upload_p50_ms,
                "upload_p95_ms": r.upload_p95_ms,
                "req_per_sec": r.req_per_sec,
                "error_pct": r.error_pct,
                "total_requests": r.total_requests,
                "total_failures": r.total_failures,
            })
    print(f"CSV resumen guardado en: {output_path}")


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("results")
    results = analyze_directory(target)

    if not results:
        print("No se encontraron resultados para analizar.")
        sys.exit(1)

    print_markdown_table(results)
    write_csv_summary(results, target / "results_summary.csv")
