import asyncio
import uuid
import random
from typing import Dict, List, Any
from datetime import datetime, UTC

class AgentInstance:
    def __init__(self, agent_type: str, tenant_id: str):
        self.instance_id = str(uuid.uuid4())
        self.agent_type = agent_type
        self.tenant_id = tenant_id
        self.status = "IDLE"
        self.load = 0.0
        self.created_at = datetime.now(UTC)

class ParliamentScalingService:
    """
    Simulates the dynamic scaling of the Agent Parliament.
    Manages agent instance lifecycles based on intent volume and resource availability.
    """
    def __init__(self):
        self._instances: Dict[str, AgentInstance] = {}
        self._max_instances = 1000
        self._scaling_threshold = 0.8

    async def scale_up(self, agent_type: str, tenant_id: str, count: int = 1) -> List[str]:
        """Spawns new agent instances to handle increased load."""
        new_ids = []
        for _ in range(count):
            if len(self._instances) >= self._max_instances:
                break
            instance = AgentInstance(agent_type, tenant_id)
            self._instances[instance.instance_id] = instance
            new_ids.append(instance.instance_id)
        
        print(f"[PARLIAMENT_SCALING] Scaled up {len(new_ids)} instances for {agent_type}")
        return new_ids

    async def scale_down(self, instance_id: str):
        """Terminates an agent instance."""
        if instance_id in self._instances:
            del self._instances[instance_id]
            print(f"[PARLIAMENT_SCALING] Terminated instance {instance_id}")

    def get_parliament_status(self) -> Dict[str, Any]:
        """Returns the current state of the parliament."""
        types = {}
        for inst in self._instances.values():
            types[inst.agent_type] = types.get(inst.agent_type, 0) + 1
            
        return {
            "total_instances": len(self._instances),
            "agent_types": types,
            "system_load": sum(inst.load for inst in self._instances.values()) / max(1, len(self._instances))
        }

    async def run_simulation(self, intent_count: int):
        """Simulates parliament behavior under intent load."""
        print(f"--- PARLIAMENT SIMULATION: {intent_count} INTENTS ---")
        
        # 1. Scale up based on load
        await self.scale_up("NOVA", "test-tenant", count=min(50, intent_count // 2))
        await self.scale_up("HERMES", "test-tenant", count=5)
        
        # 2. Simulate processing
        for inst in self._instances.values():
            inst.status = "BUSY"
            inst.load = random.uniform(0.5, 0.95)
            
        status = self.get_parliament_status()
        print(f"Parliament Load: {status['system_load']:.2%}")
        
        # 3. Simulate completion
        for inst_id in list(self._instances.keys()):
            if random.random() > 0.7:
                await self.scale_down(inst_id)
                
        final_status = self.get_parliament_status()
        print(f"Simulation Complete. Remaining instances: {final_status['total_instances']}")
