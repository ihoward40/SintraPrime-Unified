# SintraPrime-Unified: One Repo, All Features

**Philosophy:** "One for all, and all for one" — A single integrated system combining Python agent framework, TypeScript interfaces, and all features from ihoward40 repos across all branches.

---

## 📐 Repository Structure

```
SintraPrime-Unified/
│
├── core/                          # Python Universe Agent Framework
│   ├── universe/                  # Core agent engine (35,492 lines)
│   │   ├── base_agent.py
│   │   ├── core_engine.py
│   │   ├── agent_communication.py
│   │   ├── swarm_patterns.py
│   │   ├── memory_system.py
│   │   ├── skill_system.py
│   │   ├── integrations/          # All integrations
│   │   │   ├── slack_integration.py
│   │   │   ├── discord_integration.py
│   │   │   ├── github_integration.py
│   │   │   ├── elevenlabs_integration.py    # From branch
│   │   │   ├── ghl_integration.py           # From branch
│   │   │   └── telephony_integration.py     # From branch
│   │   ├── hive_mind_api.py       # FastAPI endpoint
│   │   └── ...
│   ├── tests/                     # 247+ tests
│   ├── requirements.txt
│   └── Dockerfile
│
├── apps/                          # TypeScript Applications
│   ├── ike-bot/                   # IKE Bot (27 branches merged)
│   │   ├── src/
│   │   ├── document-intelligence/ # From branch
│   │   ├── google-drive-outbox/   # From branch
│   │   ├── legal-templates/       # From branch
│   │   ├── beneficiaries-crud/    # From branch
│   │   ├── router/                # SintraPrime router integration
│   │   └── package.json
│   │
│   ├── sintraprime/               # SintraPrime UI (70+ branches merged)
│   │   ├── ui/client/             # React frontend
│   │   │   ├── chat/              # Chat interface
│   │   │   ├── workflows/         # Workflow dialog
│   │   │   ├── skills/            # Skills discovery
│   │   │   └── onboarding/        # Onboarding tour
│   │   │
│   │   ├── airlock_server/        # Express server
│   │   │   ├── routes/
│   │   │   ├── autonomous/        # Autonomous tasks router
│   │   │   ├── migrations/        # DB migrations
│   │   │   └── ...
│   │   │
│   │   ├── features/
│   │   │   ├── elevenlabs/        # Voice integration
│   │   │   ├── ghl/               # GoHighLevel integration
│   │   │   ├── phone/             # Telephony integration
│   │   │   ├── vlm/               # Vision Language Model
│   │   │   ├── memory/            # Persistent AI memory
│   │   │   ├── agent-schemas/     # Agent framework
│   │   │   ├── autonomous-tasks/  # Task autonomy
│   │   │   ├── skills-hub/        # Open-source tools hub
│   │   │   └── swarm/             # Agent swarm coordination
│   │   │
│   │   └── package.json
│   │
│   └── ike-trust-agent/           # Trust & Verification Agent
│       ├── src/
│       └── package.json
│
├── shared/                        # Shared Resources
│   ├── types/                     # TypeScript types for both
│   ├── schemas/                   # Database schemas
│   │   └── universe_db_setup.sql  # 14-table schema
│   ├── config/                    # Shared configuration
│   └── utils/                     # Shared utilities
│
├── docker-compose.yml             # Unified orchestration
├── docker-compose-distributed.yml # Distributed mode
├── Dockerfile                     # Multi-service build
│
├── deployment/                    # Automation & Setup
│   ├── windows/
│   │   ├── setup.ps1              # PowerShell setup
│   │   ├── deploy.ps1             # Deployment script
│   │   └── health-check.ps1       # Verification
│   ├── linux/
│   │   ├── setup.sh
│   │   ├── deploy.sh
│   │   └── health-check.sh
│   └── integrations/
│       ├── merge-branches.py      # Branch merger
│       ├── sync-manager.py        # Keep in sync with upstream
│       └── feature-mapper.py      # Map branches → features
│
├── docs/                          # Unified Documentation
│   ├── ARCHITECTURE.md            # This file
│   ├── FEATURES.md                # Complete feature list
│   ├── API.md                     # API documentation
│   ├── DEPLOYMENT.md              # Deploy guide
│   ├── CONTRIBUTING.md            # How to contribute
│   └── TROUBLESHOOTING.md         # Common issues
│
├── tests/                         # Unified test suite
│   ├── integration/               # Python ↔ TypeScript tests
│   ├── e2e/                       # End-to-end scenarios
│   └── performance/               # Load testing
│
├── .github/
│   └── workflows/                 # CI/CD automation
│
└── README.md                      # Project overview

```

---

## 🔌 Services Architecture (docker-compose)

### Core Services

| Service | Port | Technology | Purpose |
|---------|------|-----------|---------|
| **hive-mind-api** | 8080 | FastAPI (Python) | Main agent API |
| **airlock-server** | 3001 | Express (TypeScript) | SintraPrime UI backend |
| **postgres** | 5432 | PostgreSQL | Unified database |
| **redis** | 6379 | Redis | Message bus & caching |
| **elasticsearch** | 9200 | Elasticsearch | Skill/agent search index |
| **grafana** | 3000 | Grafana | Monitoring dashboard |
| **prometheus** | 9090 | Prometheus | Metrics collection |
| **s3-storage** | 9000 | MinIO | Object storage (skills, docs) |

### Communication Layer

```
┌─────────────────────────────────────────────────┐
│  Python Agent Swarms (Hive Mind)                │
│  ├── Core agents                                │
│  ├── Skill agents                               │
│  └── Specialized agents (voice, memory, etc.)   │
└──────────────────┬──────────────────────────────┘
                   │
              HTTP/REST
           WebSocket gRPC
                   │
┌──────────────────▼──────────────────────────────┐
│  Unified Bus (Redis)                            │
│  ├── Agent ↔ Agent messaging                    │
│  ├── Agent ↔ Skill invocation                   │
│  └── Event broadcasting                         │
└──────────────────┬──────────────────────────────┘
                   │
              HTTP/REST
           gRPC/Protocol Buffers
                   │
┌──────────────────▼──────────────────────────────┐
│  TypeScript Services (Skills & UI)              │
│  ├── SintraPrime UI (React + Express)           │
│  ├── IKE Bot (agents & integrations)            │
│  ├── Trust Agent (verification)                 │
│  └── Specialized skills (voice, memory, etc.)  │
└─────────────────────────────────────────────────┘
```

---

## 🎯 Features Matrix

### From Python Universe
- ✅ Agent framework & lifecycle
- ✅ Swarm coordination
- ✅ Memory system (short/long-term)
- ✅ Skill system & marketplace
- ✅ Slack/Discord/GitHub integrations
- ✅ Event hub & real-time updates
- ✅ Analytics & monitoring
- ✅ Distributed execution

### From SintraPrime (70+ branches)
- ✅ ElevenLabs voice integration
- ✅ GoHighLevel (GHL) integration
- ✅ Phone/Telephony integration
- ✅ Vision Language Model (VLM) intelligence
- ✅ Persistent AI memory layer
- ✅ Agent schemas framework
- ✅ Autonomous task functions
- ✅ Autonomous router
- ✅ Skills discovery & learning
- ✅ Workflow dialog UI
- ✅ Chat responsive layout
- ✅ Onboarding tour
- ✅ Open-source tools hub
- ✅ High-ROI skills integration
- ✅ Swarm coordination (recent)
- ✅ Query guards (security)
- ✅ Database migrations (auto)

### From IKE Bot (27 branches)
- ✅ Document intelligence module
- ✅ Google Drive integration
- ✅ Legal document templates
- ✅ Beneficiaries & disputes management
- ✅ User profile system
- ✅ Binder outbox specification
- ✅ ED25519 cryptographic support
- ✅ NodeJS API router

### From IKE Trust Agent
- ✅ Trust verification system
- ✅ Cryptographic validation

---

## 🚀 Deployment Model

### One-Command Setup (Windows PowerShell)

```powershell
# Clone unified repo
git clone https://github.com/ihoward40/SintraPrime-Unified.git
cd SintraPrime-Unified

# Run setup
.\deployment\windows\setup.ps1

# Deploy
.\deployment\windows\deploy.ps1

# Verify
.\deployment\windows\health-check.ps1
```

### Automated Setup Process

1. **Environment Detection** (Windows/Linux/Mac)
2. **Docker Verification** (installed, running, sufficient resources)
3. **Repository Sync** (pull all ihoward40 branches, merge features)
4. **Database Migration** (PostgreSQL schema initialization)
5. **Service Startup** (docker-compose up)
6. **Health Check** (all endpoints responding)
7. **Feature Verification** (test all integrations)
8. **Dashboard Display** (open browser to UI)

---

## 🔄 Branch Integration Strategy

### Approach: Smart Merge

1. **Identify Feature Branches** across all three repos
2. **Extract Core Features** from each branch
3. **Resolve Conflicts** (shared dependencies, naming)
4. **Create Feature Toggles** (enable/disable via config)
5. **Consolidate to Single Tree** (no orphaned branches)
6. **Maintain Sync** (auto-pull latest from upstream)

### Key Features by Branch Type

**Copilot Branches** (ike-bot):
- Document intelligence → `/core/skills/document-intelligence/`
- Google Drive → `/core/integrations/google-drive/`
- Legal templates → `/apps/ike-bot/legal-templates/`

**Feature Branches** (SintraPrime):
- Voice integration → `/apps/sintraprime/features/elevenlabs/`
- VLM → `/apps/sintraprime/features/vlm/`
- Autonomous tasks → `/apps/sintraprime/features/autonomous-tasks/`

**Swarm Branches** (SintraPrime - Recent):
- Swarm coordination → `/core/swarm_patterns.py` (already there)
- Query guards → `/core/security/query_guards/`

---

## 🔐 Data Model

### Unified Database (PostgreSQL 14+)

**From Python Universe:**
- agents, agent_states, agent_skills
- memory, long_term_memory
- event_logs, audit_trail
- integrations, integration_configs

**From SintraPrime:**
- users, user_profiles
- tasks, autonomous_tasks, task_executions
- workflows, workflow_steps
- skills, skill_registry
- documents, document_versions

**From IKE Bot:**
- beneficiaries, disputes
- legal_documents, templates
- outbox_items, outbox_state

**Shared:**
- organizations, teams
- audit_logs, compliance_records
- api_keys, authentication

---

## 📊 Development Timeline

| Phase | Timeline | Deliverable |
|-------|----------|-------------|
| **Setup** | Now | Merged repo structure, all branches integrated |
| **Integration** | 1-2 hours | Python ↔ TypeScript communication working |
| **Testing** | 1-2 hours | 250+ tests passing, integration tests green |
| **Docker** | 30 min | docker-compose up, all services healthy |
| **Deployment** | 30 min | Windows PowerShell automation complete |
| **Documentation** | 30 min | Feature index, deployment guide, API docs |
| **Launch** | Ready | One-command deploy to any Windows machine |

---

## 🎯 Success Criteria (Phase 2)

- ✅ All repos cloned and branches extracted
- ✅ Python + TypeScript services communicate
- ✅ Unified docker-compose.yml works
- ✅ All 70+ SintraPrime features visible/usable
- ✅ All 27 ike-bot features visible/usable
- ✅ 250+ tests passing
- ✅ One-command Windows deployment working
- ✅ Health check shows all services running
- ✅ Dashboard displays all agents, skills, integrations
- ✅ API documentation complete

---

## 🔄 Sync Strategy

**Automated Sync Agent** (runs daily):
1. Pulls latest from `ihoward40/ike-bot:main`
2. Pulls latest from `ihoward40/SintraPrime:master`
3. Pulls latest from `ihoward40/ike-trust-agent:main`
4. Merges feature branches into unified tree
5. Runs test suite
6. Commits updates to `ihoward40/SintraPrime-Unified:main`
7. Notifies team of changes

---

**This is the blueprint. Let's build it.**
