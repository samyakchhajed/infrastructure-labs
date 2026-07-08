import flask
import time
import random
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from werkzeug.serving import make_server
import threading

# Prometheus metrics
request_count = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
accepted_jobs = Counter('jobs_accepted_total', 'Total jobs accepted', [])
request_latency = Histogram('api_request_duration_seconds', 'API request latency', ['endpoint'])

# Intentional bad instrumentation: high cardinality label (user_id)
bad_instrumentation = Counter('api_requests_by_user', 'Requests by user (BAD: unbounded cardinality)', ['user_id'])

app = flask.Flask(__name__)


@app.route('/jobs', methods=['POST'])
def submit_job():
    """Accept a job and put it in the queue."""
    start = time.time()
    
    try:
        # Get queue and logger from Flask global context
        queue_obj = flask.current_app.config['queue']
        logger = flask.current_app.config['logger']
        
        # Get request parameters for controlled scenarios
        mode = flask.request.args.get('mode', 'normal')
        user_id = flask.request.args.get('user_id', 'unknown')
        
        # Simulate latency if requested
        if mode == 'latency':
            time.sleep(random.uniform(0.5, 2.0))
        
        # Simulate error if requested
        if mode == 'error':
            request_count.labels(method='POST', endpoint='/jobs', status='500').inc()
            bad_instrumentation.labels(user_id=user_id).inc()
            return {'error': 'Simulated failure'}, 500
        
        # Create job
        job = {
            'id': f"job_{int(time.time())}_{random.randint(1000, 9999)}",
            'mode': mode,
            'user_id': user_id,
            'created_at': time.time()
        }
        
        # Put job in queue
        queue_obj.put(job)
        accepted_jobs.inc()
        
        duration = time.time() - start
        request_latency.labels(endpoint='/jobs').observe(duration)
        request_count.labels(method='POST', endpoint='/jobs', status='200').inc()
        bad_instrumentation.labels(user_id=user_id).inc()
        
        logger.info(f"Accepted job {job['id']} (mode={mode})")
        return {'job_id': job['id']}, 200
    
    except Exception as e:
        request_count.labels(method='POST', endpoint='/jobs', status='500').inc()
        logger = flask.current_app.config.get('logger')
        if logger:
            logger.error(f"Error processing request: {e}")
        return {'error': str(e)}, 500


@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


def start_api(config):
    """Start the Flask API server."""
    queue_obj = config['queue']
    stop_event = config['stop_event']
    logger = config['logger_api']
    port = config['port']
    
    # Store config in Flask app
    app.config['queue'] = queue_obj
    app.config['logger'] = logger
    app.config['stop_event'] = stop_event
    
    logger.info(f"Starting API on port {port}...")
    
    # Create WSGI server instead of using app.run()
    # Bind to 0.0.0.0 so Docker containers can reach it via service name
    server = make_server('0.0.0.0', port, app, threaded=True)
    
    # Run server in a thread
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    
    logger.info(f"API server listening on 0.0.0.0:{port}")
    
    # Keep running until stop_event is set
    while not stop_event.is_set():
        time.sleep(1)
    
    logger.info("Stopping API server...")
    server.shutdown()
    logger.info("API stopped.")

