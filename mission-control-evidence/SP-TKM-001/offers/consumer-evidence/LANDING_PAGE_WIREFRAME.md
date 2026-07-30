# Consumer Evidence Intake Pack — Landing-Page Wireframe

Mission: SP-TKM-001
Owner: Revenue Architect
Platform: Existing SintraPrime web stack
Status: Internal wireframe only — no production deployment

## 1. Page Goal

Capture email leads and validate demand for the $9 Consumer Evidence Intake Pack.

## 2. URL

Primary:

```
https://sintraprime.com/consumer-evidence-intake-pack
```

Tracked version for TikTok bio:

```
https://sintraprime.com/consumer-evidence-intake-pack?utm_source=tiktok&utm_medium=organic&utm_campaign=consumer_evidence&utm_content=bio
```

## 3. Section Layout (Mobile-First)

### 3.1 Hero

- Headline: "Turn scattered records into organized evidence."
- Subheadline: "The Consumer Evidence Intake Pack helps you build a clear case file before you talk to a company, regulator, or qualified professional."
- CTA button: "Get the $9 Intake Pack" (secondary CTA: "Join the free waitlist")

### 3.2 Problem Statement

- Bullets:
  - Paperwork spread across emails, drawers, and apps
  - Deadlines approaching but records are disorganized
  - Hard to explain the issue clearly when it matters

### 3.3 Who It Is For

- Consumers facing a billing, collection, credit-report, or complaint issue
- People who want to organize records before seeking professional help
- Anyone who prefers to understand their own evidence first

### 3.4 What Is Included

- 10 guided PDF templates
- Editable worksheets (CSV/txt)
- Redaction guide
- Quick-start guide
- Resource directory

### 3.5 What It Does NOT Do

- Provide individualized legal, tax, or financial advice
- Guarantee any outcome, dispute result, or record removal
- Create an attorney-client relationship
- Draft letters or file court papers for you

### 3.6 Price

- **$9** (validation price)
- Note: "Limited-time validation price. No hidden fees. One-time purchase."

### 3.7 Educational Disclaimer

> This product provides general consumer education and document-organization tools. It is not individualized legal, tax, or financial advice. Outcomes depend on your facts, jurisdiction, and evidence.

### 3.8 Privacy-Minimized Interest Form

Fields:

- First name (required)
- Email address (required)
- Primary topic of interest (optional; dropdown: debt/credit/billing/complaint/other)
- How did you hear about us? (optional)

No full SSN, account numbers, payment card numbers, or document uploads accepted on this page.

### 3.9 UTM Attribution Support

- Landing page reads `utm_source`, `utm_medium`, `utm_campaign`, `utm_content` from query string.
- Values stored with lead record.
- Cookie/session fallback for returning visitors.

### 3.10 CTA Section

- Button: "Join the Waitlist — $9 Pack Coming Soon"
- No payment processor is connected in this increment.
- Click records lead and shows confirmation message.

### 3.11 Accessible Export / Fallback

- All form fields have associated labels.
- Color contrast meets WCAG 2.1 AA.
- Static markdown/PDF version of the page available for testing and fallback.
- Lead magnet delivered as direct file download after email verification.

### 3.12 Footer

- Educational disclaimer repeated
- Privacy policy link
- Contact route
- Copyright

## 4. Mobile-Responsive Notes

- Single-column layout below 768px
- Touch-friendly button size (minimum 44x44px)
- Readable font size (minimum 16px for inputs)
- Hero image or illustration optional; text must load fast

## 5. Not Connected in This Increment

- No payment processor
- No paid checkout
- No subscription or recurring billing
- No affiliate tracking pixels
- No TikTok pixel until privacy review is complete

## 6. Assets Needed

- Hero illustration or image
- Product mockup (PDF cover thumbnails)
- Privacy policy page
- Terms of use page
- Confirmation email copy
