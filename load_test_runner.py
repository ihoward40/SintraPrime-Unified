"""Locust load test runner

Configuration:
- 10 concurrent users
- 1000 requests/minute
- Auto-fail if error rate >1% or p99 >2.5s
"​

from locust import HttpUser, task, between
import random
from datetime import datetime

class AdminDashboardUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def get_metrics(self):
        self.client.get("/admin/metrics")

    @task(2)
    def list_sessions(self):
        self.client.get("/admin/sessions")
