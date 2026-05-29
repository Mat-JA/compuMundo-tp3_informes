# Hit 4 — Guía de implementación

## Estructura de archivos

```
hit4-observability/
  metrics.py                          ← Módulo Python de métricas (copiar a applications/shared/)
  HOW_TO_INTEGRATE.py                 ← Diffs a aplicar en cada servicio
  pipeline-observability.yaml         ← GitHub Actions pipeline
  kubernetes/
    namespace-monitoring.yaml         ← Namespace monitoring
    prometheus-stack-values.yaml      ← Helm values (Prometheus + Grafana + AlertManager)
    sobel-alerts.yaml                 ← PrometheusRules con alertas
    sobel-dashboard-configmap.yaml    ← Dashboard de Grafana (ConfigMap)
```


## Hit 4 — Prometheus + Grafana

### Paso 1 — Copiar el módulo de métricas

```bash
cp hit4-observability/metrics.py applications/shared/metrics.py
```

Agregar `prometheus-client==0.20.0` a cada `requirements.txt`.

### Paso 2 — Integrar métricas en los servicios

Seguir las instrucciones en `HOW_TO_INTEGRATE.py`. Resumen:


| Servicio      | Qué agregar                                                                             |
| ------------- | ---------------------------------------------------------------------------------------- |
| `worker`      | `start_metrics_server(9090)` + `record_fragment_processed()` + `record_fragment_error()` |
| `backend`     | `setup_metrics_endpoint(app)` + `IMAGES_SUBMITTED.inc()`                                 |
| `joiner`      | `setup_metrics_endpoint(app)` + `record_image_completed()`                               |
| `dlq_monitor` | `setup_metrics_endpoint(app)` + `DLQ_REQUEUED.inc()`                                     |
| `split`       | `setup_metrics_endpoint(app)`                                                            |

### Paso 3 — Agregar anotaciones en los Deployments de Kubernetes

En cada `Deployment` dentro de `spec.template.metadata.annotations`:

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"
```

### Paso 4 — Agregar IPs de workers externos en Prometheus

En `prometheus-stack-values.yaml`, sección `additionalScrapeConfigs > sobel-workers-external`:

```yaml
static_configs:
  - targets: ["10.x.x.x:9090", "10.x.x.y:9090"]
```

### Paso 5 — Desplegar con GitHub Actions

1. Mover `pipeline-observability.yaml` a `.github/workflows/`
2. Agregar secrets: `GRAFANA_ADMIN_PASSWORD`
3. Ejecutar el pipeline con action = `install`

### Paso 6 — Verificar

```bash
# Port-forward Grafana si no tiene LoadBalancer todavía
kubectl port-forward svc/kube-prom-stack-grafana 3000:3000 -n monitoring

# Ver alertas activas
kubectl get prometheusrule -n monitoring
```

### Dashboard de Grafana

El dashboard `sobel-main` se carga automáticamente e incluye:

- CPU y Memoria por pod
- Cola `fragments.pending` (publicados / consumidos / en espera)
- Dead Letter Queue
- Latencia p50/p95/p99 de procesamiento Sobel
- Throughput de fragmentos procesados por segundo
- Tasa de errores (gauge con umbrales de color)
- Requests al backend por segundo

### Alertas configuradas


| Alerta                     | Condición                         | Severidad |
| -------------------------- | ---------------------------------- | --------- |
| `FragmentQueueHighDepth`   | Cola > 500 msgs por 2 min          | warning   |
| `FragmentQueueCritical`    | Cola > 2000 msgs por 1 min         | critical  |
| `DLQHasMessages`           | DLQ > 0 msgs                       | warning   |
| `RabbitMQDown`             | Endpoint caído 1 min              | critical  |
| `WorkerNotProcessing`      | 0 procesados + cola > 10 por 3 min | critical  |
| `WorkerHighProcessingTime` | p95 > 30s por 5 min                | warning   |
| `WorkerHighErrorRate`      | Error rate > 5% por 2 min          | warning   |
| `BackendHighErrorRate`     | HTTP 5xx > 1% por 2 min            | warning   |
| `PodCrashLooping`          | Restart rate > 0 por 5 min         | critical  |
| `HighMemoryUsage`          | Memory > 85% del límite           | warning   |
