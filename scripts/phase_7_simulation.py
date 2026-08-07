import asyncio
import logging
from portal.services.multi_tenant_governance import governance_service
from portal.services.policy_as_code import policy_engine, PolicyEffect
from portal.services.governed_identity import identity_service

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Phase7Simulation")

async def run_governance_simulation():
    logger.info("=== PHASE 7: GOVERNANCE & POLICY SIMULATION ===")
    
    # 1. Setup Tenant and Policies
    tenant_id = "tenant-bravo"
    governance_service.register_tenant(tenant_id, plan="GOLD")
    
    policy_yaml = """
id: restrict-sensitive-access
effect: DENY
actions: ["READ", "WRITE"]
resources: ["SENSITIVE_FOLDER_001"]
conditions:
  security_clearance: "LOW"
"""
    policy_engine.load_policy_from_yaml(policy_yaml, tenant_id=tenant_id)
    
    # 2. Test Policy Enforcement
    logger.info("Testing Policy Enforcement (DENY)...")
    context = {"security_clearance": "LOW"}
    authorized = await governance_service.authorize_intent(
        tenant_id, "READ", "SENSITIVE_FOLDER_001", context
    )
    
    if not authorized:
        logger.info("Status: POLICY DENY VERIFIED")
    else:
        logger.error("Status: POLICY DENY FAILURE")
        return False
        
    # 3. Test Identity Provisioning & Scoping
    logger.info("\nTesting Governed Identity...")
    identity = identity_service.provision_agent_identity(tenant_id, ["WORK_FOLDER_002"])
    
    has_access = identity_service.validate_access(identity.identity_id, "WORK_FOLDER_002")
    no_access = identity_service.validate_access(identity.identity_id, "SENSITIVE_FOLDER_001")
    
    if has_access and not no_access:
        logger.info("Status: FOLDER-SCOPED ACCESS VERIFIED")
    else:
        logger.error("Status: FOLDER-SCOPED ACCESS FAILURE")
        return False
        
    return True

async def main():
    success = await run_governance_simulation()
    if success:
        logger.info("\n=== PHASE 7 ARCHITECTURE VERIFIED ===")
    else:
        logger.error("\n=== PHASE 7 ARCHITECTURE VERIFICATION FAILED ===")

if __name__ == "__main__":
    asyncio.run(main())
