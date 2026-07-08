# Lab 2 --- Monitoring the Monitor and Alert Delivery

A local observability lab for testing whether the monitoring and alert-delivery path itself can be trusted.

## Engineering Question

**How do you know the monitoring and alerting path itself is working?**

## System Architecture

API /metrics ---> Prometheus ---> Alertmanager ---> Webhook Receiver

The application and its Prometheus instrumentation were reused from Lab 1. This lab extended the path with alert rules, Alertmanager, and a local webhook receiver.

## Technology

-   Python 3.11
-   Flask
-   Prometheus
-   Prometheus alert rules
-   Alertmanager
-   Docker Compose

## Alert Rules

| Alert | Condition | Purpose |
|---|---|---|
| `AppTargetDown` | `up{job="app"} == 0` for 30 seconds | Test target failure and the alert lifecycle |
| `HighErrorRate` | HTTP 500 rate exceeds 20% of total request rate for 30 seconds | Distinguish application failure from target unavailability |
| `AlwaysFiring` | `vector(1)` | Continuously validate routing and notification delivery |

`AlwaysFiring` acted as a local heartbeat/dead-man-style test signal
independent of application behaviour.

## Experiment 1 --- Validate the Complete Path

With all services running, `AlwaysFiring` became active automatically.

Prometheus
→ evaluates AlwaysFiring
→ sends alert to Alertmanager
→ Alertmanager routes the alert
→ receiver accepts POST /alerts
→ receiver returns HTTP 200

**Finding:** a continuous test alert can validate the alerting path
independently of an application incident.

## Experiment 2 --- Alert Lifecycle and Recovery

The application container was stopped while Prometheus, Alertmanager,
and the receiver remained running.

The target-down rule used:

``` promql
up{job="app"} == 0
```

with `for: 30s`.

The observed lifecycle was:

Healthy
→ target unreachable
→ Pending
→ Firing
→ delivered to Alertmanager
→ delivered to receiver
→ application restarted
→ Resolved

The alert became Pending only after Prometheus detected the failed
scrape and evaluated the rule. It later became Firing after the
condition remained active long enough.

**Finding:** `for: 30s` does not mean an alert fires exactly 30 seconds
after the real-world failure begins. Scrape timing, evaluation timing,
and UI refresh timing also affect the visible transition.

## Experiment 3 --- Break the Final Receiver

Only the webhook receiver was stopped.

``` text
Prometheus:        working
Alert evaluation: working
Alertmanager:      working
Active alerts:     still visible
Receiver:          unavailable
Notification:      failing
```

Prometheus continued evaluating alerts and Alertmanager continued
displaying them. Alertmanager logs showed failed notification attempts.

After the receiver was restarted, Alertmanager retried and logged
`Notify success`.

delivery working
→ receiver unavailable
→ notification attempts fail
→ receiver returns
→ Alertmanager retries
→ notification succeeds

**Finding:** a firing alert and a healthy Alertmanager UI do not prove
that the downstream receiver received the notification.

## Experiment 4 --- Break Prometheus to Alertmanager Delivery

Only Alertmanager was stopped.

Prometheus continued to show `AlwaysFiring` as Firing, but logged errors
while trying to send alerts to the unavailable Alertmanager endpoint.

``` text
Prometheus:        working
Rule evaluation:   working
Alert:             firing
Alertmanager:      unavailable
Receiver delivery: impossible
```

The Alertmanager interface was unreachable while the service was
stopped.

After Alertmanager restarted, the active alert eventually reappeared in
its interface. This proved that Prometheus-to-Alertmanager communication
had recovered. No immediate new receiver delivery was observed, so the
lab does not claim that restarting Alertmanager caused a fresh
end-to-end notification.

**Finding:** alert evaluation and alert delivery are separate stages.
Prometheus can continue evaluating and displaying a firing alert while
the downstream alert-management stage is unavailable.

## Failure Isolation

The experiments distinguished two independent delivery failures:

``` text
Prometheus ---> Alertmanager -X-> Receiver
```

and:

``` text
Prometheus -X-> Alertmanager ---> Receiver
```

| Failure | Prometheus Alert State | Alertmanager UI | Failure Evidence |
|---|---|---|---|
| Receiver unavailable | Alert still firing | Alert still visible | Alertmanager logs show notification failure |
| Alertmanager unavailable | Alert still firing | UI unreachable | Prometheus logs show alert-send failure |

## Key Findings

-   A firing alert does not prove successful notification delivery.
-   Prometheus rule evaluation can continue while Alertmanager is unavailable.
-   Alertmanager can hold a valid active alert while its downstream receiver is unavailable.
-   Alert states move through inactive, pending, firing, and resolved according to rule conditions and timing.
-   A `for` duration is only one part of detection time; scrape and evaluation intervals also matter.
-   A heartbeat/dead-man-style alert provides a continuous signal for testing the path.
-   Logs at different stages can reveal which delivery link failed.
-   Recovery of one stage should not be assumed to prove immediate end-to-end delivery.

## Running the Lab

### Prerequisites

-   Python 3.11+
-   Docker Desktop with Docker Compose

### Start

``` powershell
docker compose up --build
```

### Interfaces

-   Application metrics: `http://localhost:5000/metrics`
-   Prometheus: `http://localhost:9090`
-   Alertmanager: `http://localhost:9093`
-   Receiver health endpoint: `http://localhost:5001/health`

### Stop and Start Individual Stages

``` powershell
docker compose stop app
docker compose start app

docker compose stop receiver
docker compose start receiver

docker compose stop alertmanager
docker compose start alertmanager
```

### Stop the Lab

``` powershell
docker compose down
```

## Limitations

-   The lab runs locally on a single machine.
-   The receiver is a local Flask webhook rather than an external paging
    or messaging service.
-   Alert timings are intentionally short for controlled testing.
-   The heartbeat rule is a local demonstration, not an externally
    monitored production dead-man switch.
-   Prometheus did not scrape Alertmanager, so Alertmanager's internal
    notification metrics were not investigated through PromQL.
-   The lab tests failure boundaries and delivery behaviour, not
    production high availability.

## Conclusion

The lab demonstrated that an alerting system is a chain of independent
stages.

Prometheus can evaluate a rule correctly while Alertmanager is
unavailable. Alertmanager can display an active alert while the final
receiver is unreachable. A firing alert therefore proves that a rule
condition is active at the evaluation stage; it does not prove that the
notification reached its destination.

The central result is that **the alert itself must not be confused with
successful alert delivery**.
