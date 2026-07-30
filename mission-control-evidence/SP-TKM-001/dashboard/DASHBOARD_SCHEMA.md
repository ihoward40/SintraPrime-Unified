# SP-TKM-001 Analytics Dashboard Schema

Mission: SP-TKM-001
Owner: Observatory
Status: Draft schema

## 1. Video-Level Metrics

| Metric | Source | Frequency | Notes |
|---|---|---|---|
| Video ID | Internal | Per video | Matches script ID (e.g., UCC001). |
| Publish date/time | TikTok Studio / manual | Per video | |
| Content pillar | Internal | Per video | Myth correction, document literacy, etc. |
| Risk rating | Sentinel | Per video | LOW / MODERATE / HIGH |
| Claim classification | Athena | Per video | Highest V-level used |
| Views | TikTok Studio | Daily | |
| Unique viewers | TikTok Studio | Daily | |
| Average watch time | TikTok Studio | Daily | |
| Completion rate | TikTok Studio | Daily | |
| 2-second retention | TikTok Studio | Daily | |
| 6-second retention | TikTok Studio | Daily | |
| Likes | TikTok Studio | Daily | |
| Comments | TikTok Studio | Daily | |
| Shares | TikTok Studio | Daily | |
| Saves | TikTok Studio | Daily | |
| Profile visits | TikTok Studio | Daily | |
| Follows | TikTok Studio | Daily | |
| Link clicks | UTM / analytics | Daily | |
| Leads | Landing-page DB | Daily | Email captures attributed by UTM. |
| Sales | Checkout DB | Daily | Product purchases attributed by UTM. |
| Revenue | Checkout DB | Daily | |
| Refunds | Checkout DB | Daily | |

## 2. Business Metrics

| Metric | Formula | Frequency |
|---|---|---|
| Lead Conversion Rate | Leads / Link clicks | Weekly |
| Product Conversion Rate | Sales / Leads | Weekly |
| Workshop Conversion Rate | Workshop signups / Leads | Weekly |
| Revenue per Lead | Revenue / Leads | Weekly |
| Revenue per Buyer | Revenue / Sales | Weekly |
| Revenue per 1,000 Views | (Revenue / Views) × 1000 | Weekly |
| Affiliate Click-Through Rate | Affiliate clicks / Views | Weekly |
| Affiliate Conversion Rate | Affiliate sales / Affiliate clicks | Weekly |
| Sponsor Inquiry Rate | Sponsor inquiries / Views | Weekly |
| Customer Acquisition Cost | Ad or production spend / Sales | Weekly |
| Refund Rate | Refunds / Sales | Weekly |
| Email List Growth | New leads - unsubscribes | Weekly |
| Repeat Purchase Rate | Repeat buyers / Total buyers | Monthly |

## 3. Content Classification Rules

After a video has been published for at least seven days, classify it:

| Class | Criteria | Action |
|---|---|---|
| SCALE | Strong watch time, saves/shares, conversion, low risk | Increase production of similar content. |
| REMAKE | Strong topic, weak hook or delivery | Reshoot with new hook or tighter pacing. |
| REPURPOSE | Strong educational value, weak as short-form | Move to email, workshop, Series, or long-form. |
| PAUSE | Weak performance, confusing response, unclear CTA | Pause similar ideas; diagnose before retry. |
| RETIRE | Outdated, legally inaccurate, policy risky, brand damaging | Remove or archive; quarantine if compliance issue. |

## 4. Weekly Experiment Tracking

Each experiment changes exactly one major variable.

| Field | Type | Description |
|---|---|---|
| experiment_id | string | EXP-YYYY-MM-DD-NN |
| week_ending | date | ISO date |
| hypothesis | text | What we expect to change. |
| variable | text | Hook, CTA, caption, thumbnail, topic, format |
| control_video_id | string | Baseline video |
| test_video_id | string | Variant video |
| metric | text | Primary metric being tested |
| result | text | Outcome |
| decision | text | Scale / remake / pause / reject |

## 5. JSON Schema Example

```json
{
  "week_ending": "2026-08-03",
  "videos": [
    {
      "video_id": "UCC001",
      "pillar": "myth_correction",
      "risk_rating": "MODERATE",
      "claim_class": "V2",
      "views": 0,
      "leads": 0,
      "sales": 0,
      "revenue": 0,
      "classification": "PENDING"
    }
  ],
  "business_metrics": {
    "lead_conversion_rate": 0,
    "revenue_per_1000_views": 0,
    "refund_rate": 0
  },
  "experiments": [
    {
      "experiment_id": "EXP-2026-08-03-01",
      "hypothesis": "A direct question hook will outperform a statement hook for UCC content.",
      "variable": "hook",
      "control_video_id": "UCC001",
      "test_video_id": "UCC004",
      "metric": "6-second retention",
      "result": "PENDING",
      "decision": "PENDING"
    }
  ]
}
```

## 6. Data Sources

- TikTok Studio analytics (manual export until API access is approved)
- Landing-page form submissions
- Checkout records
- UTM parameter logs
- Affiliate platform reports
- Sponsor inquiry inbox

## 7. Reports

- Daily operating update: top 3 metrics, blockers, next actions.
- Weekly operating review: content published, views, top/bottom videos, leads, sales, revenue, experiments, compliance incidents, decisions.
- Final 30-day report: mission decision supported by evidence.
