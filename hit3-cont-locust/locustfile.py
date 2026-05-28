
#Hit 3 (cont.) — Load Testing con Locust
#========================================
#Escenarios:
#  - V1: Tamaño de imagen: 1KB, 10KB, 100KB, 1MB, 10MB, 100MB
#  - V2: Concurrencia: controlada por --users de Locust
#  - V3: Workers: ajustada externamente (Terraform/GKE)

#Uso:
#  locust -f locustfile.py --host=http://<BACKEND_IP>:8000
#  locust -f locustfile.py --host=http://<BACKEND_IP>:8000 --headless \
#    -u 10 -r 2 --run-time 2m --csv=results/run_u10

#Variables de entorno opcionales:
#  IMAGE_SIZE_KB  — tamaño de imagen sintética en KB (default: 100)
#  POLL_TIMEOUT   — segundos máximos esperando resultado (default: 120)


from __future__ import annotations

import io
import logging
import os
import struct
import time
import zlib

from locust import HttpUser, TaskSet, between, events, task

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers para generar imágenes PNG sintéticas de tamaño controlado
# ---------------------------------------------------------------------------

def _make_png(target_kb: int) -> bytes:
    """
    Genera un PNG válido de tamaño aproximado a target_kb.
    Usa píxeles aleatorios para evitar que la compresión deflate
    reduzca demasiado el tamaño del archivo.
    """
    import random
    target_bytes = target_kb * 1024

    # Calculamos un tamaño de imagen cuadrada que produzca ~target_bytes
    # PNG sin compresión: width * height * 3 bytes (RGB) + overhead ~11 bytes/row
    # Estimación: pixels = target_bytes / 3
    pixels = max(target_bytes // 3, 1)
    side = max(int(pixels ** 0.5), 1)

    width = side
    height = side

    def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
        length = struct.pack(">I", len(data))
        crc = struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        return length + chunk_type + data + crc

    # IHDR
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr = png_chunk(b"IHDR", ihdr_data)

    # IDAT — generamos filas de píxeles RGB aleatorios
    raw_rows = []
    for _ in range(height):
        row = bytes([random.randint(0, 255) for _ in range(width * 3)])
        raw_rows.append(b"\x00" + row)  # filtro None por fila

    raw_data = b"".join(raw_rows)
    compressed = zlib.compress(raw_data, level=1)  # level=1 → velocidad, menos compresión
    idat = png_chunk(b"IDAT", compressed)

    # IEND
    iend = png_chunk(b"IEND", b"")

    return b"\x89PNG\r\n\x1a\n" + ihdr + idat + iend


# Precargamos imágenes de distintos tamaños para no generarlas en cada request
IMAGE_SIZES_KB = [1, 10, 100, 1024, 10240, 102400]
_IMAGE_CACHE: dict[int, bytes] = {}

def _get_image(size_kb: int) -> bytes:
    if size_kb not in _IMAGE_CACHE:
        _IMAGE_CACHE[size_kb] = _make_png(size_kb)
    return _IMAGE_CACHE[size_kb]


# ---------------------------------------------------------------------------
# TaskSets
# ---------------------------------------------------------------------------

class SobelUploadAndPoll(TaskSet):
    """
    Sube una imagen, hace polling hasta completar (o timeout) y registra
    la latencia end-to-end como métrica custom de Locust.
    """

    # Tamaño de imagen en KB, configurable por variable de entorno
    image_size_kb: int = int(os.environ.get("IMAGE_SIZE_KB", "100"))
    poll_timeout: int = int(os.environ.get("POLL_TIMEOUT", "120"))
    poll_interval: float = 2.0  # segundos entre polls

    @task(1)
    def upload_and_wait(self) -> None:
        png_bytes = _get_image(self.image_size_kb)

        # --- UPLOAD ---
        with self.client.post(
            "/api/images",
            files={"file": ("test.png", io.BytesIO(png_bytes), "image/png")},
            catch_response=True,
            name="POST /api/images",
        ) as resp:
            if resp.status_code != 201:
                resp.failure(f"Upload failed: {resp.status_code} — {resp.text[:200]}")
                return
            image_id = resp.json().get("image_id")
            if not image_id:
                resp.failure("No image_id in upload response")
                return
            resp.success()

        # --- POLLING ---
        start = time.monotonic()
        final_status = None

        while (time.monotonic() - start) < self.poll_timeout:
            with self.client.get(
                f"/api/images/{image_id}/status",
                catch_response=True,
                name="GET /api/images/{id}/status",
            ) as poll_resp:
                if poll_resp.status_code == 200:
                    data = poll_resp.json()
                    status = data.get("status", "")
                    poll_resp.success()
                    if status == "completed":
                        final_status = "completed"
                        break
                    elif status == "error":
                        final_status = "error"
                        break
                else:
                    poll_resp.failure(f"Poll failed: {poll_resp.status_code}")
                    break

            time.sleep(self.poll_interval)

        elapsed_ms = int((time.monotonic() - start) * 1000)

        # Registramos la latencia e2e como evento Locust
        events.request.fire(
            request_type="E2E",
            name=f"e2e_{self.image_size_kb}kb",
            response_time=elapsed_ms,
            response_length=0,
            exception=None if final_status == "completed" else Exception(
                f"final_status={final_status}, timeout={self.poll_timeout}s"
            ),
            context={},
        )

    @task(3)
    def health_check(self) -> None:
        """Tarea liviana para medir overhead base del servidor."""
        with self.client.get("/health", catch_response=True, name="GET /health") as r:
            if r.status_code == 200:
                r.success()
            else:
                r.failure(f"Health check failed: {r.status_code}")


class StatusOnlyCheck(TaskSet):
    """
    Escenario de lectura pura — útil para medir throughput de polling
    sin costo de cómputo Sobel.
    """
    known_ids: list[str] = []

    @task
    def poll_random(self) -> None:
        if not self.known_ids:
            self.client.get("/health")
            return
        image_id = self.known_ids[int(time.time()) % len(self.known_ids)]
        self.client.get(
            f"/api/images/{image_id}/status",
            name="GET /api/images/{id}/status [read-only]",
        )


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class SobelUser(HttpUser):
    """
    Usuario principal: sube imágenes y espera resultado.
    Pausa entre 1 y 5 segundos entre tareas para simular un usuario real.
    """
    tasks = [SobelUploadAndPoll]
    wait_time = between(1, 5)

    def on_start(self) -> None:
        logger.info("SobelUser started — image_size=%dKB", SobelUploadAndPoll.image_size_kb)


class ReadOnlyUser(HttpUser):
    """
    Usuario de solo lectura (polling). Peso bajo: 1 ReadOnly por cada 4 SobelUsers.
    """
    tasks = [StatusOnlyCheck]
    wait_time = between(0.5, 2)
    weight = 1
