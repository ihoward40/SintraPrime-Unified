# Demo Intake Scenario: Acme Corp Trust Setup

## Client Profile
- **Name:** Alex Taylor
- **Age:** 58
- **Net Worth:** $2.3M (real estate, stocks, cash)
- **Family:** Spouse (Jordan, 60), 2 adult kids (Morgan 28, Riley 26)
- **Goal:** Protect assets, minimize estate taxes, ensure smooth transition

## Intake Form Data (Copy/Paste into SintraPrime)
```json
{
  "client_name": "Alex Taylor",
  "client_email": "client@example.dev",
  "age": 58,
  "net_worth": 2300000,
  "state": "California",
  "trust_type": "Revocable Living Trust",
  "has_spouse": true,
  "spouse_name": "Jordan Taylor",
  "num_children": 2,
  "assets": {
    "real_estate": 1500000,
    "stocks": 500000,
    "cash": 300000
  },
  "concerns": "Estate taxes, probate avoidance, minor child protection"
}
```

## Expected AI Output (2-3 min generation time)

### Document 1: Trust Summary
```
ALEX TAYLOR REVOCABLE LIVING TRUST
Effective Date: [Today]
Trustee: Alex Taylor
Co-Trustee: Jordan Taylor
Successor Trustee: Morgan Taylor

PROPERTY SCHEDULE:
- Primary Residence: 123 Sample St, CA (est. $1.2M)
- Investment Portfolio: Sample brokerage account (est. $500K)
- Cash Reserves: Sample bank checking (est. $300K)
- [Additional assets listed]

BENEFICIARIES:
Primary: Alex Taylor (during life)
Remainder: Jordan Taylor (surviving spouse), then children equally

TAX OPTIMIZATION:
✅ Federal Estate Tax: Exempt (uses spousal lifetime exemption)
✅ California Inheritance Tax: None (no CA estate tax)
✅ Probate Avoidance: YES (all assets in trust)
```

### Document 2: Compliance Checklist
```
CALIFORNIA COMPLIANCE VERIFICATION
✅ Proper trust language (CA Probate Code §13100+)
✅ Witness requirements met (2 witnesses for real property)
✅ Notarization completed
✅ No minor beneficiary issues (all adults)
✅ Tax ID obtained for trust
✅ No creditor concerns noted

RISK ASSESSMENT: LOW
Status: APPROVED FOR EXECUTION
```

### Document 3: Client Action Items
```
1. Sign trust document (2 witnesses, 1 notary)
2. Retitle real estate into trust name
3. Transfer brokerage accounts into trust
4. Update beneficiaries on life insurance
5. Create pour-over will
6. Schedule annual review (next: Q2 2027)

Estimated timeline: 30 days to full execution
```

## Payment Screen
```
INTAKE COMPLETE - $297 DUE

Trust Setup: $297
Compliance Verification: Included
Document Generation: Included
Admin Access: 12 months ($47/mo thereafter)

Total Due: $297

[Pay with Stripe button]
↓
[Processing...]
↓
Payment ID: pi_1RtwX5CT25knq5v20V8j0h
Status: SUCCEEDED
Receipt: Receipt automatically sent to client@example.dev
```

## Follow-Up (In Admin Dashboard)
```
Receipt Entry:
- Date: 2026-05-05T10:45:12Z
- Client: Alex Taylor
- Action: trust_intake
- Intake ID: intake_7d92f4b9
- Documents: 3 (summary, compliance, actions)
- Payment: $297 (Stripe pi_1RtwX5CT25knq5v20V8j0h)
- Status: COMPLETED
- Duration: 2 min 43 sec
- Compliance: PASSED
```

## Talking Points for Demo
1. **Speed:** From intake form to 3 documents in 2:43 min
2. **Compliance:** Automatic verification against CA law
3. **Personalization:** Trust customized to Alex's specific situation
4. **Revenue:** $297 intake + $47/month × 12 months = $864 lifetime value per client
5. **Scalability:** Same workflow handles 100+ clients/month