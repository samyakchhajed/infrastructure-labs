import time
import random
from prometheus_client import Counter, Histogram, Gauge

# Prometheus metrics
jobs_completed = Counter('worker_jobs_completed_total', 'Total jobs completed', [])
jobs_failed = Counter('worker_jobs_failed_total', 'Total jobs failed', [])
jobs_in_progress = Gauge('worker_jobs_in_progress', 'Jobs currently being processed', [])
queue_depth = Gauge('worker_queue_depth', 'Current queue depth', [])
processing_duration = Histogram('worker_processing_duration_seconds', 'Job processing duration', [])


def start_worker(config):
    """Start the worker that consumes from the queue."""
    queue_obj = config['queue']
    stop_event = config['stop_event']
    logger = config['logger_worker']
    
    logger.info("Worker started, listening for jobs...")
    
    while not stop_event.is_set():
        try:
            # Non-blocking queue get with timeout
            try:
                job = queue_obj.get(timeout=1)
            except:
                # No job available, update queue depth and continue
                queue_depth.set(queue_obj.qsize())
                continue
            
            # Update queue depth
            queue_depth.set(queue_obj.qsize())
            
            # Mark job as in progress
            jobs_in_progress.inc()
            start_time = time.time()
            
            try:
                mode = job.get('mode', 'normal')
                job_id = job.get('id', 'unknown')
                
                logger.info(f"Processing {job_id} (mode={mode})")
                
                # Simulate processing based on mode
                if mode == 'normal':
                    time.sleep(random.uniform(0.1, 0.5))
                elif mode == 'latency':
                    time.sleep(random.uniform(1.0, 3.0))
                elif mode == 'error':
                    # Simulate failure
                    if random.random() < 0.5:
                        raise Exception("Simulated job failure")
                    time.sleep(0.2)
                elif mode == 'backlog':
                    # Simulate slow processing to create backlog
                    time.sleep(random.uniform(2.0, 4.0))
                else:
                    time.sleep(0.2)
                
                # Success
                jobs_completed.inc()
                logger.info(f"Completed {job_id}")
            
            except Exception as e:
                # Failure
                jobs_failed.inc()
                logger.error(f"Failed to process {job_id}: {e}")
            
            finally:
                # Update metrics
                jobs_in_progress.dec()
                duration = time.time() - start_time
                processing_duration.observe(duration)
                queue_obj.task_done()
        
        except Exception as e:
            logger.error(f"Worker error: {e}")
            time.sleep(1)
    
    logger.info("Worker stopped.")
