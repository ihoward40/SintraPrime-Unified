import argparse
from locust import HttpUser, task, between
import logging

logging.basicConfig(level=logging.INFO)

class PortalUser(HttpUser):
    """Load test user simulating portal interactions"""
    wait_time = between(1, 5)
    
    @task(3)
    def view_dashboard(self):
        self.client.get("/api/v1/dashboard")
    
    @task(2)
    def list_sessions(self):
        self.client.get("/api/v1/admin/sessions")
    
    @task(1)
    def check_health(self):
        self.client.get("/health")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--users", type=int, default=10)
    parser.add_argument("--spawn-rate", type=int, default=1)
    parser.add_argument("--duration", type=int, default=60)
    args = parser.parse_args()
    
    print(f"Starting load test: {args.users} users, {args.spawn_rate} spawn rate, {args.duration}s duration")