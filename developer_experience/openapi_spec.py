"""
openapi_spec.py — Master OpenAPI 3.1 Specification for SintraPrime-Unified
Generates complete spec for all 10 modules and exports as JSON + YAML.
"""

import json
import yaml
from pathlib import Path

# ---------------------------------------------------------------------------
# Shared components / schemas
# ---------------------------------------------------------------------------

SHARED_SCHEMAS = {
    "Error": {
        "type": "object",
        "required": ["code", "message"],
        "properties": {
            "code": {"type": "integer", "example": 400},
            "message": {"type": "string", "example": "Bad request"},
            "details": {"type": "string"},
        },
    },
    "Pagination": {
        "type": "object",
        "properties": {
            "page": {"type": "integer", "example": 1},
            "per_page": {"type": "integer", "example": 20},
            "total": {"type": "integer", "example": 100},
            "total_pages": {"type": "integer", "example": 5},
        },
    },
    "HealthCheck": {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["ok", "degraded", "down"], "example": "ok"},
            "version": {"type": "string", "example": "2.0.0"},
            "uptime_seconds": {"type": "integer", "example": 86400},
        },
    },
}

SHARED_RESPONSES = {
    "400": {"description": "Bad Request", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
    "401": {"description": "Unauthorized", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
    "403": {"description": "Forbidden", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
    "404": {"description": "Not Found", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
    "429": {"description": "Rate Limit Exceeded", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
    "500": {"description": "Internal Server Error", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
}

# ---------------------------------------------------------------------------
# Module: Legal Intelligence API
# ---------------------------------------------------------------------------

LEGAL_PATHS = {
    "/legal/case-law/search": {
        "get": {
            "tags": ["Legal Intelligence"],
            "summary": "Search case law",
            "operationId": "searchCaseLaw",
            "parameters": [
                {"name": "query", "in": "query", "required": True, "schema": {"type": "string"}, "example": "landlord tenant security deposit California"},
                {"name": "jurisdiction", "in": "query", "schema": {"type": "string"}, "example": "CA"},
                {"name": "date_from", "in": "query", "schema": {"type": "string", "format": "date"}, "example": "2020-01-01"},
                {"name": "court_level", "in": "query", "schema": {"type": "string", "enum": ["supreme", "appellate", "district", "all"]}, "example": "appellate"},
                {"name": "page", "in": "query", "schema": {"type": "integer", "default": 1}},
                {"name": "per_page", "in": "query", "schema": {"type": "integer", "default": 20}},
            ],
            "responses": {
                "200": {
                    "description": "Case law results",
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/CaseLawSearchResult"}, "example": {"cases": [{"id": "CA-2023-1234", "title": "Smith v. Jones", "court": "CA Court of Appeal", "date": "2023-06-15", "summary": "Landlord must return deposit within 21 days.", "relevance_score": 0.97}], "pagination": {"page": 1, "per_page": 20, "total": 45}}}},
                },
                **SHARED_RESPONSES,
            },
        }
    },
    "/legal/case-law/{case_id}": {
        "get": {
            "tags": ["Legal Intelligence"],
            "summary": "Get full case text",
            "operationId": "getCaseLaw",
            "parameters": [{"name": "case_id", "in": "path", "required": True, "schema": {"type": "string"}}],
            "responses": {
                "200": {"description": "Full case details", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/CaseLaw"}}}},
                **SHARED_RESPONSES,
            },
        }
    },
    "/legal/contract/analyze": {
        "post": {
            "tags": ["Legal Intelligence"],
            "summary": "Analyze contract for red flags",
            "operationId": "analyzeContract",
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ContractAnalysisRequest"}, "example": {"text": "This agreement is entered into...", "contract_type": "lease", "party_role": "tenant"}}},
            },
            "responses": {
                "200": {"description": "Contract analysis", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ContractAnalysisResult"}}}},
                **SHARED_RESPONSES,
            },
        }
    },
    "/legal/deadline/monitor": {
        "post": {
            "tags": ["Legal Intelligence"],
            "summary": "Set up court deadline monitoring",
            "operationId": "monitorDeadline",
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/DeadlineMonitorRequest"}}},
            },
            "responses": {
                "201": {"description": "Deadline monitor created", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/DeadlineMonitor"}}}},
                **SHARED_RESPONSES,
            },
        }
    },
    "/legal/predict/outcome": {
        "post": {
            "tags": ["Legal Intelligence"],
            "summary": "Predict case outcome probability",
            "operationId": "predictCaseOutcome",
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/OutcomePredictionRequest"}}},
            },
            "responses": {
                "200": {"description": "Outcome prediction", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/OutcomePrediction"}}}},
                **SHARED_RESPONSES,
            },
        }
    },
    "/legal/complaint/file": {
        "post": {
            "tags": ["Legal Intelligence"],
            "summary": "File federal agency complaint",
            "operationId": "fileComplaint",
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ComplaintRequest"}}},
            },
            "responses": {
                "201": {"description": "Complaint filed", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ComplaintResult"}}}},
                **SHARED_RESPONSES,
            },
        }
    },
}

LEGAL_SCHEMAS = {
    "CaseLaw": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "title": {"type": "string"},
            "court": {"type": "string"},
            "date": {"type": "string", "format": "date"},
            "jurisdiction": {"type": "string"},
            "summary": {"type": "string"},
            "full_text": {"type": "string"},
            "citations": {"type": "array", "items": {"type": "string"}},
            "relevance_score": {"type": "number"},
        },
    },
    "CaseLawSearchResult": {
        "type": "object",
        "properties": {
            "cases": {"type": "array", "items": {"$ref": "#/components/schemas/CaseLaw"}},
            "pagination": {"$ref": "#/components/schemas/Pagination"},
        },
    },
    "ContractAnalysisRequest": {
        "type": "object",
        "required": ["text"],
        "properties": {
            "text": {"type": "string"},
            "contract_type": {"type": "string", "enum": ["lease", "employment", "nda", "service", "sale", "other"]},
            "party_role": {"type": "string"},
        },
    },
    "ContractAnalysisResult": {
        "type": "object",
        "properties": {
            "red_flags": {"type": "array", "items": {"type": "object", "properties": {"clause": {"type": "string"}, "severity": {"type": "string"}, "explanation": {"type": "string"}}}},
            "missing_clauses": {"type": "array", "items": {"type": "string"}},
            "risk_score": {"type": "number"},
            "recommendations": {"type": "array", "items": {"type": "string"}},
        },
    },
    "DeadlineMonitorRequest": {
        "type": "object",
        "required": ["case_number", "deadlines"],
        "properties": {
            "case_number": {"type": "string"},
            "court": {"type": "string"},
            "deadlines": {"type": "array", "items": {"type": "object", "properties": {"name": {"type": "string"}, "date": {"type": "string", "format": "date"}, "alert_days_before": {"type": "integer"}}}},
            "notification_email": {"type": "string", "format": "email"},
        },
    },
    "DeadlineMonitor": {
        "type": "object",
        "properties": {
            "monitor_id": {"type": "string"},
            "case_number": {"type": "string"},
            "status": {"type": "string"},
            "next_deadline": {"type": "string", "format": "date"},
        },
    },
    "OutcomePredictionRequest": {
        "type": "object",
        "required": ["case_type", "facts_summary"],
        "properties": {
            "case_type": {"type": "string"},
            "facts_summary": {"type": "string"},
            "jurisdiction": {"type": "string"},
            "similar_cases": {"type": "array", "items": {"type": "string"}},
        },
    },
    "OutcomePrediction": {
        "type": "object",
        "properties": {
            "win_probability": {"type": "number"},
            "confidence": {"type": "number"},
            "key_factors": {"type": "array", "items": {"type": "string"}},
            "recommended_strategy": {"type": "string"},
            "similar_cases_outcome": {"type": "array", "items": {"type": "object"}},
        },
    },
    "ComplaintRequest": {
        "type": "object",
        "required": ["agency", "description"],
        "properties": {
            "agency": {"type": "string", "enum": ["CFPB", "FTC", "EEOC", "HUD", "DOL", "FDA", "EPA"]},
            "description": {"type": "string"},
            "complainant_name": {"type": "string"},
            "respondent_name": {"type": "string"},
            "date_of_incident": {"type": "string", "format": "date"},
            "evidence_urls": {"type": "array", "items": {"type": "string", "format": "uri"}},
        },
    },
    "ComplaintResult": {
        "type": "object",
        "properties": {
            "complaint_id": {"type": "string"},
            "agency": {"type": "string"},
            "status": {"type": "string"},
            "confirmation_number": {"type": "string"},
            "estimated_response_days": {"type": "integer"},
        },
    },
}

# ---------------------------------------------------------------------------
# Module: Trust Law API
# ---------------------------------------------------------------------------

TRUST_PATHS = {
    "/trust/living-trust/create": {
        "post": {
            "tags": ["Trust Law"],
            "summary": "Create a living trust",
            "operationId": "createLivingTrust",
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/LivingTrustRequest"}, "example": {"grantor_name": "John Smith", "state": "CA", "assets": [{"description": "Primary residence", "value": 850000}], "beneficiaries": [{"name": "Jane Smith", "relationship": "spouse", "share_percent": 100}]}}},
            },
            "responses": {
                "201": {"description": "Trust created", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/TrustDocument"}}}},
                **SHARED_RESPONSES,
            },
        }
    },
    "/trust/{trust_id}/assets": {
        "get": {
            "tags": ["Trust Law"],
            "summary": "List trust assets",
            "operationId": "listTrustAssets",
            "parameters": [{"name": "trust_id", "in": "path", "required": True, "schema": {"type": "string"}}],
            "responses": {
                "200": {"description": "Trust assets", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/TrustAssets"}}}},
                **SHARED_RESPONSES,
            },
        },
        "post": {
            "tags": ["Trust Law"],
            "summary": "Add asset to trust",
            "operationId": "addTrustAsset",
            "parameters": [{"name": "trust_id", "in": "path", "required": True, "schema": {"type": "string"}}],
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/TrustAsset"}}},
            },
            "responses": {
                "201": {"description": "Asset added", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/TrustAsset"}}}},
                **SHARED_RESPONSES,
            },
        },
    },
    "/trust/business-formation/checklist": {
        "post": {
            "tags": ["Trust Law"],
            "summary": "Generate business formation checklist",
            "operationId": "businessFormationChecklist",
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/BusinessFormationRequest"}}},
            },
            "responses": {
                "200": {"description": "Formation checklist", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/BusinessFormationChecklist"}}}},
                **SHARED_RESPONSES,
            },
        }
    },
}

TRUST_SCHEMAS = {
    "LivingTrustRequest": {
        "type": "object",
        "required": ["grantor_name", "state"],
        "properties": {
            "grantor_name": {"type": "string"},
            "co_grantor_name": {"type": "string"},
            "state": {"type": "string"},
            "trust_name": {"type": "string"},
            "successor_trustee": {"type": "string"},
            "assets": {"type": "array", "items": {"$ref": "#/components/schemas/TrustAsset"}},
            "beneficiaries": {"type": "array", "items": {"$ref": "#/components/schemas/Beneficiary"}},
        },
    },
    "TrustDocument": {
        "type": "object",
        "properties": {
            "trust_id": {"type": "string"},
            "trust_name": {"type": "string"},
            "state": {"type": "string"},
            "created_at": {"type": "string", "format": "date-time"},
            "document_url": {"type": "string", "format": "uri"},
            "status": {"type": "string", "enum": ["draft", "executed", "funded"]},
        },
    },
    "TrustAsset": {
        "type": "object",
        "properties": {
            "asset_id": {"type": "string"},
            "description": {"type": "string"},
            "asset_type": {"type": "string", "enum": ["real_estate", "bank_account", "investment", "vehicle", "business", "other"]},
            "value": {"type": "number"},
            "transfer_status": {"type": "string", "enum": ["pending", "transferred", "deeded"]},
        },
    },
    "TrustAssets": {
        "type": "object",
        "properties": {
            "trust_id": {"type": "string"},
            "assets": {"type": "array", "items": {"$ref": "#/components/schemas/TrustAsset"}},
            "total_value": {"type": "number"},
        },
    },
    "Beneficiary": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "relationship": {"type": "string"},
            "share_percent": {"type": "number"},
            "condition": {"type": "string"},
        },
    },
    "BusinessFormationRequest": {
        "type": "object",
        "required": ["business_type", "state"],
        "properties": {
            "business_type": {"type": "string", "enum": ["LLC", "Corporation", "S-Corp", "Partnership", "Sole-Proprietorship"]},
            "state": {"type": "string"},
            "business_name": {"type": "string"},
            "owners": {"type": "array", "items": {"type": "object"}},
        },
    },
    "BusinessFormationChecklist": {
        "type": "object",
        "properties": {
            "business_type": {"type": "string"},
            "state": {"type": "string"},
            "steps": {"type": "array", "items": {"type": "object", "properties": {"step": {"type": "integer"}, "title": {"type": "string"}, "description": {"type": "string"}, "required_forms": {"type": "array", "items": {"type": "string"}}, "estimated_cost": {"type": "number"}}}},
            "total_estimated_cost": {"type": "number"},
            "estimated_time_days": {"type": "integer"},
        },
    },
}

# ---------------------------------------------------------------------------
# Module: Banking / Plaid API
# ---------------------------------------------------------------------------

BANKING_PATHS = {
    "/banking/credit-report/analyze": {
        "post": {
            "tags": ["Banking/Plaid"],
            "summary": "Analyze credit report",
            "operationId": "analyzeCreditReport",
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/CreditReportRequest"}}},
            },
            "responses": {
                "200": {"description": "Credit analysis", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/CreditAnalysis"}}}},
                **SHARED_RESPONSES,
            },
        }
    },
    "/banking/plaid/link": {
        "post": {
            "tags": ["Banking/Plaid"],
            "summary": "Create Plaid Link token",
            "operationId": "createPlaidLink",
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": {"type": "object", "properties": {"user_id": {"type": "string"}, "products": {"type": "array", "items": {"type": "string"}}}}}},
            },
            "responses": {
                "200": {"description": "Link token", "content": {"application/json": {"schema": {"type": "object", "properties": {"link_token": {"type": "string"}, "expiration": {"type": "string"}}}}}},
                **SHARED_RESPONSES,
            },
        }
    },
    "/banking/debt/negotiate": {
        "post": {
            "tags": ["Banking/Plaid"],
            "summary": "Generate debt settlement strategy",
            "operationId": "negotiateDebt",
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/DebtNegotiationRequest"}}},
            },
            "responses": {
                "200": {"description": "Settlement strategy", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/DebtNegotiationResult"}}}},
                **SHARED_RESPONSES,
            },
        }
    },
    "/banking/transactions": {
        "get": {
            "tags": ["Banking/Plaid"],
            "summary": "List bank transactions",
            "operationId": "listTransactions",
            "parameters": [
                {"name": "account_id", "in": "query", "required": True, "schema": {"type": "string"}},
                {"name": "start_date", "in": "query", "schema": {"type": "string", "format": "date"}},
                {"name": "end_date", "in": "query", "schema": {"type": "string", "format": "date"}},
            ],
            "responses": {
                "200": {"description": "Transactions list", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/TransactionList"}}}},
                **SHARED_RESPONSES,
            },
        }
    },
}

BANKING_SCHEMAS = {
    "CreditReportRequest": {
        "type": "object",
        "properties": {
            "report_data": {"type": "object"},
            "ssn_last4": {"type": "string"},
            "dispute_items": {"type": "array", "items": {"type": "string"}},
        },
    },
    "CreditAnalysis": {
        "type": "object",
        "properties": {
            "score": {"type": "integer"},
            "score_change": {"type": "integer"},
            "negative_items": {"type": "array", "items": {"type": "object"}},
            "dispute_recommendations": {"type": "array", "items": {"type": "string"}},
            "improvement_tips": {"type": "array", "items": {"type": "string"}},
        },
    },
    "DebtNegotiationRequest": {
        "type": "object",
        "required": ["debts"],
        "properties": {
            "debts": {"type": "array", "items": {"type": "object", "properties": {"creditor": {"type": "string"}, "balance": {"type": "number"}, "interest_rate": {"type": "number"}, "months_delinquent": {"type": "integer"}}}},
            "available_lump_sum": {"type": "number"},
            "monthly_budget": {"type": "number"},
        },
    },
    "DebtNegotiationResult": {
        "type": "object",
        "properties": {
            "strategy": {"type": "string", "enum": ["settlement", "payment_plan", "bankruptcy_consult", "avalanche", "snowball"]},
            "settlement_offers": {"type": "array", "items": {"type": "object"}},
            "sample_letters": {"type": "array", "items": {"type": "string"}},
            "estimated_savings": {"type": "number"},
        },
    },
    "TransactionList": {
        "type": "object",
        "properties": {
            "account_id": {"type": "string"},
            "transactions": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "date": {"type": "string"}, "amount": {"type": "number"}, "name": {"type": "string"}, "category": {"type": "array", "items": {"type": "string"}}}}},
            "total_count": {"type": "integer"},
        },
    },
}

# ---------------------------------------------------------------------------
# Module: Governance API
# ---------------------------------------------------------------------------

GOVERNANCE_PATHS = {
    "/governance/policies": {
        "get": {
            "tags": ["Governance"],
            "summary": "List governance policies",
            "operationId": "listPolicies",
            "parameters": [
                {"name": "status", "in": "query", "schema": {"type": "string", "enum": ["active", "draft", "archived"]}},
                {"name": "category", "in": "query", "schema": {"type": "string"}},
            ],
            "responses": {
                "200": {"description": "Policies list", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/PolicyList"}}}},
                **SHARED_RESPONSES,
            },
        },
        "post": {
            "tags": ["Governance"],
            "summary": "Create governance policy",
            "operationId": "createPolicy",
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/PolicyRequest"}}}},
            "responses": {
                "201": {"description": "Policy created", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Policy"}}}},
                **SHARED_RESPONSES,
            },
        },
    },
    "/governance/agents/register": {
        "post": {
            "tags": ["Governance"],
            "summary": "Register agent for governance",
            "operationId": "registerAgent",
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AgentRegistration"}}}},
            "responses": {
                "201": {"description": "Agent registered", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/RegisteredAgent"}}}},
                **SHARED_RESPONSES,
            },
        }
    },
    "/governance/audit-log": {
        "get": {
            "tags": ["Governance"],
            "summary": "Get audit log",
            "operationId": "getAuditLog",
            "parameters": [
                {"name": "agent_id", "in": "query", "schema": {"type": "string"}},
                {"name": "from_date", "in": "query", "schema": {"type": "string", "format": "date-time"}},
                {"name": "to_date", "in": "query", "schema": {"type": "string", "format": "date-time"}},
            ],
            "responses": {
                "200": {"description": "Audit log entries", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AuditLog"}}}},
                **SHARED_RESPONSES,
            },
        }
    },
}

GOVERNANCE_SCHEMAS = {
    "Policy": {
        "type": "object",
        "properties": {
            "policy_id": {"type": "string"},
            "name": {"type": "string"},
            "description": {"type": "string"},
            "rules": {"type": "array", "items": {"type": "object"}},
            "status": {"type": "string"},
            "created_at": {"type": "string", "format": "date-time"},
        },
    },
    "PolicyList": {
        "type": "object",
        "properties": {
            "policies": {"type": "array", "items": {"$ref": "#/components/schemas/Policy"}},
            "total": {"type": "integer"},
        },
    },
    "PolicyRequest": {
        "type": "object",
        "required": ["name", "rules"],
        "properties": {
            "name": {"type": "string"},
            "description": {"type": "string"},
            "rules": {"type": "array", "items": {"type": "object"}},
            "category": {"type": "string"},
        },
    },
    "AgentRegistration": {
        "type": "object",
        "required": ["agent_name", "capabilities"],
        "properties": {
            "agent_name": {"type": "string"},
            "agent_type": {"type": "string"},
            "capabilities": {"type": "array", "items": {"type": "string"}},
            "policy_ids": {"type": "array", "items": {"type": "string"}},
        },
    },
    "RegisteredAgent": {
        "type": "object",
        "properties": {
            "agent_id": {"type": "string"},
            "agent_name": {"type": "string"},
            "status": {"type": "string"},
            "registered_at": {"type": "string", "format": "date-time"},
        },
    },
    "AuditLog": {
        "type": "object",
        "properties": {
            "entries": {"type": "array", "items": {"type": "object", "properties": {"timestamp": {"type": "string"}, "agent_id": {"type": "string"}, "action": {"type": "string"}, "result": {"type": "string"}}}},
            "total": {"type": "integer"},
        },
    },
}

# ---------------------------------------------------------------------------
# Module: MCP Server API
# ---------------------------------------------------------------------------

MCP_PATHS = {
    "/mcp/tools": {
        "get": {
            "tags": ["MCP Server"],
            "summary": "List available MCP tools",
            "operationId": "listMcpTools",
            "responses": {
                "200": {"description": "Tools list", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/McpToolList"}}}},
                **SHARED_RESPONSES,
            },
        }
    },
    "/mcp/execute": {
        "post": {
            "tags": ["MCP Server"],
            "summary": "Execute MCP tool",
            "operationId": "executeMcpTool",
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/McpExecuteRequest"}}}},
            "responses": {
                "200": {"description": "Tool execution result", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/McpExecuteResult"}}}},
                **SHARED_RESPONSES,
            },
        }
    },
    "/mcp/agents/swarm": {
        "post": {
            "tags": ["MCP Server"],
            "summary": "Launch multi-agent swarm",
            "operationId": "launchSwarm",
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SwarmRequest"}}}},
            "responses": {
                "202": {"description": "Swarm launched", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SwarmStatus"}}}},
                **SHARED_RESPONSES,
            },
        }
    },
}

MCP_SCHEMAS = {
    "McpTool": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "description": {"type": "string"},
            "input_schema": {"type": "object"},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
    },
    "McpToolList": {
        "type": "object",
        "properties": {
            "tools": {"type": "array", "items": {"$ref": "#/components/schemas/McpTool"}},
            "total": {"type": "integer"},
        },
    },
    "McpExecuteRequest": {
        "type": "object",
        "required": ["tool_name", "arguments"],
        "properties": {
            "tool_name": {"type": "string"},
            "arguments": {"type": "object"},
            "timeout_seconds": {"type": "integer", "default": 30},
        },
    },
    "McpExecuteResult": {
        "type": "object",
        "properties": {
            "tool_name": {"type": "string"},
            "result": {"type": "object"},
            "execution_ms": {"type": "integer"},
            "status": {"type": "string", "enum": ["success", "error", "timeout"]},
        },
    },
    "SwarmRequest": {
        "type": "object",
        "required": ["task", "num_agents"],
        "properties": {
            "task": {"type": "string"},
            "num_agents": {"type": "integer", "minimum": 2, "maximum": 20},
            "agent_types": {"type": "array", "items": {"type": "string"}},
            "coordination_strategy": {"type": "string", "enum": ["hierarchical", "flat", "expert", "debate"]},
        },
    },
    "SwarmStatus": {
        "type": "object",
        "properties": {
            "swarm_id": {"type": "string"},
            "status": {"type": "string"},
            "agents": {"type": "array", "items": {"type": "object"}},
            "estimated_completion_seconds": {"type": "integer"},
        },
    },
}

# ---------------------------------------------------------------------------
# Module: Emotional Intelligence API
# ---------------------------------------------------------------------------

EI_PATHS = {
    "/ei/sentiment/analyze": {
        "post": {
            "tags": ["Emotional Intelligence"],
            "summary": "Analyze emotional sentiment",
            "operationId": "analyzeSentiment",
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SentimentRequest"}}}},
            "responses": {
                "200": {"description": "Sentiment analysis", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SentimentResult"}}}},
                **SHARED_RESPONSES,
            },
        }
    },
    "/ei/communication/adapt": {
        "post": {
            "tags": ["Emotional Intelligence"],
            "summary": "Adapt communication style",
            "operationId": "adaptCommunication",
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/CommunicationAdaptRequest"}}}},
            "responses": {
                "200": {"description": "Adapted communication", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/CommunicationAdaptResult"}}}},
                **SHARED_RESPONSES,
            },
        }
    },
}

EI_SCHEMAS = {
    "SentimentRequest": {
        "type": "object",
        "required": ["text"],
        "properties": {
            "text": {"type": "string"},
            "context": {"type": "string"},
            "user_profile": {"type": "object"},
        },
    },
    "SentimentResult": {
        "type": "object",
        "properties": {
            "primary_emotion": {"type": "string"},
            "emotions": {"type": "object", "additionalProperties": {"type": "number"}},
            "stress_level": {"type": "number"},
            "empathy_score": {"type": "number"},
            "recommended_tone": {"type": "string"},
        },
    },
    "CommunicationAdaptRequest": {
        "type": "object",
        "required": ["message", "target_sentiment"],
        "properties": {
            "message": {"type": "string"},
            "target_sentiment": {"type": "string"},
            "audience_type": {"type": "string"},
        },
    },
    "CommunicationAdaptResult": {
        "type": "object",
        "properties": {
            "adapted_message": {"type": "string"},
            "tone": {"type": "string"},
            "changes_made": {"type": "array", "items": {"type": "string"}},
        },
    },
}

# ---------------------------------------------------------------------------
# Module: App Builder API
# ---------------------------------------------------------------------------

APPBUILDER_PATHS = {
    "/appbuilder/apps": {
        "get": {
            "tags": ["App Builder"],
            "summary": "List built apps",
            "operationId": "listApps",
            "responses": {
                "200": {"description": "Apps list", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AppList"}}}},
                **SHARED_RESPONSES,
            },
        },
        "post": {
            "tags": ["App Builder"],
            "summary": "Build new app from spec",
            "operationId": "buildApp",
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AppBuildRequest"}}}},
            "responses": {
                "202": {"description": "Build started", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AppBuildJob"}}}},
                **SHARED_RESPONSES,
            },
        },
    },
    "/appbuilder/apps/{app_id}/deploy": {
        "post": {
            "tags": ["App Builder"],
            "summary": "Deploy app",
            "operationId": "deployApp",
            "parameters": [{"name": "app_id", "in": "path", "required": True, "schema": {"type": "string"}}],
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": {"environment": {"type": "string", "enum": ["staging", "production"]}}}}}},
            "responses": {
                "200": {"description": "Deploy result", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/DeployResult"}}}},
                **SHARED_RESPONSES,
            },
        }
    },
}

APPBUILDER_SCHEMAS = {
    "AppBuildRequest": {
        "type": "object",
        "required": ["name", "spec"],
        "properties": {
            "name": {"type": "string"},
            "spec": {"type": "object"},
            "template": {"type": "string"},
            "tech_stack": {"type": "string", "enum": ["react", "vue", "nextjs", "fastapi", "express"]},
        },
    },
    "AppBuildJob": {
        "type": "object",
        "properties": {
            "job_id": {"type": "string"},
            "app_id": {"type": "string"},
            "status": {"type": "string"},
            "estimated_seconds": {"type": "integer"},
        },
    },
    "AppList": {
        "type": "object",
        "properties": {
            "apps": {"type": "array", "items": {"type": "object", "properties": {"app_id": {"type": "string"}, "name": {"type": "string"}, "status": {"type": "string"}}}},
        },
    },
    "DeployResult": {
        "type": "object",
        "properties": {
            "app_id": {"type": "string"},
            "environment": {"type": "string"},
            "url": {"type": "string", "format": "uri"},
            "deployed_at": {"type": "string", "format": "date-time"},
        },
    },
}

# ---------------------------------------------------------------------------
# Module: Observability API
# ---------------------------------------------------------------------------

OBS_PATHS = {
    "/observability/metrics": {
        "get": {
            "tags": ["Observability"],
            "summary": "Get system metrics",
            "operationId": "getMetrics",
            "parameters": [
                {"name": "service", "in": "query", "schema": {"type": "string"}},
                {"name": "from", "in": "query", "schema": {"type": "string", "format": "date-time"}},
                {"name": "to", "in": "query", "schema": {"type": "string", "format": "date-time"}},
            ],
            "responses": {
                "200": {"description": "Metrics data", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/MetricsData"}}}},
                **SHARED_RESPONSES,
            },
        }
    },
    "/observability/traces": {
        "get": {
            "tags": ["Observability"],
            "summary": "Get distributed traces",
            "operationId": "getTraces",
            "parameters": [{"name": "trace_id", "in": "query", "schema": {"type": "string"}}],
            "responses": {
                "200": {"description": "Traces", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/TraceData"}}}},
                **SHARED_RESPONSES,
            },
        }
    },
    "/observability/health": {
        "get": {
            "tags": ["Observability"],
            "summary": "System health check",
            "operationId": "healthCheck",
            "responses": {
                "200": {"description": "Health status", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/HealthCheck"}}}},
                **SHARED_RESPONSES,
            },
        }
    },
}

OBS_SCHEMAS = {
    "MetricsData": {
        "type": "object",
        "properties": {
            "service": {"type": "string"},
            "metrics": {"type": "array", "items": {"type": "object", "properties": {"name": {"type": "string"}, "value": {"type": "number"}, "unit": {"type": "string"}, "timestamp": {"type": "string"}}}},
        },
    },
    "TraceData": {
        "type": "object",
        "properties": {
            "trace_id": {"type": "string"},
            "spans": {"type": "array", "items": {"type": "object", "properties": {"span_id": {"type": "string"}, "operation": {"type": "string"}, "duration_ms": {"type": "integer"}, "status": {"type": "string"}}}},
        },
    },
}

# ---------------------------------------------------------------------------
# Module: Compliance API
# ---------------------------------------------------------------------------

COMPLIANCE_PATHS = {
    "/compliance/check": {
        "post": {
            "tags": ["Compliance"],
            "summary": "Run compliance check",
            "operationId": "runComplianceCheck",
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ComplianceCheckRequest"}}}},
            "responses": {
                "200": {"description": "Compliance result", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ComplianceResult"}}}},
                **SHARED_RESPONSES,
            },
        }
    },
    "/compliance/reports": {
        "get": {
            "tags": ["Compliance"],
            "summary": "List compliance reports",
            "operationId": "listComplianceReports",
            "responses": {
                "200": {"description": "Reports list", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ComplianceReportList"}}}},
                **SHARED_RESPONSES,
            },
        }
    },
}

COMPLIANCE_SCHEMAS = {
    "ComplianceCheckRequest": {
        "type": "object",
        "required": ["framework", "data"],
        "properties": {
            "framework": {"type": "string", "enum": ["GDPR", "CCPA", "HIPAA", "SOC2", "PCI-DSS", "FTC-Act"]},
            "data": {"type": "object"},
            "scope": {"type": "array", "items": {"type": "string"}},
        },
    },
    "ComplianceResult": {
        "type": "object",
        "properties": {
            "framework": {"type": "string"},
            "status": {"type": "string", "enum": ["compliant", "non_compliant", "partial"]},
            "violations": {"type": "array", "items": {"type": "object", "properties": {"rule": {"type": "string"}, "severity": {"type": "string"}, "description": {"type": "string"}}}},
            "recommendations": {"type": "array", "items": {"type": "string"}},
            "score": {"type": "number"},
        },
    },
    "ComplianceReportList": {
        "type": "object",
        "properties": {
            "reports": {"type": "array", "items": {"type": "object", "properties": {"report_id": {"type": "string"}, "framework": {"type": "string"}, "created_at": {"type": "string"}, "status": {"type": "string"}}}},
        },
    },
}

# ---------------------------------------------------------------------------
# Module: Workflow Builder API
# ---------------------------------------------------------------------------

WORKFLOW_PATHS = {
    "/workflows": {
        "get": {
            "tags": ["Workflow Builder"],
            "summary": "List workflows",
            "operationId": "listWorkflows",
            "responses": {
                "200": {"description": "Workflows", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/WorkflowList"}}}},
                **SHARED_RESPONSES,
            },
        },
        "post": {
            "tags": ["Workflow Builder"],
            "summary": "Create workflow",
            "operationId": "createWorkflow",
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/WorkflowRequest"}}}},
            "responses": {
                "201": {"description": "Workflow created", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Workflow"}}}},
                **SHARED_RESPONSES,
            },
        },
    },
    "/workflows/{workflow_id}/execute": {
        "post": {
            "tags": ["Workflow Builder"],
            "summary": "Execute workflow",
            "operationId": "executeWorkflow",
            "parameters": [{"name": "workflow_id", "in": "path", "required": True, "schema": {"type": "string"}}],
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": {"inputs": {"type": "object"}}}}}},
            "responses": {
                "202": {"description": "Execution started", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/WorkflowExecution"}}}},
                **SHARED_RESPONSES,
            },
        }
    },
}

WORKFLOW_SCHEMAS = {
    "Workflow": {
        "type": "object",
        "properties": {
            "workflow_id": {"type": "string"},
            "name": {"type": "string"},
            "steps": {"type": "array", "items": {"type": "object"}},
            "trigger": {"type": "string"},
            "status": {"type": "string"},
        },
    },
    "WorkflowList": {
        "type": "object",
        "properties": {
            "workflows": {"type": "array", "items": {"$ref": "#/components/schemas/Workflow"}},
            "total": {"type": "integer"},
        },
    },
    "WorkflowRequest": {
        "type": "object",
        "required": ["name", "steps"],
        "properties": {
            "name": {"type": "string"},
            "steps": {"type": "array", "items": {"type": "object"}},
            "trigger": {"type": "string"},
        },
    },
    "WorkflowExecution": {
        "type": "object",
        "properties": {
            "execution_id": {"type": "string"},
            "workflow_id": {"type": "string"},
            "status": {"type": "string"},
            "started_at": {"type": "string", "format": "date-time"},
        },
    },
}

# ---------------------------------------------------------------------------
# Assemble the full OpenAPI specification
# ---------------------------------------------------------------------------

def build_openapi_spec() -> dict:
    """Build and return the complete OpenAPI 3.1 specification."""
    all_paths = {}
    all_paths.update(LEGAL_PATHS)
    all_paths.update(TRUST_PATHS)
    all_paths.update(BANKING_PATHS)
    all_paths.update(GOVERNANCE_PATHS)
    all_paths.update(MCP_PATHS)
    all_paths.update(EI_PATHS)
    all_paths.update(APPBUILDER_PATHS)
    all_paths.update(OBS_PATHS)
    all_paths.update(COMPLIANCE_PATHS)
    all_paths.update(WORKFLOW_PATHS)

    all_schemas = {}
    all_schemas.update(SHARED_SCHEMAS)
    all_schemas.update(LEGAL_SCHEMAS)
    all_schemas.update(TRUST_SCHEMAS)
    all_schemas.update(BANKING_SCHEMAS)
    all_schemas.update(GOVERNANCE_SCHEMAS)
    all_schemas.update(MCP_SCHEMAS)
    all_schemas.update(EI_SCHEMAS)
    all_schemas.update(APPBUILDER_SCHEMAS)
    all_schemas.update(OBS_SCHEMAS)
    all_schemas.update(COMPLIANCE_SCHEMAS)
    all_schemas.update(WORKFLOW_SCHEMAS)

    spec = {
        "openapi": "3.1.0",
        "info": {
            "title": "SintraPrime-Unified API",
            "version": "2.0.0",
            "description": "Comprehensive API for SintraPrime-Unified — AI-powered legal, financial, and governance automation platform.",
            "contact": {"name": "SintraPrime Support", "url": "https://ikesolutions.org", "email": "support@ikesolutions.org"},
            "license": {"name": "Proprietary"},
        },
        "servers": [
            {"url": "https://api.sintraprime.ikesolutions.org/v2", "description": "Production"},
            {"url": "https://api-staging.sintraprime.ikesolutions.org/v2", "description": "Staging"},
            {"url": "http://localhost:8000/v2", "description": "Local Development"},
        ],
        "tags": [
            {"name": "Legal Intelligence", "description": "Case law, contract analysis, court deadline monitoring"},
            {"name": "Trust Law", "description": "Living trusts, estate planning, business formation"},
            {"name": "Banking/Plaid", "description": "Credit analysis, debt negotiation, Plaid integration"},
            {"name": "Governance", "description": "Policy management, agent governance, audit logging"},
            {"name": "MCP Server", "description": "Model Context Protocol tool execution and agent swarms"},
            {"name": "Emotional Intelligence", "description": "Sentiment analysis and communication adaptation"},
            {"name": "App Builder", "description": "Dynamic app generation and deployment"},
            {"name": "Observability", "description": "Metrics, tracing, and health monitoring"},
            {"name": "Compliance", "description": "Regulatory compliance checking (GDPR, HIPAA, etc.)"},
            {"name": "Workflow Builder", "description": "Automated multi-step workflow creation and execution"},
        ],
        "paths": all_paths,
        "components": {
            "schemas": all_schemas,
            "securitySchemes": {
                "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
                "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"},
            },
        },
        "security": [{"BearerAuth": []}, {"ApiKeyAuth": []}],
    }
    return spec


def export_openapi(output_dir: str = ".") -> dict:
    """Export OpenAPI spec as both JSON and YAML files."""
    spec = build_openapi_spec()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    json_path = output_path / "openapi.json"
    with open(json_path, "w") as f:
        json.dump(spec, f, indent=2)
    print(f"✅ Exported: {json_path}")

    yaml_path = output_path / "openapi.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(spec, f, sort_keys=False, allow_unicode=True)
    print(f"✅ Exported: {yaml_path}")

    endpoints = sum(
        len(methods) for methods in spec["paths"].values()
        if isinstance(methods, dict)
    )
    schemas = len(spec["components"]["schemas"])
    print(f"📊 Total endpoints: {endpoints} | Schemas: {schemas}")
    return spec


if __name__ == "__main__":
    export_openapi(".")
