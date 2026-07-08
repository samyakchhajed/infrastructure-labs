import requests
import time
import random
import argparse


def generate_traffic(mode='normal', count=10, rate=1):
    """
    Generate controlled traffic to the API.
    
    Args:
        mode: 'normal', 'errors', 'latency', 'backlog', 'high-cardinality'
        count: number of requests
        rate: requests per second
    """
    base_url = 'http://localhost:5000'
    sent = 0
    successful = 0
    failed = 0
    
    print(f"Generating {count} requests in '{mode}' mode at {rate} req/s...")
    print(f"Target: {base_url}/jobs\n")
    
    for i in range(count):
        if mode == 'normal':
            params = {'mode': 'normal'}
        elif mode == 'errors':
            params = {'mode': 'error' if random.random() < 0.5 else 'normal'}
        elif mode == 'latency':
            params = {'mode': 'latency'}
        elif mode == 'backlog':
            params = {'mode': 'backlog'}
        elif mode == 'high-cardinality':
            # Send requests with many unique user_ids to cause cardinality explosion
            params = {'mode': 'normal', 'user_id': f'user_{random.randint(1, 10000)}'}
        else:
            params = {'mode': 'normal'}
        
        try:
            print(f"[{i+1}/{count}] Sending request with params: {params}...", end=' ', flush=True)
            response = requests.post(f'{base_url}/jobs', params=params, timeout=10)
            sent += 1
            
            if response.status_code == 200:
                successful += 1
                print(f"✓ 200")
            else:
                failed += 1
                print(f"✗ {response.status_code}")
        
        except requests.exceptions.Timeout:
            sent += 1
            failed += 1
            print(f"✗ TIMEOUT")
        except requests.exceptions.ConnectionError:
            sent += 1
            failed += 1
            print(f"✗ CONNECTION ERROR (is main.py running?)")
        except Exception as e:
            sent += 1
            failed += 1
            print(f"✗ ERROR: {e}")
        
        # Rate limit
        if i < count - 1:  # Don't sleep after last request
            time.sleep(1.0 / rate)
    
    print(f"\n{'='*50}")
    print(f"Traffic Summary:")
    print(f"  Sent:       {sent}")
    print(f"  Successful: {successful}")
    print(f"  Failed:     {failed}")
    print(f"{'='*50}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Traffic generator for metrics lab')
    parser.add_argument('--mode', default='normal', 
                        choices=['normal', 'errors', 'latency', 'backlog', 'high-cardinality'],
                        help='Traffic mode')
    parser.add_argument('--count', type=int, default=10, help='Number of requests')
    parser.add_argument('--rate', type=float, default=1, help='Requests per second')
    
    args = parser.parse_args()
    
    generate_traffic(mode=args.mode, count=args.count, rate=args.rate)
