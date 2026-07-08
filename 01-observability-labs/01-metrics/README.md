# Lab 1 --- Metrics and Instrumentation Behaviour

A local observability lab for studying what metrics actually represent, how workload behaviour appears in Prometheus, and how poor instrumentation can mislead an operator.

## Engineering Question

**What does a metric actually represent, and how can bad instrumentation mislead an operator?**

## System Architecture

``` text
Traffic Generator ---> API ---> In-Memory Queue ---> Worker

API / metrics ---> Prometheus ---> Grafana
```

The Python application contains an API and worker connected through a shared in-memory queue. A traffic generator creates controlled normal, error, latency, backlog, and high-cardinality workloads. Prometheus scrapes the application's `/metrics` endpoint, and Grafana visualizes selected PromQL queries.

## Technology

-   Python 3.11
-   Flask
-   Prometheus Python client
-   Prometheus
-   PromQL
-   Grafana
-   Docker Compose

## Metric Design

| Metric | Type | Purpose |
|---|---|---|
| `api_requests_total` | Counter | Count API requests by method, endpoint, and HTTP status |
| `jobs_accepted_total` | Counter | Count jobs accepted into the queue |
| `api_request_duration_seconds` | Histogram | Record API request latency |
| `api_requests_by_user_total` | Counter | Demonstrate high cardinality through the `user_id` label |
| `worker_jobs_completed_total` | Counter | Count successfully completed jobs |
| `worker_jobs_failed_total` | Counter | Count failed jobs |
| `worker_jobs_in_progress` | Gauge | Track jobs currently being processed |
| `worker_queue_depth` | Gauge | Track current queued work |
| `worker_processing_duration_seconds` | Histogram | Record worker processing duration |

  --------------------------------------------------------------------------------------

The `user_id` label is intentionally poor instrumentation. It allows the number of time series to grow with the number of distinct users.

## Controlled Workloads

The traffic generator supports five modes:

  `normal` - Sends successful requests under ordinary processing behaviour

  `errors` - Mixes normal requests with simulated HTTP 500 failures

  `latency` - Adds request and worker delay

  `backlog` - Sends work faster than the slow worker can process it

  `high-cardinality` - Sends requests with many distinct `user_id` values

Example:

``` powershell
python traffic.py --mode normal --count 20 --rate 2
```

## Experiments and Findings

### 1. Counter Behaviour and Request Rate

Normal traffic was generated and the raw request counter was inspected first. The counter remained at its accumulated value after traffic stopped. It answered how many requests had occurred since the process started, but not how quickly requests were arriving.

The request rate was then calculated with:

``` promql
sum(rate(api_requests_total[1m]))
```

**Finding:** a raw counter stores cumulative events, while `rate()` converts counter growth over a time window into recent activity.

------------------------------------------------------------------------

### 2. Error Traffic and Error Percentage

The error workload produced separate request series for HTTP `200` and `500` status labels.

The failure percentage was calculated as:

``` promql
(sum(rate(api_requests_total{status="500"}[1m])) / sum(rate(api_requests_total[1m]))) * 100
```

One observed workload produced 11 failures from 20 requests, or 55%. The Prometheus graph fluctuated around the same range because the query used a moving one-minute rate window rather than the traffic generator's final total.

**Finding:** an error count shows how many failures occurred; an error ratio shows how severe those failures were relative to current traffic.

------------------------------------------------------------------------

### 3. Latency Distribution and p95

The latency workload deliberately slowed requests. p95 request latency was estimated from histogram buckets:

``` promql
histogram_quantile(0.95, sum by (le) (rate(api_request_duration_seconds_bucket[1m])))
```

Observed p95 latency reached approximately **2.3--2.4 seconds**.

**Finding:** histogram buckets preserve latency-distribution information, allowing percentiles to expose slow-tail behaviour that a single average can hide.

------------------------------------------------------------------------

### 4. Queue Backlog and Recovery

The backlog workload caused work to arrive faster than the worker could process it.

The queue-depth gauge was inspected with:

``` promql
worker_queue_depth
```

The observed queue depth peaked at **15** and later returned to **0** as the worker drained the backlog.

**Finding:** a gauge can rise and fall with current system state. Queue depth exposed temporary work accumulation that cumulative request and completion counters could not show directly.

------------------------------------------------------------------------

### 5. `up = 1` While Requests Fail

The error workload was used to compare scrape reachability with application correctness.

Prometheus continued to report:

``` promql
up{job="app"}
```

as `1`, while HTTP 500 responses were occurring.

The failure activity was visible with:

``` promql
sum(rate(api_requests_total{status="500"}[1m]))
```

**Finding:** `up = 1` means Prometheus successfully scraped the target. It does not prove that the application is successfully performing useful work.

------------------------------------------------------------------------

### 6. High-Cardinality Label Growth

The deliberately bad metric used `user_id` as a label. A controlled workload sent requests with many distinct user IDs.

Series count was inspected with:

``` promql
count(api_requests_by_user_total)
```

After the experiment, the metric had grown to **51 time series**.

**Finding:** every distinct label-value combination creates a separate time series. An unbounded identifier such as `user_id` can make cardinality grow with traffic diversity even when the metric itself appears useful.

## Grafana Dashboard

The final dashboard contained four panels:

* Request Rate - How much traffic is arriving?
* p95 Request Latency - Are requests becoming slow?
* Queue Depth - Is unfinished work accumulating?
* HTTP Error Percentage - What fraction of recent requests is failing?

The panels were intentionally limited to signals that answered operational questions. Viewing them over the same time window made traffic, latency, backlog, and failures easier to correlate.

## Key Findings

-   Raw counters and rates answer different questions: accumulated events versus recent activity.
-   Gauges are suitable for current state because they can increase and decrease.
-   Histogram buckets make percentile estimation possible.
-   Error ratios provide context that raw failure counts cannot.
-   Queue depth reveals imbalance between incoming and completed work.
-   `up = 1` proves scrape success, not application correctness.
-   Unbounded labels can create dangerous time-series growth.
-   A metric becomes misleading when it is interpreted as proving more than it actually measures.

## Running the Lab

### Prerequisites

-   Python 3.11+
-   Docker Desktop with Docker Compose

Install the Python dependencies if required:

``` powershell
pip install -r requirements
```

### Start the Stack

From the lab directory:

``` powershell
docker compose up --build
```

For later runs, the stack can be started in detached mode:

``` powershell
docker compose up -d
```

### Open the Interfaces

-   Application metrics: `http://localhost:5000/metrics`
-   Prometheus: `http://localhost:9090`
-   Grafana: `http://localhost:3000`

Grafana connects to Prometheus from inside the Docker network using:

``` text
http://prometheus:9090
```

### Generate Workloads

``` powershell
python traffic.py --mode normal --count 20 --rate 2
python traffic.py --mode errors --count 20 --rate 2
python traffic.py --mode latency --count 20 --rate 2
python traffic.py --mode backlog --count 20 --rate 3
python traffic.py --mode high-cardinality --count 50 --rate 5
```

Run high-cardinality traffic conservatively. The purpose is to observe series growth, not to stress the monitoring system.

### Stop the Lab

``` powershell
docker compose down
```

## Limitations

-   The system runs locally on a single machine.
-   The queue is in memory rather than an external queue service.
-   Traffic and failures are synthetic and deliberately controlled.
-   Application logic is intentionally simple so the lab can focus on metric behaviour.
-   The high-cardinality metric is intentionally unsafe and exists only to demonstrate the instrumentation problem.

## Conclusion

The lab showed that collecting metrics is not enough. Operational conclusions depend on what each metric actually represents and how it is queried.

A cumulative counter did not show current traffic rate. A healthy scrape target did not prove successful application work. A queue gauge revealed accumulating work that request totals could not. Histogram buckets exposed latency distribution, while an unbounded label silently multiplied time series.

The central result is that **monitoring becomes misleading when a metric is interpreted as answering a question it was never designed to answer**.