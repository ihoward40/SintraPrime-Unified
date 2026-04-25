# Supabase Migrations

This directory contains SQL migration files for the IKE-BOT database schema.

## Structure

- `migrations/` - Contains numbered SQL migration files
  - `00001_init_schema.sql` - Initial database schema with all tables
  - `00002_seed_data.sql` - Seed data for development/testing

## Tables

### beneficiaries
Stores information about trust beneficiaries.

### credit_disputes
Tracks credit disputes filed on behalf of beneficiaries.

### billing_events
Records billing and payment events from Stripe and other sources.

### enforcement_packets
Manages enforcement packets (UCC liens, FOIA requests, etc.).

### agent_logs
Audit trail and logging for all API actions.

## Running Migrations

### Prerequisites
1. Install Supabase CLI: `npm install -g supabase`
2. Ensure you have Supabase project credentials in `.env`

### Manual Migration (SQL Files)
You can run migrations manually using the Supabase Dashboard or CLI:

```bash
# Using Supabase CLI
supabase db push

# Or apply specific migration
supabase db execute --file supabase/migrations/00001_init_schema.sql
```

### Using NPM Scripts
```bash
# Initialize schema
npm run db:init

# Run all migrations
npm run db:migrate

# Seed database
npm run db:seed

# Reset database (caution!)
npm run db:reset
```

## Best Practices

1. **Never modify existing migrations** - Create new migrations instead
2. **Use sequential numbering** - Start with 00001, 00002, etc.
3. **Include rollback capability** - Consider creating corresponding down migrations
4. **Test migrations** - Always test on a development database first
5. **Document changes** - Add comments explaining complex migrations

## Creating New Migrations

1. Create a new file: `supabase/migrations/XXXXX_description.sql`
2. Write your SQL changes
3. Test locally
4. Commit to repository
5. Run migration on staging/production
