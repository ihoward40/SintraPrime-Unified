# Quick Start Guide

Get IKE-BOT up and running in 5 minutes.

## Prerequisites

- Node.js 18+ installed
- npm or yarn
- Supabase account (free tier works)

## Step 1: Install Dependencies

```bash
npm install
```

## Step 2: Configure Environment

Create `.env` file (copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
PORT=3000
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=your_key_here
```

## Step 3: Set Up Database

### Option A: Using Supabase Dashboard (Recommended)
1. Go to your Supabase project
2. Navigate to SQL Editor
3. Copy contents of `supabase/migrations/00001_init_schema.sql`
4. Run the SQL
5. Copy contents of `supabase/migrations/00002_seed_data.sql`
6. Run the SQL

### Option B: Using Supabase CLI
```bash
npm install -g supabase
npm run db:init
npm run db:seed
```

## Step 4: Start the Server

```bash
npm run dev
```

You should see:
```
Server listening on http://127.0.0.1:3000
```

## Step 5: Test the API

### Health Check
```bash
curl http://localhost:3000/
```

Expected response:
```json
{"ok":true,"message":"IKE-BOT running"}
```

### Create a Beneficiary
```bash
curl -X POST http://localhost:3000/api/beneficiaries \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "phone": "555-0100",
    "relationship": "Primary"
  }'
```

### List Beneficiaries
```bash
curl http://localhost:3000/api/beneficiaries
```

## Next Steps

- Read [README.md](./README.md) for complete API documentation
- Read [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) for technical details
- Check [supabase/README.md](./supabase/README.md) for database migration info

## Common Issues

### "Supabase credentials not found"
- Make sure `.env` file exists
- Verify `SUPABASE_URL` and `SUPABASE_ANON_KEY` are set
- Check Supabase project is active

### Database errors
- Ensure migrations have been run
- Check Supabase project has tables created
- Verify your Supabase API key has correct permissions

### Port already in use
- Change `PORT` in `.env` to a different port
- Or kill the process using port 3000:
  ```bash
  # On Mac/Linux
  lsof -ti:3000 | xargs kill -9
  
  # On Windows
  netstat -ano | findstr :3000
  taskkill /PID <PID> /F
  ```

## Development Tips

### View Logs
Logs are automatically formatted with colors in development:
```bash
npm run dev
```

### Build for Production
```bash
npm run build
npm start
```

### Database Management
```bash
npm run db:migrate  # Run migrations
npm run db:seed     # Seed test data
npm run db:reset    # Reset database (careful!)
```

## Useful Commands

```bash
# Development
npm run dev         # Start with hot reload

# Production
npm run build       # Compile TypeScript
npm start           # Run compiled code

# Database
npm run db:init     # Initialize schema
npm run db:seed     # Add test data
npm run db:migrate  # Run all migrations
npm run db:reset    # Reset database
```

## API Quick Reference

### Beneficiaries
- `GET /api/beneficiaries` - List all
- `GET /api/beneficiaries/:id` - Get one
- `POST /api/beneficiaries` - Create
- `PUT /api/beneficiaries/:id` - Update
- `DELETE /api/beneficiaries/:id` - Delete

### Credit Disputes
- `GET /api/credit-disputes` - List all
- `GET /api/credit-disputes/:id` - Get one
- `POST /api/credit-disputes` - Create
- `PUT /api/credit-disputes/:id` - Update
- `DELETE /api/credit-disputes/:id` - Delete

### Webhooks
- `POST /webhooks/stripe` - Stripe events
- `POST /webhooks/make` - Make.com automation
- `POST /webhooks/sendgrid` - SendGrid emails
- `POST /webhooks/postmark` - Postmark emails
- `POST /webhooks/billing-alert` - Billing alerts

## Need Help?

- Check [README.md](./README.md) for detailed documentation
- Check [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) for technical details
- Open an issue on GitHub

---

**You're ready to go! 🚀**
