"""
Service Registry - Service discovery and registration (Consul-compatible)

Provides:
- Service discovery
- Health checking
- Auto-deregistration
- Weighted routing
- Custom tags support
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Status of a service instance."""
    PASSING = "passing"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Health check for a service."""
    check_id: str
    check_type: str  # http, tcp, docker, script, ttl
    interval_ms: int = 10000
    timeout_ms: int = 5000
    status: ServiceStatus = ServiceStatus.UNKNOWN
    output: str = ""
    last_check_time: float = field(default_factory=time.time)
    consecutive_failures: int = 0
    failure_threshold: int = 3

    def is_healthy(self) -> bool:
        """Check if the check is healthy."""
        return self.status in (ServiceStatus.PASSING, ServiceStatus.WARNING)

    def is_critical(self) -> bool:
        """Check if the check is critical."""
        return self.consecutive_failures >= self.failure_threshold

    def record_pass(self) -> None:
        """Record a passing check."""
        self.status = ServiceStatus.PASSING
        self.consecutive_failures = 0
        self.last_check_time = time.time()

    def record_fail(self) -> None:
        """Record a failing check."""
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.failure_threshold:
            self.status = ServiceStatus.CRITICAL
        else:
            self.status = ServiceStatus.WARNING
        self.last_check_time = time.time()


@dataclass
class ServiceInstance:
    """A service instance registered in the service registry."""
    service_id: str
    service_name: str
    address: str
    port: int
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    weight: int = 10  # For weighted load balancing
    enable_tag_override: bool = False
    checks: Dict[str, HealthCheck] = field(default_factory=dict)
    registration_time: float = field(default_factory=time.time)
    deregistration_time: Optional[float] = None
    is_deregistered: bool = False

    def get_status(self) -> ServiceStatus:
        """Get the overall status of the service instance."""
        if not self.checks:
            return ServiceStatus.PASSING

        statuses = [check.status for check in self.checks.values()]

        if any(status == ServiceStatus.CRITICAL for status in statuses):
            return ServiceStatus.CRITICAL
        if any(status == ServiceStatus.WARNING for status in statuses):
            return ServiceStatus.WARNING

        return ServiceStatus.PASSING

    def is_healthy(self) -> bool:
        """Check if service instance is healthy."""
        return self.get_status() in (ServiceStatus.PASSING, ServiceStatus.WARNING)

    def add_health_check(self, check: HealthCheck) -> None:
        """Add a health check to this service."""
        self.checks[check.check_id] = check

    def remove_health_check(self, check_id: str) -> bool:
        """Remove a health check."""
        if check_id in self.checks:
            del self.checks[check_id]
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'service_id': self.service_id,
            'service_name': self.service_name,
            'address': self.address,
            'port': self.port,
            'tags': list(self.tags),
            'metadata': self.metadata,
            'weight': self.weight,
            'status': self.get_status().value,
            'is_healthy': self.is_healthy(),
            'check_count': len(self.checks),
            'registration_time': self.registration_time,
        }


class ServiceRegistry:
    """Service registry with Consul-compatible interface."""

    def __init__(self):
        self.services: Dict[str, ServiceInstance] = {}
        self.services_by_name: Dict[str, Set[str]] = defaultdict(set)
        self.services_by_tag: Dict[str, Set[str]] = defaultdict(set)
        self.deregistered_services: Dict[str, ServiceInstance] = {}
        self.health_check_tasks: Dict[str, asyncio.Task] = {}
        self.auto_deregister_delay_s = 3600  # 1 hour

    def register_service(
        self,
        service_name: str,
        address: str,
        port: int,
        service_id: Optional[str] = None,
        tags: Optional[Set[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        weight: int = 10
    ) -> ServiceInstance:
        """Register a new service instance."""
        service_id = service_id or str(uuid.uuid4())

        instance = ServiceInstance(
            service_id=service_id,
            service_name=service_name,
            address=address,
            port=port,
            tags=tags or set(),
            metadata=metadata or {},
            weight=weight
        )

        self.services[service_id] = instance
        self.services_by_name[service_name].add(service_id)

        for tag in instance.tags:
            self.services_by_tag[tag].add(service_id)

        logger.info(f"Registered service {service_name} with ID {service_id}")
        return instance

    def deregister_service(self, service_id: str) -> bool:
        """Deregister a service instance."""
        if service_id not in self.services:
            return False

        instance = self.services[service_id]
        instance.is_deregistered = True
        instance.deregistration_time = time.time()

        self.deregistered_services[service_id] = instance
        del self.services[service_id]

        self.services_by_name[instance.service_name].discard(service_id)
        for tag in instance.tags:
            self.services_by_tag[tag].discard(service_id)

        logger.info(f"Deregistered service {service_id}")
        return True

    def get_service(self, service_id: str) -> Optional[ServiceInstance]:
        """Get a service instance by ID."""
        return self.services.get(service_id)

    def get_services_by_name(self, service_name: str) -> List[ServiceInstance]:
        """Get all instances of a service by name."""
        service_ids = self.services_by_name.get(service_name, set())
        return [self.services[sid] for sid in service_ids if sid in self.services]

    def get_services_by_tag(self, tag: str) -> List[ServiceInstance]:
        """Get all services with a specific tag."""
        service_ids = self.services_by_tag.get(tag, set())
        return [self.services[sid] for sid in service_ids if sid in self.services]

    def get_healthy_services(self, service_name: str) -> List[ServiceInstance]:
        """Get healthy instances of a service."""
        instances = self.get_services_by_name(service_name)
        return [inst for inst in instances if inst.is_healthy()]

    def get_weighted_service_selection(
        self,
        service_name: str,
        tag_filter: Optional[str] = None
    ) -> Optional[ServiceInstance]:
        """Select a service instance using weighted random selection."""
        if tag_filter:
            instances = self.get_services_by_tag(tag_filter)
            instances = [i for i in instances if i.service_name == service_name and i.is_healthy()]
        else:
            instances = self.get_healthy_services(service_name)

        if not instances:
            return None

        # Calculate total weight
        total_weight = sum(inst.weight for inst in instances)
        if total_weight == 0:
            import random
            return random.choice(instances)

        # Weighted random selection
        import random
        choice_value = random.uniform(0, total_weight)
        current_sum = 0
        for instance in instances:
            current_sum += instance.weight
            if choice_value <= current_sum:
                return instance

        return instances[-1]

    def add_health_check(
        self,
        service_id: str,
        check_type: str,
        interval_ms: int = 10000,
        timeout_ms: int = 5000
    ) -> Optional[HealthCheck]:
        """Add a health check to a service."""
        if service_id not in self.services:
            return None

        check_id = f"{service_id}-{check_type}-{len(self.services[service_id].checks)}"
        check = HealthCheck(
            check_id=check_id,
            check_type=check_type,
            interval_ms=interval_ms,
            timeout_ms=timeout_ms
        )

        self.services[service_id].add_health_check(check)
        return check

    def update_check_status(
        self,
        service_id: str,
        check_id: str,
        is_passing: bool,
        output: str = ""
    ) -> bool:
        """Update the status of a health check."""
        if service_id not in self.services:
            return False

        service = self.services[service_id]
        if check_id not in service.checks:
            return False

        check = service.checks[check_id]
        check.output = output

        if is_passing:
            check.record_pass()
        else:
            check.record_fail()

        logger.debug(f"Updated check {check_id} status to {check.status.value}")
        return True

    def get_service_stats(self) -> Dict[str, Any]:
        """Get statistics about registered services."""
        total_instances = len(self.services)
        healthy_instances = sum(1 for s in self.services.values() if s.is_healthy())
        
        services_by_name = defaultdict(int)
        healthy_by_name = defaultdict(int)

        for instance in self.services.values():
            services_by_name[instance.service_name] += 1
            if instance.is_healthy():
                healthy_by_name[instance.service_name] += 1

        return {
            'total_services': len(services_by_name),
            'total_instances': total_instances,
            'healthy_instances': healthy_instances,
            'unhealthy_instances': total_instances - healthy_instances,
            'services': {
                name: {
                    'total_instances': services_by_name[name],
                    'healthy_instances': healthy_by_name[name],
                }
                for name in services_by_name
            },
            'deregistered_services': len(self.deregistered_services),
        }

    def cleanup_deregistered_services(self) -> int:
        """Remove old deregistered services to save memory."""
        current_time = time.time()
        cleaned_count = 0

        service_ids_to_remove = []
        for service_id, instance in self.deregistered_services.items():
            if instance.deregistration_time is None:
                continue
            elapsed = current_time - instance.deregistration_time
            if elapsed > self.auto_deregister_delay_s:
                service_ids_to_remove.append(service_id)

        for service_id in service_ids_to_remove:
            del self.deregistered_services[service_id]
            cleaned_count += 1

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} deregistered services")

        return cleaned_count

    async def monitor_service_health(
        self,
        service_id: str,
        check_fn: callable
    ) -> None:
        """Monitor the health of a service with custom check function."""
        if service_id not in self.services:
            return

        service = self.services[service_id]

        # Find or create a TTL check
        ttl_check = None
        for check in service.checks.values():
            if check.check_type == "ttl":
                ttl_check = check
                break

        if not ttl_check:
            ttl_check = HealthCheck(
                check_id=f"{service_id}-ttl",
                check_type="ttl"
            )
            service.add_health_check(ttl_check)

        while service_id in self.services:
            try:
                result = check_fn()
                if asyncio.iscoroutine(result):
                    result = await result

                if result:
                    self.update_check_status(service_id, ttl_check.check_id, True)
                else:
                    self.update_check_status(service_id, ttl_check.check_id, False)

                await asyncio.sleep(ttl_check.interval_ms / 1000.0)

            except Exception as e:
                logger.error(f"Error monitoring service {service_id}: {e}")
                self.update_check_status(service_id, ttl_check.check_id, False, str(e))

    def query_service(
        self,
        service_name: str,
        tag_filter: Optional[str] = None,
        passing_only: bool = True
    ) -> List[ServiceInstance]:
        """Query for service instances."""
        if tag_filter:
            instances = self.get_services_by_tag(tag_filter)
            instances = [i for i in instances if i.service_name == service_name]
        else:
            instances = self.get_services_by_name(service_name)

        if passing_only:
            instances = [i for i in instances if i.is_healthy()]

        return instances
