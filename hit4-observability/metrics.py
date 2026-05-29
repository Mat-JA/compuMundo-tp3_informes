"""
Hit 4 — Métricas custom de Prometheus para el sistema Sobel
============================================================
Agrega este módulo a applications/shared/metrics.py

Métricas exportadas:
  - sobel_fragments_processed_total        (Counter)
  - sobel_fragments_errors_total           (Counter)
  - sobel_fragment_processing_duration_seconds (Histogram)
  - sobel_queue_depth                      (Gauge — actualizada por el autoscaler)
  - sobel_images_submitted_total           (Counter — backend)
  - sobel_images_completed_total           (Counter — joiner)
  - sobel_dlq_requeued_total               (Counter — dlq_monitor)

Uso en worker/main.py:
    from ..shared.metrics import (
        FRAGMENTS_PROCESSED,
        FRAGMENTS_ERRORS,
        PROCESSING_DURATION,
        record_fragment_processed,
    )

    # Al finalizar exitosamente un fragmento:
    record_fragment_processed(worker_id=WORKER_ID, duration_seconds=elapsed)

    # En caso de error:
    FRAGMENTS_ERRORS.labels(worker_id=WORKER_ID, reason="gcs_error").inc()

Uso en backend/main.py:
    from ..shared.metrics import IMAGES_SUBMITTED, setup_metrics_endpoint
    setup_metrics_endpoint(app)

    # Al publicar imagen:
    IMAGES_SUBMITTED.inc()
"""

from __future__ import annotations

import logging
from typing import Optional

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    REGISTRY,
    make_asgi_app,
    CollectorRegistry,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Definición de métricas
# ---------------------------------------------------------------------------

FRAGMENTS_PROCESSED = Counter(
    "sobel_fragments_processed_total",
    "Total de fragmentos Sobel procesados exitosamente",
    ["worker_id"],
)

FRAGMENTS_ERRORS = Counter(
    "sobel_fragments_errors_total",
    "Total de fragmentos que fallaron durante el procesamiento",
    ["worker_id", "reason"],
)

PROCESSING_DURATION = Histogram(
    "sobel_fragment_processing_duration_seconds",
    "Duración del procesamiento Sobel por fragmento (descarga + filtro + subida)",
    ["worker_id"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0, 120.0],
)

QUEUE_DEPTH = Gauge(
    "sobel_queue_depth",
    "Profundidad actual de la cola fragments.pending (actualizada por autoscaler)",
    ["queue_name"],
)

IMAGES_SUBMITTED = Counter(
    "sobel_images_submitted_total",
    "Total de imágenes enviadas al sistema (backend)",
)

IMAGES_COMPLETED = Counter(
    "sobel_images_completed_total",
    "Total de imágenes completamente procesadas (joiner)",
    ["status"],  # success | error
)

DLQ_REQUEUED = Counter(
    "sobel_dlq_requeued_total",
    "Total de fragmentos reencolados desde la DLQ",
)

DLQ_DISCARDED = Counter(
    "sobel_dlq_discarded_total",
    "Total de fragmentos descartados definitivamente desde la DLQ",
)

IMAGE_E2E_DURATION = Histogram(
    "sobel_image_e2e_duration_seconds",
    "Duración end-to-end de procesamiento completo de imagen (desde upload hasta completed)",
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def record_fragment_processed(worker_id: str, duration_seconds: float) -> None:
    """Registra un fragmento procesado exitosamente."""
    FRAGMENTS_PROCESSED.labels(worker_id=worker_id).inc()
    PROCESSING_DURATION.labels(worker_id=worker_id).observe(duration_seconds)


def record_fragment_error(worker_id: str, reason: str) -> None:
    """Registra un fragmento que falló."""
    FRAGMENTS_ERRORS.labels(worker_id=worker_id, reason=reason).inc()


def record_image_completed(status: str = "success", e2e_seconds: Optional[float] = None) -> None:
    """Registra una imagen completamente procesada."""
    IMAGES_COMPLETED.labels(status=status).inc()
    if e2e_seconds is not None:
        IMAGE_E2E_DURATION.observe(e2e_seconds)


# ---------------------------------------------------------------------------
# Endpoint /metrics para FastAPI (backend, split, joiner, dlq_monitor)
# ---------------------------------------------------------------------------

def setup_metrics_endpoint(app) -> None:
    """
    Monta el endpoint /metrics en una aplicación FastAPI existente.

    Llamar desde el lifespan o al crear la app:
        from ..shared.metrics import setup_metrics_endpoint
        setup_metrics_endpoint(app)
    """
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
    logger.info("Prometheus /metrics endpoint montado")


# ---------------------------------------------------------------------------
# Servidor de métricas standalone para los workers (no tienen FastAPI)
# ---------------------------------------------------------------------------

def start_metrics_server(port: int = 9090) -> None:
    """
    Inicia un servidor HTTP standalone para exponer /metrics.
    Usar en worker/main.py (que no tiene FastAPI):

        from ..shared.metrics import start_metrics_server
        start_metrics_server(port=9090)
    """
    import threading
    from prometheus_client import start_http_server

    def _serve():
        start_http_server(port)
        logger.info("Prometheus metrics server escuchando en :%d", port)

    t = threading.Thread(target=_serve, daemon=True)
    t.start()
