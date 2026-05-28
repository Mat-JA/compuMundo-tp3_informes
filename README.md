# TP3 Informes


# Trabajo Práctico Nº 3 — Parte 2

<details open="" class="section-collapsible">
<p><strong>Fecha de entrega:</strong> 20/05/2026 — todos los puntos.</p>
<blockquote>
<p><strong>Continuidad con la Parte 1.</strong> Esta entrega asume los
ejercicios del Hit #0 (patrones de mensajería [RMQ]) y el Hit #1 (Sobel
distribuido sobre Docker [SOB68]) ya resueltos. Los requisitos generales
de entrega (informe, repositorio público, CI/CD, gitleaks, video,
health-check) y la lista de <strong>Contenidos del programa
relacionados</strong> son los mismos que los declarados en la Parte 1 —
no se repiten acá.</p>
</blockquote>
<hr/>
</details>

**Fecha de entrega:** 20/05/2026 — todos los puntos.

> **Continuidad con la Parte 1.** Esta entrega asume los ejercicios del Hit #0 (patrones de mensajería [RMQ]) y el Hit #1 (Sobel distribuido sobre Docker [SOB68]) ya resueltos. Los requisitos generales de entrega (informe, repositorio público, CI/CD, gitleaks, video, health-check) y la lista de **Contenidos del programa relacionados** son los mismos que los declarados en la Parte 1 — no se repiten acá.

---

</details>

<details open="" class="section-collapsible">
<p>La definición canónica del <strong>NIST</strong> [NIST800-145]
establece cinco características esenciales del Cloud Computing:
<em>on-demand self-service</em>, <em>broad network access</em>,
<em>resource pooling</em>, <em>rapid elasticity</em> y <em>measured
service</em>. El paper de Berkeley de Armbrust et al. [ARMBRUST10] —“A
View of Cloud Computing”— sigue siendo la referencia académica más
citada para entender el modelo y sus tradeoffs económicos.</p>
<p>Sobre esa base, en la práctica tenemos dos patrones de trabajo:</p>
<ul data-tight="true"><li><p><strong>Cloud Native:</strong> la aplicación corre 100% en la
nube.</p></li><li data-node-id="20260528143557-i5raov0"><p><strong>Híbrido (On-premise + Cloud):</strong> parte de la
aplicación corre en equipos locales y otra parte en la nube.</p></li></ul>
<p>Pensemos la nube como una <em>extensión</em> de la capacidad de
cómputo de los equipos locales. Aplicando este enfoque podemos
implementar el patrón de <strong>Cloud-Bursting</strong> [CBURST]:
cuando la demanda local satura la capacidad propia, “se desborda” hacia
la nube.</p>
<blockquote>
<p><strong>Nota sobre tradeoffs distribuidos.</strong> Antes de diseñar
componentes que se sincronizan en la nube, conviene tener presente el
<strong>teorema CAP</strong> de Brewer [BREWER00]: en presencia de
particiones de red, hay que elegir entre consistencia y disponibilidad.
RabbitMQ y Redis adoptan posiciones distintas en ese espacio —
investiguen cuál es la elección de cada uno y por qué importa para su
arquitectura.</p>
</blockquote>
<p>En esta segunda parte vamos a hacer que todo lo que en la Parte 1 se
corrió “distribuido” (pero centralizado en la propia computadora)
<strong>escale realmente</strong>.</p>
<p>¿Qué queremos lograr?</p>
<ul data-tight="true"><li><p><strong>Si nos quedamos solo en local</strong>, agregar más nodos de
trabajo requiere tiempo (compra, ambientación, espacio físico e
instalación de paquetes) y genera un costo fijo mínimo, además del
variable por intensidad de uso.</p></li><li data-node-id="20260528143557-repl1hc"><p><strong>Hacer offloading a la nube</strong> [KUM10] es la
alternativa elástica: los recursos se aprovisionan y se destruyen
on-demand, y se paga solo por el tiempo de uso. En este apartado vamos a
trabajar sobre este enfoque.</p></li></ul>
<hr/>
<h3 id="hit-2--sobel-con-offloading-en-la-nube">Hit #2 — Sobel con
offloading en la nube</h3>
<p>El objetivo del Hit #2 es construir una <strong>base
elástica</strong>: el mismo cómputo del operador de Sobel del Hit #1,
pero usando <strong>Terraform</strong> [TF] para crear nodos de trabajo
bajo demanda y eliminarlos al terminar la tarea. Para cada worker, el
ciclo es:</p>
<ul data-tight="true"><li><p><strong>Provisioning:</strong> crear la VM en el cloud
provider.</p></li><li data-node-id="20260528143557-fzr2s8z"><p><strong>Bootstrap:</strong> instalar las herramientas necesarias
mediante <code>user_data</code> (Java, Docker, tooling).</p></li><li><p><strong>Deploy:</strong> copiar el ejecutable (<code>.jar</code>,
<code>.py</code>, etc.) o descargar la imagen Docker desde un registry
público.</p></li><li data-node-id="20260528143557-7iek2mx"><p><strong>Join:</strong> poner a correr la aplicación e integrarla al
cluster de trabajo.</p></li><li><p><strong>Teardown:</strong> una vez completada la tarea, destruir la
VM.</p></li></ul>
<h4 id="requisitos-de-infraestructura-como-código-iac">Requisitos de
Infraestructura como Código (IaC)</h4>
<ul data-tight="true"><li><p><strong>Remote state obligatorio:</strong> configurar un backend
remoto para el estado de Terraform (GCS bucket + lock, o S3 + DynamoDB
lock). <strong>No se acepta</strong> estado local
(<code>terraform.tfstate</code> en el repo).</p></li><li data-node-id="20260528143557-uf0w8qh"><p><strong>Estructura de archivos mínima:</strong> organizar el código
Terraform en archivos separados: <code>provider.tf</code> (configuración
del provider y backend), <code>variables.tf</code> (declaración de
variables), <code>main.tf</code> (recursos principales) y
<code>outputs.tf</code> (valores de salida). No colocar todo en un único
archivo.</p></li><li><p><strong>Terraform plan en CI/CD:</strong> el pipeline debe ejecutar
<code>terraform plan</code> en cada Pull Request y
<code>terraform apply</code> <strong>solo</strong> al mergear a la rama
principal.</p></li></ul>
<p>El objetivo es construir una arquitectura <strong>híbrida</strong>
escalable (tipo 1, inicial). Presenten el diagrama de arquitectura y
justifiquen, para cada servicio, dónde lo despliegan (local vs nube) y
por qué.</p>
<p><img src="https://dpetrocelli.github.io/sd2026/assets/images/tp3_hit2.png" alt="Hit #2 — Sobel con Offloading en la Nube"/></p>
<hr/>
<h3 id="hit-3--sobel-contenerizado-asincrónico-y-escalable-base-del-tp-integrador">Hit
#3 — Sobel contenerizado, asincrónico y escalable (base del TP
Integrador)</h3>
<p>A diferencia del esquema híbrido del Hit #2, ahora la idea es
construir una infraestructura <strong>100% en la nube</strong> pero con
un enfoque diferente: orquestada con Kubernetes [K8S]. El paper de Burns
et al. [BURNS16] —“Borg, Omega, and Kubernetes”— traza el linaje
conceptual de K8s desde los sistemas de orquestación internos de Google
y explica por qué se diseñó como está.</p>
<h4 id="1-desplegar-con-terraform-un-cluster-de-kubernetes-gke">1.
Desplegar con Terraform un cluster de Kubernetes (GKE)</h4>
<p>Este cluster va a manejar todos los recursos del sistema: tanto los
servicios de infraestructura (RabbitMQ, Redis) como los componentes de
aplicación (frontend, backend, split, joiner). La configuración mínima
exigida es:</p>
<ol type="1" data-tight="true"><li><p><strong>Nodegroup de infraestructura:</strong> aloja los servicios
base (RabbitMQ, Redis, observabilidad).</p></li><li data-node-id="20260528143557-ugleggs"><p><strong>Nodegroup de aplicaciones:</strong> aloja los componentes
del sistema (frontend, backend, split, joiner).</p></li><li><p><strong>Pool de workers fuera del cluster:</strong> máquinas
virtuales gestionadas con Terraform aparte (no son nodos de Kubernetes),
encargadas de las tareas de cómputo intensivo. Mantenerlas fuera del
cluster permite escalarlas de manera independiente y aprovechar tipos de
instancia distintos sin cambiar el <code>nodepool</code> de GKE.</p></li></ol>
<h4 id="requisitos-de-mensajería-aplicando-los-patrones-del-hit-0">Requisitos
de mensajería (aplicando los patrones del Hit #0)</h4>
<ul data-tight="true"><li><p><strong>Dead Letter Queue:</strong> configurar una DLX en las colas
de procesamiento Sobel. Si un worker falla al procesar un fragmento de
imagen (crash, timeout, <em>out of memory</em>), el mensaje debe ir a la
DLQ en lugar de perderse. Implementar un servicio que monitoree la DLQ y
re-asigne los fragmentos fallidos a otros workers.</p></li><li data-node-id="20260528143557-njap3v9"><p><strong>Retry con exponential backoff:</strong> cuando un worker no
puede contactar a RabbitMQ o Redis (por ejemplo, durante un despliegue o
reinicio), debe reintentar la conexión con backoff exponencial (1s, 2s,
4s, 8s, máximo 30s). <strong>No implementar retry infinito sin
backoff:</strong> genera tormentas de reconexión que empeoran el
problema.</p></li><li><p><strong>Pub/Sub para notificación de resultados:</strong> cuando un
worker completa un fragmento, publicar el resultado en un
<em>exchange</em> <code>fanout</code> para que tanto el servicio
<em>joiner</em> como el dashboard de monitoreo reciban la
notificación.</p></li></ul>
<p><img src="https://dpetrocelli.github.io/sd2026/assets/images/tp3_hit3.png" alt="Hit #3 — Arquitectura Kubernetes (GKE)"/></p>
<h4 id="2-construir-los-pipelines-de-despliegue">2. Construir los
pipelines de despliegue</h4>
<ul data-tight="true"><li><p><strong>Pipeline 1 — Infraestructura:</strong> construye el cluster
de Kubernetes con Terraform.
</p><ul data-tight="true"><li><p><strong>Pipeline 1.1</strong> — Despliega los servicios base
(RabbitMQ, Redis y otros).</p></li><li data-node-id="20260528143557-btk94on"><p><strong>Pipeline 1.2 … 1.N</strong> — Despliega cada aplicación
(frontend, backend, split, joiner).</p></li></ul></li><li data-node-id="20260528143557-g6n8adm"><p><strong>Pipeline 2 — Workers dinámicos:</strong> despliega y
destruye las máquinas virtuales que actúan como workers. Objetivo
deseable: que el dimensionamiento sea <strong>dinámico</strong> según la
cola pendiente.</p></li></ul>
<hr/>
<h3 id="hit-3-cont--análisis-de-desempeño-bajo-carga">Hit #3 (cont.) —
Análisis de desempeño bajo carga</h3>
<p>Para evaluar el desempeño de la plataforma vamos a medir los tiempos
de respuesta en diferentes escenarios, modificando tres variables:</p>
<ul data-tight="true"><li><p><strong>V1 — Tamaño de los datos:</strong> 1 KB, 10 KB, 100 KB, 1
MB, 10 MB, 100 MB.</p></li><li data-node-id="20260528143557-sf9cpg0"><p><strong>V2 — Concurrencia:</strong> distintos niveles de peticiones
concurrentes.</p></li><li><p><strong>V3 — Cantidad de workers:</strong> se ajusta el número de
procesos o threads disponibles para manejar las peticiones.</p></li></ul>
<blockquote>
<p><strong>Nota sobre quotas:</strong> las cuentas gratuitas de los
cloud providers tienen límites de VMs por región/zona. Si necesitan
escalar a más nodos para los experimentos, distribúyanlos entre varias
regiones para no chocar contra el cupo.</p>
</blockquote>
<p>El objetivo es entender cómo la plataforma responde al modificar
estas variables, identificar la capacidad real de escalabilidad y los
posibles cuellos de botella. Los resultados se presentan en una tabla
con el tiempo de respuesta para cada combinación de variables, dando una
visión clara de la evolución del desempeño bajo distintas
condiciones.</p>
<p><strong>Herramienta de load testing:</strong> usar una herramienta de
benchmarking como <strong>Locust</strong> [LOCUST] o <strong>k6</strong>
[K6]. Permiten definir escenarios reproducibles y generar reportes
comparables. Documenten la configuración del test (cantidad de
<em>virtual users</em>, <em>ramp-up</em>, duración) y presenten los
resultados con métricas estándar: latencia p50/p95/p99, throughput
(req/s) y tasa de errores.</p>
<hr/>
<h3 id="hit-4--observabilidad-prometheus--grafana">Hit #4 —
Observabilidad (Prometheus + Grafana)</h3>
<p>La observabilidad es un pilar de las prácticas modernas de
<strong>Site Reliability Engineering</strong> [BEYER16]: sin métricas,
logs y trazas no se pueden definir SLOs ni razonar sobre la salud del
sistema en producción. Desplieguen Prometheus [PROM, BRAZIL18] y Grafana
[GRAF] en el cluster de Kubernetes para monitorear la plataforma:</p>
<ol type="1" data-tight="true"><li><p><strong>Instalación:</strong> instalar Prometheus y Grafana en el
nodegroup de infraestructura. Pueden usar el Helm chart oficial
<code>prometheus-community/kube-prometheus-stack</code>.</p></li><li data-node-id="20260528143557-yqn0adm"><p><strong>Instrumentación:</strong> instrumentar los servicios
(backend, workers, split, joiner) para que exporten métricas custom:
tareas procesadas, tareas en cola, tiempo de procesamiento por tarea y
errores.</p></li><li><p><strong>Dashboard:</strong> crear un dashboard en Grafana que
muestre como mínimo:
</p><ul data-tight="true"><li><p>Uso de CPU y memoria por pod/nodo.</p></li><li data-node-id="20260528143557-noieaeh"><p>Mensajes procesados en RabbitMQ (publicados vs consumidos vs en
cola).</p></li><li><p>Latencia de procesamiento de tareas (p50, p95, p99).</p></li><li data-node-id="20260528143557-uuq50b9"><p>Tasa de errores.</p></li></ul></li><li data-node-id="20260528143557-51xdgbj"><p><strong>Alertas:</strong> configurar al menos una alerta básica (por
ejemplo: cola de RabbitMQ supera un umbral, o un worker no responde en X
segundos).</p></li></ol>
<hr/>
</details>

La definición canónica del **NIST** [NIST800-145] establece cinco características esenciales del Cloud Computing: *on-demand self-service*, *broad network access*, *resource pooling*, *rapid elasticity* y *measured service*. El paper de Berkeley de Armbrust et al. [ARMBRUST10] —“A View of Cloud Computing”— sigue siendo la referencia académica más citada para entender el modelo y sus tradeoffs económicos.

Sobre esa base, en la práctica tenemos dos patrones de trabajo:

* **Cloud Native:** la aplicación corre 100% en la nube.
* **Híbrido (On-premise + Cloud):** parte de la aplicación corre en equipos locales y otra parte en la nube.

Pensemos la nube como una *extensión* de la capacidad de cómputo de los equipos locales. Aplicando este enfoque podemos implementar el patrón de **Cloud-Bursting** [CBURST]: cuando la demanda local satura la capacidad propia, “se desborda” hacia la nube.

> **Nota sobre tradeoffs distribuidos.** Antes de diseñar componentes que se sincronizan en la nube, conviene tener presente el **teorema CAP** de Brewer [BREWER00]: en presencia de particiones de red, hay que elegir entre consistencia y disponibilidad. RabbitMQ y Redis adoptan posiciones distintas en ese espacio — investiguen cuál es la elección de cada uno y por qué importa para su arquitectura.

En esta segunda parte vamos a hacer que todo lo que en la Parte 1 se corrió “distribuido” (pero centralizado en la propia computadora) **escale realmente**.

¿Qué queremos lograr?

* **Si nos quedamos solo en local**, agregar más nodos de trabajo requiere tiempo (compra, ambientación, espacio físico e instalación de paquetes) y genera un costo fijo mínimo, además del variable por intensidad de uso.
* **Hacer offloading a la nube** [KUM10] es la alternativa elástica: los recursos se aprovisionan y se destruyen on-demand, y se paga solo por el tiempo de uso. En este apartado vamos a trabajar sobre este enfoque.

---

### Hit #2 — Sobel con offloading en la nube

El objetivo del Hit #2 es construir una **base elástica**: el mismo cómputo del operador de Sobel del Hit #1, pero usando **Terraform** [TF] para crear nodos de trabajo bajo demanda y eliminarlos al terminar la tarea. Para cada worker, el ciclo es:

* **Provisioning:** crear la VM en el cloud provider.
* **Bootstrap:** instalar las herramientas necesarias mediante `user_data` (Java, Docker, tooling).
* **Deploy:** copiar el ejecutable (`.jar`, `.py`, etc.) o descargar la imagen Docker desde un registry público.
* **Join:** poner a correr la aplicación e integrarla al cluster de trabajo.
* **Teardown:** una vez completada la tarea, destruir la VM.

#### Requisitos de Infraestructura como Código (IaC)

* **Remote state obligatorio:** configurar un backend remoto para el estado de Terraform (GCS bucket + lock, o S3 + DynamoDB lock). **No se acepta** estado local (`terraform.tfstate` en el repo).
* **Estructura de archivos mínima:** organizar el código Terraform en archivos separados: `provider.tf` (configuración del provider y backend), `variables.tf` (declaración de variables), `main.tf` (recursos principales) y `outputs.tf` (valores de salida). No colocar todo en un único archivo.
* **Terraform plan en CI/CD:** el pipeline debe ejecutar `terraform plan` en cada Pull Request y `terraform apply`**solo** al mergear a la rama principal.

El objetivo es construir una arquitectura **híbrida** escalable (tipo 1, inicial). Presenten el diagrama de arquitectura y justifiquen, para cada servicio, dónde lo despliegan (local vs nube) y por qué.

![Hit #2 — Sobel con Offloading en la Nube](https://dpetrocelli.github.io/sd2026/assets/images/tp3_hit2.png)

---

### Hit #3 — Sobel contenerizado, asincrónico y escalable (base del TP Integrador)

A diferencia del esquema híbrido del Hit #2, ahora la idea es construir una infraestructura **100% en la nube** pero con un enfoque diferente: orquestada con Kubernetes [K8S]. El paper de Burns et al. [BURNS16] —“Borg, Omega, and Kubernetes”— traza el linaje conceptual de K8s desde los sistemas de orquestación internos de Google y explica por qué se diseñó como está.

#### 1. Desplegar con Terraform un cluster de Kubernetes (GKE)

Este cluster va a manejar todos los recursos del sistema: tanto los servicios de infraestructura (RabbitMQ, Redis) como los componentes de aplicación (frontend, backend, split, joiner). La configuración mínima exigida es:

1. **Nodegroup de infraestructura:** aloja los servicios base (RabbitMQ, Redis, observabilidad).
2. **Nodegroup de aplicaciones:** aloja los componentes del sistema (frontend, backend, split, joiner).
3. **Pool de workers fuera del cluster:** máquinas virtuales gestionadas con Terraform aparte (no son nodos de Kubernetes), encargadas de las tareas de cómputo intensivo. Mantenerlas fuera del cluster permite escalarlas de manera independiente y aprovechar tipos de instancia distintos sin cambiar el `nodepool` de GKE.

#### Requisitos de mensajería (aplicando los patrones del Hit #0)

* **Dead Letter Queue:** configurar una DLX en las colas de procesamiento Sobel. Si un worker falla al procesar un fragmento de imagen (crash, timeout, *out of memory*), el mensaje debe ir a la DLQ en lugar de perderse. Implementar un servicio que monitoree la DLQ y re-asigne los fragmentos fallidos a otros workers.
* **Retry con exponential backoff:** cuando un worker no puede contactar a RabbitMQ o Redis (por ejemplo, durante un despliegue o reinicio), debe reintentar la conexión con backoff exponencial (1s, 2s, 4s, 8s, máximo 30s). **No implementar retry infinito sin backoff:** genera tormentas de reconexión que empeoran el problema.
* **Pub/Sub para notificación de resultados:** cuando un worker completa un fragmento, publicar el resultado en un *exchange*`fanout` para que tanto el servicio *joiner* como el dashboard de monitoreo reciban la notificación.

![Hit #3 — Arquitectura Kubernetes (GKE)](https://dpetrocelli.github.io/sd2026/assets/images/tp3_hit3.png)

#### 2. Construir los pipelines de despliegue

* **Pipeline 1 — Infraestructura:** construye el cluster de Kubernetes con Terraform.
  * **Pipeline 1.1** — Despliega los servicios base (RabbitMQ, Redis y otros).
  * **Pipeline 1.2 … 1.N** — Despliega cada aplicación (frontend, backend, split, joiner).
* **Pipeline 2 — Workers dinámicos:** despliega y destruye las máquinas virtuales que actúan como workers. Objetivo deseable: que el dimensionamiento sea **dinámico** según la cola pendiente.

---

### Hit #3 (cont.) — Análisis de desempeño bajo carga

Para evaluar el desempeño de la plataforma vamos a medir los tiempos de respuesta en diferentes escenarios, modificando tres variables:

* **V1 — Tamaño de los datos:** 1 KB, 10 KB, 100 KB, 1 MB, 10 MB, 100 MB.
* **V2 — Concurrencia:** distintos niveles de peticiones concurrentes.
* **V3 — Cantidad de workers:** se ajusta el número de procesos o threads disponibles para manejar las peticiones.

> **Nota sobre quotas:** las cuentas gratuitas de los cloud providers tienen límites de VMs por región/zona. Si necesitan escalar a más nodos para los experimentos, distribúyanlos entre varias regiones para no chocar contra el cupo.

El objetivo es entender cómo la plataforma responde al modificar estas variables, identificar la capacidad real de escalabilidad y los posibles cuellos de botella. Los resultados se presentan en una tabla con el tiempo de respuesta para cada combinación de variables, dando una visión clara de la evolución del desempeño bajo distintas condiciones.

**Herramienta de load testing:** usar una herramienta de benchmarking como **Locust** [LOCUST] o **k6** [K6]. Permiten definir escenarios reproducibles y generar reportes comparables. Documenten la configuración del test (cantidad de *virtual users*, *ramp-up*, duración) y presenten los resultados con métricas estándar: latencia p50/p95/p99, throughput (req/s) y tasa de errores.

---

### Hit #4 — Observabilidad (Prometheus + Grafana)

La observabilidad es un pilar de las prácticas modernas de **Site Reliability Engineering** [BEYER16]: sin métricas, logs y trazas no se pueden definir SLOs ni razonar sobre la salud del sistema en producción. Desplieguen Prometheus [PROM, BRAZIL18] y Grafana [GRAF] en el cluster de Kubernetes para monitorear la plataforma:

1. **Instalación:** instalar Prometheus y Grafana en el nodegroup de infraestructura. Pueden usar el Helm chart oficial `prometheus-community/kube-prometheus-stack`.
2. **Instrumentación:** instrumentar los servicios (backend, workers, split, joiner) para que exporten métricas custom: tareas procesadas, tareas en cola, tiempo de procesamiento por tarea y errores.
3. **Dashboard:** crear un dashboard en Grafana que muestre como mínimo:
   * Uso de CPU y memoria por pod/nodo.
   * Mensajes procesados en RabbitMQ (publicados vs consumidos vs en cola).
   * Latencia de procesamiento de tareas (p50, p95, p99).
   * Tasa de errores.
4. **Alertas:** configurar al menos una alerta básica (por ejemplo: cola de RabbitMQ supera un umbral, o un worker no responde en X segundos).

---

</details>

<details open="" class="section-collapsible">
<h3 id="cloud-computing--papers-fundacionales">Cloud Computing — papers
fundacionales</h3>
<ul data-tight="true"><li><p><strong>[ARMBRUST10]</strong> Armbrust, M., Fox, A., Griffith, R.,
Joseph, A.D., Katz, R., Konwinski, A., Lee, G., Patterson, D., Rabkin,
A., Stoica, I. & Zaharia, M. (2010). “A View of Cloud Computing”.
<em>Communications of the ACM</em>, 53(4), 50–58. <a href="https://www2.eecs.berkeley.edu/Pubs/TechRpts/2009/EECS-2009-28.pdf">PDF</a></p></li><li data-node-id="20260528143557-35vsktt"><p><strong>[BREWER00]</strong> Brewer, E. (2000). “Towards Robust
Distributed Systems”. PODC Keynote — origen del <strong>Teorema
CAP</strong>. <a href="https://people.eecs.berkeley.edu/~brewer/cs262b-2004/PODC-keynote.pdf">PDF</a></p></li><li><p><strong>[KUM10]</strong> Kumar, K. & Lu, Y. (2010). “Cloud
Computing for Mobile Users: Can Offloading Computation Save Energy?”.
Purdue University. <a href="https://www.cs.purdue.edu/homes/bb/mobile-cloud-survey.pdf">PDF</a></p></li><li data-node-id="20260528143557-ochv7ao"><p><strong>[NIST800-145]</strong> Mell, P. & Grance, T. (2011).
<em>The NIST Definition of Cloud Computing</em>. NIST Special
Publication 800-145. <a href="https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-145.pdf">PDF</a></p></li></ul>
<h3 id="kubernetes-y-orquestación">Kubernetes y orquestación</h3>
<ul data-tight="true"><li><p><strong>[BURNS16]</strong> Burns, B., Grant, B., Oppenheimer, D.,
Brewer, E. & Wilkes, J. (2016). “Borg, Omega, and Kubernetes”.
<em>Communications of the ACM</em>, 59(5), 50–57. <a href="https://queue.acm.org/detail.cfm?id=2898444">ACM</a></p></li><li data-node-id="20260528143557-1idnugd"><p><strong>[BUR18]</strong> Burns, B. (2018). <em>Designing Distributed
Systems: Patterns and Paradigms for Scalable, Reliable Services</em>.
O’Reilly Media.</p></li><li><p><strong>[K8S]</strong> Kubernetes Documentation. <a href="https://kubernetes.io/docs/">kubernetes.io/docs</a></p></li></ul>
<h3 id="observabilidad-y-sre">Observabilidad y SRE</h3>
<ul data-tight="true"><li><p><strong>[BEYER16]</strong> Beyer, B., Jones, C., Petoff, J. &
Murphy, N.R. (2016). <em>Site Reliability Engineering: How Google Runs
Production Systems</em>. O’Reilly. — Caps. 4–6: SLIs/SLOs y monitoreo.
<a href="https://sre.google/sre-book/table-of-contents/">Free
online</a></p></li><li data-node-id="20260528143557-p2c7hdy"><p><strong>[BRAZIL18]</strong> Brazil, B. (2018). <em>Prometheus: Up
& Running — Infrastructure and Application Performance
Monitoring</em>. O’Reilly.</p></li><li><p><strong>[GRAF]</strong> Grafana Documentation. <a href="https://grafana.com/docs/grafana/">grafana.com/docs/grafana</a></p></li><li data-node-id="20260528143557-ugsnq2c"><p><strong>[PROM]</strong> Prometheus — Monitoring system & time
series database. <a href="https://prometheus.io/docs/">prometheus.io/docs</a></p></li></ul>
<h3 id="iac-load-testing-y-otras-herramientas">IaC, Load Testing y otras
herramientas</h3>
<ul data-tight="true"><li><p><strong>[CBURST]</strong> Cloud-bursting — Atlassian. <a href="https://www.atlassian.com/es/continuous-delivery/principles/cloud-bursting">atlassian.com/…/cloud-bursting</a></p></li><li data-node-id="20260528143557-m2pr5qq"><p><strong>[K6]</strong> k6 — Load testing for engineering teams. <a href="https://k6.io">k6.io</a></p></li><li><p><strong>[LOCUST]</strong> Locust — Open source load testing tool. <a href="https://locust.io">locust.io</a></p></li><li data-node-id="20260528143557-qzdav7d"><p><strong>[RMQ]</strong> RabbitMQ Documentation. <a href="https://www.rabbitmq.com/tutorials">rabbitmq.com/tutorials</a></p></li><li><p><strong>[SOB68]</strong> Sobel, I. & Feldman, G. (1968). “A 3x3
Isotropic Gradient Operator for Image Processing”. Stanford AI
Project.</p></li><li data-node-id="20260528143557-d88oucr"><p><strong>[TF]</strong> Terraform by HashiCorp — Documentation. <a href="https://developer.hashicorp.com/terraform/docs">developer.hashicorp.com/terraform/docs</a></p></li></ul>
  </details>

### Cloud Computing — papers fundacionales

* **[ARMBRUST10]** Armbrust, M., Fox, A., Griffith, R., Joseph, A.D., Katz, R., Konwinski, A., Lee, G., Patterson, D., Rabkin, A., Stoica, I. & Zaharia, M. (2010). “A View of Cloud Computing”. *Communications of the ACM*, 53(4), 50–58. [PDF](https://www2.eecs.berkeley.edu/Pubs/TechRpts/2009/EECS-2009-28.pdf)
* **[BREWER00]** Brewer, E. (2000). “Towards Robust Distributed Systems”. PODC Keynote — origen del **Teorema CAP**. [PDF](https://people.eecs.berkeley.edu/~brewer/cs262b-2004/PODC-keynote.pdf)
* **[KUM10]** Kumar, K. & Lu, Y. (2010). “Cloud Computing for Mobile Users: Can Offloading Computation Save Energy?”. Purdue University. [PDF](https://www.cs.purdue.edu/homes/bb/mobile-cloud-survey.pdf)
* **[NIST800-145]** Mell, P. & Grance, T. (2011). *The NIST Definition of Cloud Computing*. NIST Special Publication 800-145. [PDF](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-145.pdf)

### Kubernetes y orquestación

* **[BURNS16]** Burns, B., Grant, B., Oppenheimer, D., Brewer, E. & Wilkes, J. (2016). “Borg, Omega, and Kubernetes”. *Communications of the ACM*, 59(5), 50–57. [ACM](https://queue.acm.org/detail.cfm?id=2898444)
* **[BUR18]** Burns, B. (2018). *Designing Distributed Systems: Patterns and Paradigms for Scalable, Reliable Services*. O’Reilly Media.
* **[K8S]** Kubernetes Documentation. [kubernetes.io/docs](https://kubernetes.io/docs/)

### Observabilidad y SRE

* **[BEYER16]** Beyer, B., Jones, C., Petoff, J. & Murphy, N.R. (2016). *Site Reliability Engineering: How Google Runs Production Systems*. O’Reilly. — Caps. 4–6: SLIs/SLOs y monitoreo. [Free online](https://sre.google/sre-book/table-of-contents/)
* **[BRAZIL18]** Brazil, B. (2018). *Prometheus: Up & Running — Infrastructure and Application Performance Monitoring*. O’Reilly.
* **[GRAF]** Grafana Documentation. [grafana.com/docs/grafana](https://grafana.com/docs/grafana/)
* **[PROM]** Prometheus — Monitoring system & time series database. [prometheus.io/docs](https://prometheus.io/docs/)

### IaC, Load Testing y otras herramientas

* **[CBURST]** Cloud-bursting — Atlassian. [atlassian.com/…/cloud-bursting](https://www.atlassian.com/es/continuous-delivery/principles/cloud-bursting)
* **[K6]** k6 — Load testing for engineering teams. [k6.io](https://k6.io)
* **[LOCUST]** Locust — Open source load testing tool. [locust.io](https://locust.io)
* **[RMQ]** RabbitMQ Documentation. [rabbitmq.com/tutorials](https://www.rabbitmq.com/tutorials)
* **[SOB68]** Sobel, I. & Feldman, G. (1968). “A 3x3 Isotropic Gradient Operator for Image Processing”. Stanford AI Project.
* **[TF]** Terraform by HashiCorp — Documentation. [developer.hashicorp.com/terraform/docs](https://developer.hashicorp.com/terraform/docs)

</details>
