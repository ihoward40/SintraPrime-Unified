# SintraPrime Unified Monorepo

A comprehensive unified monorepo combining:
- **ike-bot** (27 branches) - Document intelligence, Google Drive integration, beneficiaries management
- **SintraPrime** (81 branches) - VLM, memory systems, GHL, telephony, voice integrations
- **ike-trust-agent** - Trust and authentication framework
- **Python Universe** (35,492 lines) - Core AI engine, agent types, utilities

## Architecture

```
SintraPrime-Unified/
├── core/
│   ├── universe/          # Python AI engine (35K+ lines)
│   ├── schemas/           # Unified database schemas
│   └── tests/             # Core test suite
├── apps/
│   ├── ike-bot/           # Document intelligence & outbox
│   ├── sintraprime/       # UI, Airlock server, features
│   └── ike-trust-agent/   # Trust and verification
├── shared/
│   ├── types/             # TypeScript type definitions
│   ├── schemas/           # JSON schemas
│   ├── config/            # Unified configuration
│   └── utils/             # Shared utilities
├── deployment/
│   ├── windows/           # PowerShell deployment scripts
│   ├── linux/             # Shell deployment scripts
│   └── integrations/      # Sync manager, backup
├── docs/                  # Complete documentation
├── tests/                 # Integration & E2E tests
├── .github/workflows/     # CI/CD pipelines
├── docker-compose.yml     # Single-command deployment
└── Makefile              # Build automation
```

## Quick Start

### Windows Deployment
```powershell
# One-command setup and deployment
& ".\deployment\windows\setup.ps1"
```

### Linux/Mac Deployment
```bash
# One-command setup and deployment
./deployment/linux/setup.sh
```

### Docker Deployment
```bash
docker-compose up -d
```

## Services

- **Hive Mind API** (FastAPI, port 8080) - Python AI engine
- **Airlock Server** (Express, port 3001) - TypeScript integration layer
- **PostgreSQL** (port 5432) - Primary database
- **Redis** (port 6379) - Caching & sessions
- **Elasticsearch** (port 9200) - Search & analytics
- **Grafana** (port 3000) - Monitoring
- **Prometheus** (port 9090) - Metrics
- **MinIO** (port 9000) - Object storage

## Features Integrated

### From SintraPrime
- VLM Vision Intelligence
- Persistent AI Memory Layer
- GHL (GoHighLevel) Integration
- Phone/Telephony Integration
- ElevenLabs Voice Synthesis
- Skills Learning System
- Swarm Coordination (2026-04-12 units)

### From IKE-Bot
- Document Intelligence Module
- Google Drive Integration
- Beneficiaries & Disputes Management
- NodeJS API Router
- SintraPrime Integration Layer
- Ed25519 Cryptographic Support

### From Python Universe
- Core AI agent types and framework
- Multi-agent orchestration
- NLP and vision processing
- Database ORM and migrations
- Authentication and authorization
- Logging and monitoring

## Deployment Automation

### Windows PowerShell (`deployment/windows/`)
- `setup.ps1` - Prerequisites check, Docker setup, initial DB migrations
- `deploy.ps1` - Build, start services, run tests, health checks
- `health-check.ps1` - Verify all services responding

### Linux/Mac Bash (`deployment/linux/`)
- `setup.sh` - Prerequisites, Docker, migrations
- `deploy.sh` - Build, start, verify

### Sync Manager (`deployment/integrations/`)
- Automatic daily sync with upstream branches
- Feature branch merger
- Conflict resolution
- Test runner integration

## Documentation

- `docs/FEATURES.md` - Complete feature inventory with source branches
- `docs/API.md` - Full API endpoint documentation
- `docs/DEPLOYMENT.md` - Step-by-step deployment guides
- `docs/ARCHITECTURE.md` - System design and data flow

## Testing

```bash
# Run all tests
make test

# Python tests
cd core && pytest -v

# TypeScript tests
cd apps/sintraprime && npm test
cd apps/ike-bot && npm test

# Integration tests
cd tests/integration && pytest -v
```

## Development

```bash
# Install dependencies
make install

# Start development environment
make dev

# Build for production
make build

# Deploy to production
make deploy
```

## Configuration

See `shared/config/unified.config.json` for:
- Service ports and worker counts
- Database connection settings
- Integration API keys
- Feature flags
- Logging levels

## Support

For issues with specific features, refer to the original repository:
- ike-bot: https://github.com/ihoward40/ike-bot
- SintraPrime: https://github.com/ihoward40/SintraPrime
- ike-trust-agent: https://github.com/ihoward40/ike-trust-agent

---

**Built:** 2026-04-22
**Version:** 1.0.0-unified
**Status:** Production Ready
