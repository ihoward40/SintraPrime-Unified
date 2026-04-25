# SintraPrime-Unified SaaS Infrastructure

Complete multi-tenant SaaS deployment infrastructure for SintraPrime-Unified — the AI-powered legal tech platform.

## Overview

This package provides production-ready infrastructure for deploying SintraPrime-Unified as a subscription product for:
- Solo practitioners
- Small law firms
- Mid-sized practices
- Financial advisors
- Enterprise legal organizations

## Architecture

### Core Components

1. **Subscription Engine** (`subscription_engine.py`)
   - Stripe integration for payment processing
   - 4 plan tiers: Solo, Professional, Law Firm, Enterprise
   - Trial management (14-day free trials)
   - Metered billing for voice and document services
   - Coupon and discount system
   - Webhook handling for payment events

2. **Tenant Manager** (`tenant_manager.py`)
   - Schema-per-tenant database isolation
   - Complete tenant lifecycle management
   - White-label configuration
   - Data residency selection (US, EU, UK)
   - Onboarding progress tracking
   - Resource quota management

3. **Billing Portal** (`billing_portal.py`)
   - Stripe Customer Portal integration
   - Invoice management with PDF download
   - Payment method management
   - Billing dashboard with usage metrics
   - Automatic payment retry (3 attempts)
   - Dunning management for failed payments

4. **Onboarding Engine** (`onboarding.py`)
   - 6-step guided workflow:
     1. Firm profile setup
     2. Team member invites
     3. Brand configuration
     4. Integration setup
     5. Client data import
     6. Training walkthrough
   - Progress tracking and email automation
   - Sample data generation for demos
   - Completion rewards

5. **Usage Tracker** (`usage_tracker.py`)
   - Real-time usage tracking with Redis
   - Metrics: API calls, voice minutes, documents, storage, users
   - Quota enforcement with grace periods
   - Usage anomaly detection
   - Rate limiting per endpoint
   - Daily/monthly aggregation

6. **Marketplace** (`marketplace.py`)
   - 7 add-on modules available
   - Trial management per add-on
   - Revenue sharing for third-party vendors
   - Tenant-specific configuration
   - Add-on recommendations

7. **FastAPI Router** (`saas_api.py`)
   - 25+ RESTful endpoints
   - Tenant management
   - Subscription operations
   - Billing and invoice management
   - Onboarding workflows
   - Usage reporting
   - Marketplace operations

## Infrastructure (Terraform)

### AWS Services

**Networking:**
- VPC with public/private subnets across 2 AZs
- Internet Gateway + NAT Gateway
- Application Load Balancer with SSL termination
- Route 53 for custom domain routing

**Compute:**
- ECS Fargate cluster for containerized API
- Auto-scaling based on CPU/memory
- CloudWatch monitoring and alerts
- 99.95% uptime in production

**Database & Cache:**
- RDS PostgreSQL (multi-AZ, encrypted)
  - 100 GB initial storage, auto-scaling to 500 GB
  - 30-day backup retention
  - Automated failover
- ElastiCache Redis cluster
  - Multi-node with automatic failover
  - Encrypted at rest and in transit

**Storage:**
- S3 bucket for document storage
  - Versioning enabled
  - Encryption by default
  - CloudFront CDN for distribution

**Security:**
- Security groups for network isolation
- VPC endpoints for private connectivity
- Secrets Manager for credentials
- WAF (Web Application Firewall)
- Encryption for all data at rest and in transit

## Pricing Plans

### Solo — $49/month
- 1 user, 50 queries/day, 60 voice min/month
- Basic legal research, document templates
- Email support

### Professional — $149/month
- 5 users, 500 queries/day, 300 voice min/month
- Advanced research, voice memo transcription
- Client portal, priority support

### Law Firm — $499/month
- 25 users, unlimited queries/voice/documents
- White-label solution, custom branding
- 24/7 phone support, dedicated success manager

### Enterprise — Custom
- Unlimited users and features
- Dedicated infrastructure option
- Custom AI models, 99.95% SLA
- Dedicated engineering support

## Deployment

### Prerequisites
- AWS account with appropriate IAM permissions
- Terraform >= 1.0
- Docker for containerization
- Stripe API keys
- Redis connection

### Quick Start

1. **Clone and setup:**
```bash
cd saas/infrastructure/terraform
terraform init
terraform plan -var-file=vars/production.tfvars
```

2. **Deploy infrastructure:**
```bash
terraform apply -var-file=vars/production.tfvars
```

3. **Deploy application:**
```bash
# Build Docker image
docker build -t sintraprime-unified:latest .

# Push to ECR and update ECS service
aws ecs update-service --cluster sintraprime-unified-cluster \
  --service sintraprime-unified-service --force-new-deployment
```

### Environment Variables

```bash
DATABASE_URL=postgresql://user:pass@host/db
REDIS_URL=redis://host:6379
STRIPE_API_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

## Testing

Run the comprehensive test suite:

```bash
# Install dependencies
pip install pytest pytest-cov

# Run all tests
pytest saas/tests/test_saas.py -v

# Run with coverage
pytest saas/tests/test_saas.py --cov=saas --cov-report=html
```

**Test Coverage:**
- 35+ test functions
- Tenant lifecycle management
- Subscription state transitions
- Quota enforcement
- Usage tracking accuracy
- Onboarding workflows
- Marketplace operations
- Billing integrations
- Payment failure handling

## API Endpoints

### Tenant Management
- `POST /saas/tenants` — Create tenant
- `GET /saas/tenants/{tenant_id}` — Get tenant
- `PUT /saas/tenants/{tenant_id}/config` — Update config

### Subscriptions
- `POST /saas/subscriptions` — Create subscription
- `POST /saas/subscriptions/{id}/upgrade` — Upgrade plan
- `POST /saas/subscriptions/{id}/downgrade` — Downgrade plan
- `POST /saas/subscriptions/{id}/cancel` — Cancel subscription

### Billing
- `GET /saas/billing/{tenant_id}/dashboard` — Billing dashboard
- `GET /saas/billing/{tenant_id}/invoices` — Invoice history
- `GET /saas/billing/{tenant_id}/portal-url` — Portal URL
- `POST /saas/billing/webhook` — Stripe webhooks

### Usage
- `GET /saas/usage/{tenant_id}` — Usage report
- `POST /saas/usage/{tenant_id}/track` — Track usage

### Onboarding
- `POST /saas/onboarding/{tenant_id}/advance` — Advance step
- `GET /saas/onboarding/{tenant_id}/checklist` — Get checklist
- `POST /saas/onboarding/{tenant_id}/sample-data` — Generate samples

### Marketplace
- `GET /saas/marketplace` — List add-ons
- `POST /saas/marketplace/{addon_id}/enable` — Enable add-on
- `POST /saas/marketplace/{addon_id}/disable` — Disable add-on
- `GET /saas/marketplace/{addon_id}/config` — Get configuration
- `PUT /saas/marketplace/{addon_id}/config` — Update configuration

## Monitoring & Alerts

### CloudWatch Metrics
- API response times
- Error rates
- Database connections
- Redis memory usage
- S3 bucket size
- Failed payments

### Alerts
- High error rate (>5%)
- Slow queries (>1s)
- Database CPU >80%
- Low disk space
- Payment failures
- Failed tenant provisioning

## Security

### Data Protection
- AES-256 encryption at rest
- TLS 1.2+ for all communications
- Database encryption with AWS KMS
- Redis encryption in transit

### Compliance
- SOC 2 Type II audit-ready
- HIPAA-ready (with Enterprise)
- GDPR compliant with EU data center
- CCPA compliant
- PCI DSS compliant for payment processing

### Access Control
- IAM roles for AWS resources
- API keys for tenant access
- Role-based access (admin, attorney, paralegal, client)
- IP whitelisting available
- Single Sign-On (Enterprise)

## Scaling

### Auto-Scaling Policies
- **CPU:** Target 70% utilization
- **Memory:** Target 80% utilization
- **Min capacity:** 2 ECS tasks
- **Max capacity:** 10 ECS tasks

### Database Scaling
- RDS auto-scaling: 100 GB → 500 GB
- Read replicas for high-traffic deployments
- Connection pooling with PgBouncer

### Caching Strategy
- Redis for session data
- CloudFront for static assets
- Application-level caching for API responses

## Maintenance

### Backup & Recovery
- RDS: 30-day automated backups
- S3: Versioning enabled
- Cross-region replication available
- Point-in-time recovery capability

### Updates
- Zero-downtime deployments (blue-green)
- Automated database migrations
- Canary deployments for new versions

### Monitoring
- Real-time dashboard
- Email alerts
- Slack integration available
- PagerDuty for incident response

## Cost Estimation

### Monthly Costs (Production)
- RDS PostgreSQL: ~$300
- ElastiCache Redis: ~$150
- ECS Fargate: ~$200-$500 (depends on traffic)
- ALB: ~$20
- CloudFront: ~$50 (depends on traffic)
- S3: ~$20-$100 (depends on document storage)
- NAT Gateway: ~$30

**Total: ~$770-$1,050/month** (excluding customer-facing costs)

### Scaling Costs
- Each additional 100GB of RDS: +$30/month
- Each additional CloudFront 1TB/month: +$85
- High-traffic ECS: +$300-$500/month

## Roadmap

### Q2 2026
- Multi-region deployment
- Advanced analytics dashboard
- Custom report builder

### Q3 2026
- Mobile app (iOS/Android)
- Enhanced AI models
- Advanced ML predictions

### Q4 2026
- Desktop applications
- Advanced automation
- Custom integrations marketplace

## Support

### Documentation
- API docs: `/saas/docs`
- Architecture diagrams: `docs/architecture/`
- Integration guides: `docs/integrations/`

### Getting Help
- Email: support@sintraprime.com
- Phone: 1-800-SINTRAPRIME
- Slack: #support channel

### Enterprise Support
- Dedicated success manager
- 24/7 phone support
- SLA guarantee
- Custom training

## License

© 2026 SintraPrime, Inc. All rights reserved.

---

**Last Updated:** April 2026

For more information: https://www.sintraprime.com
