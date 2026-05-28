# Hit 3 (cont.) — Guía de implementación

## Estructura de archivos

```
hit3-cont-locust/
  locustfile.py          ← Tests de carga (Locust)
  run_experiments.sh     ← Script que corre todas las combinaciones V1×V2
  analyze_results.py     ← Genera tabla Markdown + CSV de resultados
  requirements.txt       ← pip install -r requirements.txt
```

## Hit 3 (cont.) — Load Testing con Locust

### Instalación

```bash
cd hit3-cont-locust
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
```

### Correr en modo UI (recomendado para explorar)

```bash
locust -f locustfile.py --host=http:/localhost:8000
# Abrir http://localhost:8089
```

### Correr todos los experimentos automáticamente

```bash
# Ajustar workers en Terraform primero, luego:
BACKEND_HOST=http://<BACKEND_IP>:8000 WORKERS=4 ./run_experiments.sh

BACKEND_HOST=http://localhost:8000 WORKERS=4 ./run_experiments.sh
# Repetir cambiando WORKERS=1, WORKERS=2, WORKERS=8, etc.
```

### Variables de entorno


| Variable        | Default | Descripción                          |
| --------------- | ------- | ------------------------------------- |
| `IMAGE_SIZE_KB` | 100     | Tamaño de imagen sintética          |
| `POLL_TIMEOUT`  | 120     | Segundos máximos esperando resultado |
| `BACKEND_HOST`  | —      | URL del backend (obligatorio)         |
| `WORKERS`       | 4       | Solo para nombre de archivo CSV       |
| `RUN_TIME`      | 2m      | Duración de cada escenario           |

### Generar tabla de resultados

```bash
python3 analyze_results.py results/workers_4
```

### Variables del experimento

- **V1 (Tamaño):** 1 KB, 10 KB, 100 KB, 1 MB, 10 MB
- **V2 (Usuarios/concurrencia):** 1, 5, 10, 20, 50
- **V3 (Workers):** ajustar el MIG en Terraform entre corridas

### Métricas reportadas

- `E2E p50/p95/p99` — latencia completa desde upload hasta completed
- `Upload p50` — solo el tiempo de subida HTTP
- `Req/s` — throughput de requests HTTP
- `Error %` — tasa de fallos
