# Advanced Monitoring — Flask + Observability Stack on AWS EC2

End-to-end observability reference for a Flask + MySQL web app: Prometheus metrics, Grafana dashboards, Jaeger distributed tracing via OpenTelemetry, structured JSON logs shipped to CloudWatch, all fronted by an nginx reverse proxy and deployed to AWS EC2 through a Jenkins → Terraform → Ansible pipeline.

The project demonstrates the **RED method** (Rate, Errors, Duration) plus system metrics and trace-to-log correlation, with click-through links from Grafana dashboard panels into specific Jaeger traces.

---

## 1. Architecture

```text
                  +----------------------------+
  Browser ----->  | nginx (reverse-proxy:80)   |
                  |  /api/      -> web:5000    |
                  |  /monitoring/ -> grafana   |
                  |  /jaeger/   -> jaeger      |
                  +-------------+--------------+
                                |
   +----------------------------+----------------------------+
   |                |                 |              |       |
   v                v                 v              v       v
 web:5000      grafana:3000       jaeger:16686    prometheus  node-
 (Flask +      (dashboards +      (UI + query)    :9090       exporter
  OTel SDK)     alert rules)            ^         (scrape)    :9100
   |                ^                    |             ^         ^
   |                | datasource         | spans       | scrape  |
   |                | (proxy)            | (thrift     |         |
   |                |                    |  6831/udp)  |         |
   +----------------+--------------------+-------------+---------+
   |
   | structured JSON logs (stdout)
   v
 awslogs Docker driver  -->  AWS CloudWatch Logs (/docker/web-app)
```

**Data flows**

- **Metrics:** Flask app exposes `/metrics`; Prometheus scrapes `web:5000` + `node-exporter:9100` every 15s.
- **Traces:** Flask app sends spans to Jaeger via the Thrift agent on UDP `6831`. `FlaskInstrumentor`, `RequestsInstrumentor`, and `MySQLInstrumentor` auto-instrument the request, outbound HTTP, and DB calls.
- **Logs:** App writes JSON to stdout; the awslogs Docker driver ships them to CloudWatch. Each log line carries `trace_id` and `span_id` so log entries can be pivoted to the matching Jaeger trace.
- **Dashboard → Trace links:** A Grafana panel queries Jaeger directly (via the configured datasource) for recent error traces; clicking a row opens the trace in the standalone Jaeger UI.

---

## 2. Service inventory

| Service        | Image                              | Internal port | Public route via nginx | Purpose                                |
|----------------|-------------------------------------|----------------|------------------------|----------------------------------------|
| `web`          | `<docker-hub-user>/<repo>:latest`   | 5000           | `/api/`                | Flask app + OTel SDK + Prometheus client |
| `db`           | `mysql:8.0`                         | 3306           | —                      | App database                           |
| `prometheus`   | `prom/prometheus:v2.53.0`           | 9090           | — (host:9090)          | Metrics scrape + alert evaluation      |
| `grafana`      | `grafana/grafana:11.1.0`            | 3000           | `/monitoring/`         | Dashboards, alert pages                |
| `jaeger`       | `jaegertracing/all-in-one:1.56`     | 16686 / 6831   | `/jaeger/`             | Trace collection + UI                  |
| `node-exporter`| `prom/node-exporter:v1.8.2`         | 9100           | —                      | Host CPU / memory metrics              |
| `nginx`        | `nginx:1.27-alpine`                 | 80             | `:80`                  | Reverse proxy                          |

---

## 3. Local development

```bash
# 1. Provide required env vars
cp .env.example .env  # if you have one; otherwise create .env with the keys below
# Required keys: MYSQL_ROOT_PASSWORD, MYSQL_DATABASE, WEB_IMAGE,
#                DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT,
#                GF_ADMIN_USER, GF_ADMIN_PASSWORD, GF_SERVER_DOMAIN

# 2. Bring the stack up
docker compose up -d

# 3. Generate traffic
./scripts/load-test.sh
```

Then open:

- App API:        `http://localhost/api/topics`
- Grafana:        `http://localhost/monitoring/` (admin / value of `GF_ADMIN_PASSWORD`)
- Jaeger UI:      `http://localhost/jaeger/`
- Prometheus UI:  `http://localhost:9090/`

---

## 4. Observability deep-dive

### 4.1 Metrics

Custom application metrics ([web/metrics.py](web/metrics.py)):

| Metric                              | Type      | Labels                        |
|-------------------------------------|-----------|-------------------------------|
| `http_requests_total`               | Counter   | `method`, `endpoint`, `status_code` |
| `http_errors_total`                 | Counter   | `method`, `endpoint`, `status_code` |
| `http_request_duration_seconds`     | Histogram | `method`, `endpoint`              |

Errors and latency observations carry **exemplars** with the active `trace_id`, allowing operators to jump from a Prometheus data point to the originating trace.

System metrics come from `node-exporter` (CPU, memory).

### 4.2 Logs (JSON + trace correlation)

[web/logging_config.py](web/logging_config.py) installs:

- `CustomJsonFormatter` (python-json-logger) — every log line is single-line JSON.
- `TraceContextFilter` attached to the **handler** (not the logger root) so it stamps `trace_id` / `span_id` from the active OTel span onto every record, including those emitted by child loggers.

Sample log entry:

```json
{
  "timestamp": "2026-05-04T10:56:03.436643Z",
  "level": "INFO",
  "name": "middleware",
  "message": "Request processed: PUT /api/topics/2400 200",
  "method": "PUT",
  "path": "/api/topics/2400",
  "status_code": 200,
  "latency": 0.047,
  "trace_id": "96a14f0f8d3599952910fef395a327ea",
  "span_id": "f2347bcf7af397aa"
}
```

Logs are written to stdout and shipped to CloudWatch Logs group `/docker/web-app` via the Docker `awslogs` driver (configured in [docker-compose.yml](docker-compose.yml)).

### 4.3 Tracing

[web/tracing.py](web/tracing.py) sets up:

- A `TracerProvider` with `service.name = advanced-monitoring-webapp`.
- A `BatchSpanProcessor` exporting to the Jaeger agent over Thrift UDP.
- Auto-instrumentation for Flask, outbound `requests`, and the MySQL driver.

**Error tagging.** The middleware ([web/middleware.py](web/middleware.py)) calls `span.set_status(StatusCode.ERROR, ...)` on any 4xx/5xx response. The Jaeger Thrift exporter translates this to the legacy `error=true` span tag, so:

- Jaeger UI renders error spans in red.
- A dashboard panel can search Jaeger with `tags=error=true` and surface recent error traces.

### 4.4 Dashboard

`Web App Observability — RED, System, Tracing` ([webapp-observability.json](monitoring/grafana/dashboards/webapp-observability.json)):

| Panel                                       | Source     |
|---------------------------------------------|------------|
| Request Rate (RPS, by route)                | Prometheus |
| Error Rate (by route)                       | Prometheus |
| 95th Percentile Latency (by route)          | Prometheus |
| Aggregate Request Latency (p50 / p90 / p99) | Prometheus |
| Aggregate Error Rate %                      | Prometheus |
| Aggregate Requests per Second               | Prometheus |
| CPU Usage (%)                               | Prometheus (node-exporter) |
| Memory Usage (MB)                           | Prometheus (node-exporter) |
| Recent Error Traces (table + click-through) | Jaeger     |

The Recent Error Traces panel includes a data link to `/jaeger/trace/${__data.fields.traceID}` for one-click drill-down.

### 4.5 Alerts

Defined in [monitoring/prometheus/alerts.yml](monitoring/prometheus/alerts.yml):

- **HighErrorRate** — error rate > 5% over 10 minutes.
- **HighLatency** — p95 latency > 300 ms over 10 minutes.

Each alert annotation includes a relative `jaeger_url` so the alert details page links to a pre-filtered Jaeger search for the affected service.

---

## 5. Reverse-proxy routing notes

nginx ([reverse-proxy/nginx.conf](reverse-proxy/nginx.conf)) handles three intertwined routing concerns. They are subtle enough to be worth calling out:

1. **`/api/` → `web:5000`.** Standard reverse proxy.

2. **`/monitoring/` → `grafana:3000`.** Grafana runs with `GF_SERVER_SERVE_FROM_SUB_PATH=true` and `GF_SERVER_ROOT_URL` referencing `GF_SERVER_DOMAIN`, so it correctly serves assets under `/monitoring/`.

3. **`/jaeger/` → `jaeger:16686`.** Jaeger is started with `QUERY_BASE_PATH=/jaeger`, which moves both the UI and the query API under `/jaeger/*`. The nginx `proxy_pass` target intentionally has **no trailing slash**, so the full URI (including `/jaeger/...`) is forwarded — Jaeger requires it.

4. **`/monitoring/jaeger/` → 301 redirect to `/jaeger/...`.** Grafana 11 prepends its sub-path (`/monitoring/`) to root-relative panel data link URLs at render time, so a click on a trace link arrives at `/monitoring/jaeger/trace/<id>`. We **redirect** (rather than rewrite) so the browser ends up at `/jaeger/trace/<id>` — Jaeger UI's React Router uses `window.location.pathname` and only routes URLs under its `QUERY_BASE_PATH` basename. A rewrite would leave the address bar at `/monitoring/jaeger/...` and the SPA would render its "Page not found" view.

The Jaeger datasource in Grafana ([datasource.yml](monitoring/grafana/provisioning/datasources/datasource.yml)) is configured with `url: http://jaeger:16686/jaeger` because the `access: proxy` mode means Grafana's backend talks to Jaeger directly over the Docker network — bypassing nginx — and Jaeger's API is also under `/jaeger/`.

---

## 6. CI/CD pipeline

Push-to-deploy via Jenkins → Docker Hub → Ansible → EC2.

```text
git push  ->  GitHub webhook  ->  Jenkins pipeline (Jenkinsfile)
                                   |
                                   |--  Load .env (file credential: app_env_file)
                                   |--  Checkout
                                   |--  Install + build Python deps
                                   |--  Unit Test (placeholder)
                                   |--  Docker build  -> tag $DOCKER_IMAGE:latest
                                   |--  Push to Docker Hub
                                   |--  Deploy to EC2
                                   |       (SSH credential: ec2_ssh
                                   |        Ansible -> docker-compose up + health check)
                                   |--  Cleanup
```

### 6.1 Required Jenkins credentials

The pipeline references these credential IDs literally — they must match exactly:

| ID             | Type                       | Contents                                          |
|----------------|----------------------------|---------------------------------------------------|
| `app_env_file` | Secret file                | `.env` with the keys listed in [§6.2](#62-jenkins-env-file-keys) |
| `ec2_ssh`      | SSH Username + private key | Username `ec2-user`, the PEM emitted by Terraform |

### 6.2 Jenkins env-file keys

```dotenv
DOCKER_HUB_USER=<dockerhub-username>
DOCKER_HUB_PASSWORD=<dockerhub-token>
DOCKER_HUB_REPO=<repo-name>
EC2_PUBLIC_IP=<from terraform output>
DB_HOST=db
DB_PORT=3306
DB_NAME=topics_db
DB_USER=root
DB_PASSWORD=<password>
GF_ADMIN_USER=admin
GF_ADMIN_PASSWORD=<password>
GF_SERVER_DOMAIN=<ec2-public-dns>
```

The `Load .env` stage validates required keys and fails fast on any missing.

---

## 7. Infrastructure (Terraform + Ansible)

### 7.1 Terraform — first-time setup

```bash
# Bootstrap remote state (S3 + DynamoDB lock)
cd infra/backend-bootstrap
terraform init && terraform apply

# Provision SG, key pair, EC2, generate Ansible inventory
cd ..
terraform init && terraform apply
terraform output           # capture instance_public_ip / dns
```

Useful outputs:

- `instance_public_ip` — paste into the Jenkins env file as `EC2_PUBLIC_IP`.
- `instance_public_dns` — use as `GF_SERVER_DOMAIN`.
- `ansible_private_key_path` — load into Jenkins SSH credential `ec2_ssh`.

### 7.2 Ansible

The `app_compose` role ([ansible/roles/app_compose/](ansible/roles/app_compose/)) runs on the EC2 host and:

- Stages `docker-compose.yml`, the database init script, and `monitoring/` + `reverse-proxy/` configs under `/opt/multicontainer`.
- Renders `.env` from `templates/.env.j2` (variables come from `vault.yml` / Jenkins env).
- Logs into Docker Hub with the supplied credentials.
- Runs `docker compose up`, then probes `/api/health` until 200.

---

## 8. Validation

```bash
# App
curl -fsS http://<host>/api/health
curl -fsS http://<host>/api/topics

# Metrics
curl -fsS http://<host>:9090/-/healthy
curl -s http://<host>:9090/api/v1/targets | jq '.data.activeTargets[].health'

# Jaeger query API (note the /jaeger prefix)
curl -s 'http://<host>/jaeger/api/services'

# Trace search used by the dashboard panel
curl -s 'http://<host>/jaeger/api/traces?service=advanced-monitoring-webapp&tags=%7B%22error%22%3A%22true%22%7D&limit=10' | jq '.data | length'
```

Reload Prometheus rules without restart:

```bash
docker compose exec prometheus kill -HUP 1
```

Reload nginx after editing `nginx.conf`:

```bash
docker compose exec nginx nginx -s reload
```

---

## 9. Common failure modes

| Symptom                                                       | Likely cause                                                                                       | Fix |
|---------------------------------------------------------------|----------------------------------------------------------------------------------------------------|------|
| Recent Error Traces panel empty even though there are errors  | Spans aren't tagged `error=true` because middleware doesn't set span status on 4xx/5xx              | Confirm `span.set_status(StatusCode.ERROR, ...)` in [web/middleware.py](web/middleware.py) |
| Jaeger UI returns 1908-byte HTML for `/jaeger/static/*.js`    | nginx `proxy_pass` had a trailing slash, stripping the `/jaeger/` prefix before forwarding         | Remove the trailing slash on `proxy_pass http://jaeger:16686;` |
| Trace link from dashboard renders Grafana "Page not found"    | nginx forwards `/monitoring/jaeger/...` to Grafana instead of redirecting to `/jaeger/...`         | Use a 301 redirect, not a rewrite, in `location /monitoring/jaeger/` |
| Trace link reaches Jaeger but shows "Error / Back home"       | Browser still at `/monitoring/jaeger/...`; Jaeger SPA's React Router only matches `/jaeger/...`     | Same as above — must be a browser-visible redirect |
| Alert links contain `localhost`                               | `GF_SERVER_DOMAIN` not set or alert annotation hard-codes `localhost`                              | Set `GF_SERVER_DOMAIN`; use relative URLs in alert annotations or template via `external_labels` |
| Logs missing `trace_id` / `span_id`                           | `TraceContextFilter` attached to a logger instead of the handler — child-logger records bypass it  | Attach the filter to the handler in [web/logging_config.py](web/logging_config.py) |
| werkzeug access logs have `trace_id: null`                    | werkzeug logs run after `teardown_request`; the OTel span is already ended                          | Expected — silence werkzeug INFO logs (`logging.getLogger("werkzeug").setLevel(WARNING)`) |
| Pipeline fails at `Load .env`                                 | A required key is missing from the Jenkins file credential                                          | Update the `app_env_file` credential and rerun |
| `Deploy to EC2` fails with permission denied                  | Wrong SSH credential ID, wrong username, or stale PEM                                              | Verify credential ID is exactly `ec2_ssh`, username `ec2-user`, key matches active EC2 key pair |

---

## 10. Hardening checklist

- Restrict `allowed_ssh_cidr` to trusted IPs.
- Replace MySQL `root` with a least-privilege application user.
- Replace the `Unit Test` placeholder with a real test invocation.
- Add image and dependency scanning (e.g., Trivy) to the pipeline.
- Add HTTPS termination (ALB or nginx + ACM/Let's Encrypt).
- Rotate Docker Hub tokens and the EC2 key pair on a schedule.

---

## 11. Repository map

```
.
├── Jenkinsfile                            CI/CD pipeline definition
├── docker-compose.yml                     Service composition
├── ansible/                               Provisioning playbooks + roles
├── infra/                                 Terraform (backend-bootstrap + main)
├── db/init.sql                            MySQL schema bootstrap
├── monitoring/
│   ├── prometheus/{prometheus,alerts}.yml Scrape config + alert rules
│   └── grafana/
│       ├── provisioning/datasources/      Prometheus + Jaeger datasources
│       └── dashboards/                    Provisioned dashboards
├── reverse-proxy/nginx.conf               Public routing + Jaeger redirects
├── scripts/load-test.sh                   Traffic generator
└── web/                                   Flask app, OTel setup, metrics
```

---

Author: Jean-Luc Ishimwe
