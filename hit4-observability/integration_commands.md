=============================================================================
# Hit 4 — Cómo integrar las métricas en el código existente
=============================================================================

Este archivo muestra los DIFFS exactos a aplicar en cada servicio.
No reemplaza los archivos originales — solo muestra qué agregar.
=============================================================================


─────────────────────────────────────────────────────────────────────────────
## 1. applications/shared/requirements.txt (agregar en cada requirements.txt)
─────────────────────────────────────────────────────────────────────────────

+ prometheus-client==0.20.0



─────────────────────────────────────────────────────────────────────────────
## 2. applications/worker/main.py — cambios necesarios
─────────────────────────────────────────────────────────────────────────────

AGREGAR al principio (después de los imports existentes):

  from ..shared.metrics import (
      record_fragment_processed,
      record_fragment_error,
      start_metrics_server,
  )

AGREGAR al inicio de async def main():

  start_metrics_server(port=9090)  # expone :9090/metrics para Prometheus

CAMBIAR en el callback, reemplazar la línea "await message.ack()":

  processing_time_sec = time.monotonic() - start_time   # ya existe como start_time
  record_fragment_processed(worker_id=WORKER_ID, duration_seconds=processing_time_sec)
  await message.ack()

CAMBIAR en el bloque except (donde hace nack):

  record_fragment_error(
      worker_id=WORKER_ID,
      reason=type(exc).__name__ if 'exc' in locals() else "unknown",
  )
  await message.nack(requeue=False)


─────────────────────────────────────────────────────────────────────────────
## 3. applications/backend/main.py — cambios necesarios
─────────────────────────────────────────────────────────────────────────────

AGREGAR import:

  from ..shared.metrics import setup_metrics_endpoint

AGREGAR al final del archivo (después de app.include_router):

  setup_metrics_endpoint(app)



─────────────────────────────────────────────────────────────────────────────
## 4. applications/backend/routes.py — cambios necesarios
─────────────────────────────────────────────────────────────────────────────

AGREGAR import:

  from ..shared.metrics import IMAGES_SUBMITTED

AGREGAR en upload_image(), después de publicar a RabbitMQ:

  IMAGES_SUBMITTED.inc()



─────────────────────────────────────────────────────────────────────────────
## 5. applications/joiner/consumer.py — cambios necesarios
─────────────────────────────────────────────────────────────────────────────

AGREGAR import:

  from ..shared.metrics import record_image_completed, setup_metrics_endpoint

AGREGAR cuando una imagen se completa exitosamente:

  record_image_completed(status="success", e2e_seconds=elapsed_total)

AGREGAR en main.py del joiner:

  setup_metrics_endpoint(app)



─────────────────────────────────────────────────────────────────────────────
## 6. applications/dlq_monitor/consumer.py — cambios necesarios
─────────────────────────────────────────────────────────────────────────────

AGREGAR import:

  from ..shared.metrics import DLQ_REQUEUED, DLQ_DISCARDED

AGREGAR cuando reencolás un fragmento:

  DLQ_REQUEUED.inc()

AGREGAR cuando descartás un fragmento:

  DLQ_DISCARDED.inc()



─────────────────────────────────────────────────────────────────────────────
## 7. Kubernetes — anotaciones para autodiscovery de Prometheus
─────────────────────────────────────────────────────────────────────────────   

Agregar en cada Deployment dentro de spec.template.metadata.annotations

Para servicios FastAPI (backend, joiner, split, dlq_monitor) — puerto 8000:

  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8000"
    prometheus.io/path: "/metrics"

Para workers externos (VMs fuera del cluster) — puerto 9090:
  Agregar las IPs a prometheus-stack-values.yaml en:
    additionalScrapeConfigs > job_name: "sobel-workers-external" > targets
