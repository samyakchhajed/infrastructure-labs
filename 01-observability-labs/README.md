# Observability Labs

Two local hands-on labs exploring how telemetry is interpreted and how failures propagate through a monitoring and alert-delivery system.

The labs progress from understanding application metrics to testing the reliability of the alerting path itself.

## Labs

| Lab | Engineering Question | Focus |
|---|---|---|
| [01 — Metrics and Instrumentation Behaviour](01-metrics/) | What does a metric actually represent, and how can bad instrumentation mislead an operator? | Prometheus metrics, PromQL, Grafana, latency, errors, backlog, health signals, and cardinality |
| [02 — Monitoring the Monitor and Alert Delivery](02-alerting/) | How do you know the monitoring and alerting path itself is working? | Alert lifecycle, Alertmanager, webhook delivery, retries, and independent alert-path failures |

## Progression

```text
Application Behaviour
        ↓
Metrics and Instrumentation
        ↓
Prometheus Queries
        ↓
Grafana Visualization
        ↓
Alert Rule Evaluation
        ↓
Alertmanager Routing
        ↓
Notification Delivery