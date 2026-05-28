#!/usr/bin/env bash
# =============================================================================
# Hit 3 (cont.) — Script de experimentos de carga automatizados
#
# Corre Locust en modo headless para cada combinación de:
#   V1 (tamaño): 1KB, 10KB, 100KB, 1MB, 10MB
#   V2 (users):  1, 5, 10, 20, 50
#
# V3 (workers) se configura externamente antes de correr este script
# ajustando el MIG de Terraform.
#
# Uso:
#   chmod +x run_experiments.sh
#   BACKEND_HOST=http://34.x.x.x:8000 WORKERS=4 ./run_experiments.sh
# =============================================================================

set -euo pipefail

BACKEND_HOST="${BACKEND_HOST:-http://localhost:8000}"
WORKERS="${WORKERS:-4}"             # Cantidad de workers (solo para nombre de archivo)
RESULTS_DIR="results/workers_${WORKERS}"
RUN_TIME="${RUN_TIME:-2m}"          # Duración de cada test
SPAWN_RATE="${SPAWN_RATE:-2}"       # Usuarios nuevos por segundo

# Tamaños de imagen a testear (en KB)
IMAGE_SIZES=(1 10 100 1024 10240 102400)

# Niveles de concurrencia a testear
USER_COUNTS=(1 5 10 20 50)

mkdir -p "$RESULTS_DIR"

echo "=============================================="
echo "  Sobel Load Test — Hit 3 (cont.)"
echo "  Backend: $BACKEND_HOST"
echo "  Workers: $WORKERS"
echo "  Run time per scenario: $RUN_TIME"
echo "=============================================="

total=$((${#IMAGE_SIZES[@]} * ${#USER_COUNTS[@]}))
current=0

for size_kb in "${IMAGE_SIZES[@]}"; do
    for users in "${USER_COUNTS[@]}"; do
        current=$((current + 1))
        tag="size${size_kb}kb_u${users}_w${WORKERS}"
        csv_prefix="${RESULTS_DIR}/${tag}"

        echo ""
        echo "[$current/$total] size=${size_kb}KB  users=${users}  workers=${WORKERS}"
        echo "  → CSV prefix: ${csv_prefix}"

        IMAGE_SIZE_KB=$size_kb locust \
            -f locustfile.py \
            --host="$BACKEND_HOST" \
            --headless \
            --users "$users" \
            --spawn-rate "$SPAWN_RATE" \
            --run-time "$RUN_TIME" \
            --csv="$csv_prefix" \
            --csv-full-history \
            --only-summary \
            2>&1 | tee "${csv_prefix}.log"

        echo "  ✓ Listo"
        sleep 5   # Pausa entre runs para que las colas se drenen
    done
done

echo ""
echo "=============================================="
echo "  Todos los experimentos completados."
echo "  Archivos en: $RESULTS_DIR"
echo ""
echo "  Para generar la tabla de resultados:"
echo "    python3 analyze_results.py $RESULTS_DIR"
echo "=============================================="
