# IkeBot AI Integration Guide

## Overview

IkeBot now includes comprehensive OpenAI API integration for AI-powered trust automation features including beneficiary analysis, credit dispute letter generation, document asset creation, and more.

## Setup

### 1. Install Dependencies

```bash
cd ike-bot
npm install openai uuid
npm install --save-dev @types/uuid
```

### 2. Configure Environment Variables

Add to your `.env` file:

```env
# OpenAI API Configuration
OPENAI_API_KEY=sk-proj-...
OPENAI_API_BASE=https://api.openai.com/v1  # Optional, defaults to OpenAI

# Optional: Set usage limits
OPENAI_MAX_TOKENS=4000
OPENAI_MONTHLY_BUDGET=100.00
```

### 3. Register AI Routes

Update `src/index.ts` or your main server file:

```typescript
import aiRoutes from './routes/ai.routes';

// Register AI routes
app.use('/api/ai', aiRoutes);
```

### 4. Database Migration (Optional)

If you want to track AI operations in the database, run this migration:

```sql
CREATE TABLE ai_generations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  operation_id UUID NOT NULL UNIQUE,
  type VARCHAR(50) NOT NULL,
  model VARCHAR(100) NOT NULL,
  prompt TEXT NOT NULL,
  response JSONB NOT NULL,
  tokens_used INTEGER,
  cost_usd DECIMAL(10, 6),
  beneficiary_id UUID REFERENCES beneficiaries(id),
  dispute_id UUID REFERENCES credit_disputes(id),
  created_at TIMESTAMP DEFAULT NOW(),
  created_by VARCHAR(255),
  metadata JSONB
);

CREATE INDEX idx_ai_generations_type ON ai_generations(type);
CREATE INDEX idx_ai_generations_beneficiary ON ai_generations(beneficiary_id);
CREATE INDEX idx_ai_generations_created_at ON ai_generations(created_at);
CREATE INDEX idx_ai_generations_operation_id ON ai_generations(operation_id);
```

## API Endpoints

### Check AI Status

```http
GET /api/ai/status
```

**Response:**
```json
{
  "available": true,
  "message": "AI features are enabled"
}
```

### Analyze Beneficiary

```http
POST /api/ai/analyze-beneficiary
Content-Type: application/json

{
  "id": "uuid",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "phone": "555-0100",
  "relationship": "Primary",
  "created_at": "2024-01-01T00:00:00Z",
  "credit_disputes": [],
  "billing_events": []
}
```

**Response:**
```json
{
  "beneficiary_id": "uuid",
  "analysis": "Based on the beneficiary profile...",
  "tokens_used": 450,
  "cost_usd": 0.00135,
  "model": "gpt-5"
}
```

### Generate Dispute Letter

```http
POST /api/ai/generate-dispute-letter
Content-Type: application/json

{
  "dispute": {
    "id": "uuid",
    "beneficiary_id": "uuid",
    "creditor_name": "Example Credit Corp",
    "dispute_reason": "This account does not belong to me",
    "dispute_type": "not_mine",
    "status": "pending",
    "account_number": "123456",
    "amount": 1500.00
  },
  "beneficiary": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "phone": "555-0100",
    "address": "123 Main St, City, State 12345"
  }
}
```

**Response:**
```json
{
  "dispute_id": "uuid",
  "letter": "[Date]\n\n[Credit Bureau Name]\n...",
  "tokens_used": 850,
  "cost_usd": 0.00255,
  "model": "gpt-5"
}
```

### Generate Document Asset

```http
POST /api/ai/generate-asset
Content-Type: application/json

{
  "asset_type": "letterhead",
  "description": "Professional letterhead for trust automation services",
  "size": "1792x1024",
  "quality": "hd"
}
```

**Response:**
```json
{
  "asset_type": "letterhead",
  "image_url": "https://...",
  "image_data": "base64_encoded_image...",
  "revised_prompt": "A professional letterhead design...",
  "cost_usd": 0.08,
  "model": "dall-e-3"
}
```

### Analyze Portfolio

```http
POST /api/ai/analyze-portfolio
Content-Type: application/json

{
  "beneficiaries": [
    { "id": "uuid1", "first_name": "John", ... },
    { "id": "uuid2", "first_name": "Jane", ... }
  ]
}
```

### Analyze Dispute Success

```http
POST /api/ai/analyze-dispute
Content-Type: application/json

{
  "id": "uuid",
  "creditor_name": "Example Credit Corp",
  "dispute_reason": "Account not mine",
  "dispute_type": "not_mine"
}
```

### Generate Personalized Message

```http
POST /api/ai/generate-message
Content-Type: application/json

{
  "beneficiary": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com"
  },
  "message_type": "welcome",
  "context": "New account setup"
}
```

## Usage Examples

### Example 1: Analyze Beneficiary Before Meeting

```typescript
import axios from 'axios';

async function prepareBeneficiaryMeeting(beneficiaryId: string) {
  // Fetch beneficiary data
  const beneficiary = await fetchBeneficiary(beneficiaryId);
  
  // Get AI analysis
  const analysis = await axios.post('http://localhost:3000/api/ai/analyze-beneficiary', {
    ...beneficiary,
    credit_disputes: await fetchDisputes(beneficiaryId),
    billing_events: await fetchBillingEvents(beneficiaryId),
  });
  
  console.log('Beneficiary Analysis:', analysis.data.analysis);
  console.log('Cost:', `$${analysis.data.cost_usd.toFixed(4)}`);
}
```

### Example 2: Auto-Generate Dispute Letters

```typescript
async function generateDisputeLetterForCase(disputeId: string) {
  const dispute = await fetchDispute(disputeId);
  const beneficiary = await fetchBeneficiary(dispute.beneficiary_id);
  
  const response = await axios.post('http://localhost:3000/api/ai/generate-dispute-letter', {
    dispute,
    beneficiary,
  });
  
  // Save letter to file or database
  await saveDisputeLetter(disputeId, response.data.letter);
  
  return response.data.letter;
}
```

### Example 3: Weekly Portfolio Review

```typescript
async function weeklyPortfolioReview() {
  const allBeneficiaries = await fetchAllBeneficiaries();
  
  const response = await axios.post('http://localhost:3000/api/ai/analyze-portfolio', {
    beneficiaries: allBeneficiaries,
  });
  
  // Send analysis to management
  await sendEmail({
    to: 'management@example.com',
    subject: 'Weekly Portfolio Analysis',
    body: response.data.analysis,
  });
}
```

## Cost Management

### Estimated Costs

The AI integration uses OpenAI's latest models with the following approximate costs:

**Text Generation (GPT-5):**
- Input: $0.000003 per token
- Output: $0.000015 per token
- Average request: ~500 tokens = $0.0045

**Image Generation (DALL-E 3):**
- Standard quality: $0.04 per image
- HD quality: $0.08 per image

**Monthly Estimates:**
- 500 beneficiary analyses: ~$2.25
- 200 dispute letters: ~$1.80
- 50 portfolio reviews: ~$5.00
- 20 document assets: ~$1.60
- **Total: ~$10.65/month** (moderate usage)

### Monitoring Usage

Track AI costs by querying the `ai_generations` table:

```sql
-- Daily cost summary
SELECT 
  DATE(created_at) as date,
  type,
  COUNT(*) as operations,
  SUM(tokens_used) as total_tokens,
  SUM(cost_usd) as total_cost
FROM ai_generations
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at), type
ORDER BY date DESC;
```

### Setting Limits

Implement usage limits in your application:

```typescript
import { calculateCost } from './ai/client';

async function checkBudget(estimatedTokens: number, model: string): Promise<boolean> {
  const estimatedCost = calculateCost(estimatedTokens, model);
  const monthlySpend = await getMonthlyAISpend();
  const monthlyBudget = parseFloat(process.env.OPENAI_MONTHLY_BUDGET || '100');
  
  if (monthlySpend + estimatedCost > monthlyBudget) {
    throw new Error('Monthly AI budget exceeded');
  }
  
  return true;
}
```

## Error Handling

The AI integration includes comprehensive error handling:

**API Unavailable:**
```json
{
  "error": "AI features are not available"
}
```

**Rate Limit Exceeded:**
```json
{
  "error": "AI operation failed: Rate limit exceeded"
}
```

**Invalid Input:**
```json
{
  "error": "Validation error: ..."
}
```

## Best Practices

### Prompt Engineering

The integration includes carefully crafted prompts for each use case. When customizing prompts:

1. **Be specific** - Include all relevant context
2. **Set expectations** - Clearly state the desired output format
3. **Use examples** - Provide examples of good outputs
4. **Iterate** - Test and refine prompts based on results

### Performance Optimization

1. **Cache results** - Store AI-generated content to avoid regeneration
2. **Batch requests** - Group similar operations when possible
3. **Use appropriate models** - GPT-5 for complex tasks, GPT-4o for simpler ones
4. **Set token limits** - Prevent unexpectedly long responses

### Security Considerations

1. **Sanitize inputs** - Remove PII before sending to OpenAI
2. **Validate outputs** - Don't trust AI-generated content blindly
3. **Audit trail** - Log all AI operations for compliance
4. **Access control** - Restrict AI endpoints to authorized users

## Integration with Existing Features

### Webhook Integration

Trigger AI operations from webhooks:

```typescript
// In webhooks/make.ts
import { generateText } from '../ai/services/textGeneration';

export async function handleMakeWebhook(req: Request, res: Response) {
  const { action, data } = req.body;
  
  if (action === 'analyze_beneficiary') {
    const analysis = await generateText(
      getBeneficiaryAnalysisPrompt(data.beneficiary)
    );
    
    // Send analysis back to Make.com
    return res.json({ analysis: analysis.text });
  }
}
```

### Agent Tools Integration

The AI features complement the existing OpenAI agent tools in `/agent-tools/`:

```typescript
// agent-tools/analyze_beneficiary.json
{
  "type": "function",
  "function": {
    "name": "analyze_beneficiary",
    "description": "Analyze a beneficiary profile using AI",
    "parameters": {
      "type": "object",
      "properties": {
        "beneficiary_id": {
          "type": "string",
          "description": "UUID of the beneficiary to analyze"
        }
      },
      "required": ["beneficiary_id"]
    }
  }
}
```

## Testing

### Manual Testing

```bash
# Check AI status
curl http://localhost:3000/api/ai/status

# Test beneficiary analysis
curl -X POST http://localhost:3000/api/ai/analyze-beneficiary \
  -H "Content-Type: application/json" \
  -d @test-data/beneficiary.json
```

### Automated Testing

Create test files in `tests/ai/`:

```typescript
import { generateText } from '../src/ai/services/textGeneration';

describe('AI Text Generation', () => {
  it('should generate text successfully', async () => {
    const result = await generateText('Write a haiku about AI');
    expect(result.text).toBeTruthy();
    expect(result.tokensUsed).toBeGreaterThan(0);
  });
});
```

## Troubleshooting

### AI Features Not Available

**Problem:** `/api/ai/status` returns `available: false`

**Solution:** Check that `OPENAI_API_KEY` is set in `.env`

### High Costs

**Problem:** Monthly AI costs exceed budget

**Solution:** 
1. Review usage patterns in `ai_generations` table
2. Implement caching for repeated requests
3. Reduce token limits
4. Use lower-cost models for simple tasks

### Poor Output Quality

**Problem:** AI-generated content doesn't meet expectations

**Solution:**
1. Review and refine prompts
2. Adjust temperature settings
3. Add more context to prompts
4. Use examples in prompts

## Next Steps

1. **Deploy to production** - Set production API keys
2. **Monitor usage** - Set up alerts for budget thresholds
3. **Gather feedback** - Collect user feedback on AI features
4. **Iterate prompts** - Refine based on real-world usage
5. **Expand features** - Add more AI-powered capabilities

## Support

For issues or questions:
- Check logs in `agent_logs` table
- Review OpenAI API status: https://status.openai.com
- Consult OpenAI documentation: https://platform.openai.com/docs

## Conclusion

The IkeBot AI integration provides powerful automation capabilities while maintaining audit trails, cost controls, and security best practices. Start with the basic features and expand based on your specific needs.
