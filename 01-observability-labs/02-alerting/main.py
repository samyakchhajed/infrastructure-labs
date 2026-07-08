from app import start_api
from worker import start_worker
import logging, threading, queue, time

logging.basicConfig(level=logging.INFO)

def get_logger(component_name):
    """Create a logger with a component prefix."""
    logger = logging.getLogger(component_name)
    logger.setLevel(logging.INFO)
    
    # Only add handler once
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(f'[{component_name}] %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

def main():
    main_logger = get_logger("MAIN")
    
    # Create shared objects
    job_queue = queue.Queue()
    stop_event = threading.Event()
    
    # Shared config dict
    config = {
        "queue": job_queue,
        "stop_event": stop_event,
        "logger_api": get_logger("API"),
        "logger_worker": get_logger("WORKER"),
        "port": 5000
    }
    
    main_logger.info("Starting observability lab...")
    
    # Start API thread
    api_thread = threading.Thread(target=start_api, args=(config,), daemon=False)
    api_thread.start()
    main_logger.info("API thread started")
    
    # Start worker thread
    worker_thread = threading.Thread(target=start_worker, args=(config,), daemon=False)
    worker_thread.start()
    main_logger.info("Worker thread started")
    
    # Keep main thread alive and wait for Ctrl+C
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        main_logger.info("Received interrupt, stopping gracefully...")
        stop_event.set()  # Signal both threads to stop
        
        api_thread.join(timeout=5)
        worker_thread.join(timeout=5)
        
        main_logger.info("All threads stopped. Exiting.")

if __name__ == "__main__":
    main()