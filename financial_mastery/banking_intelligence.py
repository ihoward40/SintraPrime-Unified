"""
Banking Intelligence — Master the banking system from FDIC to private banking.
Covers banking rights, payment systems, wealth management banking, and ChexSystems disputes.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class BankingSystemGuide:
    """Comprehensive guide to the US banking system."""
    sections: Dict[str, List[str]]

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 70 + "╗",
            "║  US BANKING SYSTEM GUIDE" + " " * 45 + "║",
            "╚" + "═" * 70 + "╝",
        ]
        for section, points in self.sections.items():
            lines += ["", f"  ─── {section} ───"]
            for point in points:
                lines.append(f"  • {point}")
        return "\n".join(lines)


@dataclass
class BankingStrategy:
    """Optimized banking strategy for specific needs."""
    primary_checking: Dict[str, str]
    savings_recommendations: List[Dict[str, str]]
    business_banking: Optional[Dict[str, str]]
    total_monthly_fees_saved: float
    action_items: List[str]

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 70 + "╗",
            "║  BANKING OPTIMIZATION STRATEGY" + " " * 39 + "║",
            "╚" + "═" * 70 + "╝",
            "",
            f"  Monthly Fee Savings: ${self.total_monthly_fees_saved:.2f}",
            "",
            "  PRIMARY CHECKING:",
            f"    {self.primary_checking.get('name', '')}: {self.primary_checking.get('why', '')}",
            f"    URL: {self.primary_checking.get('url', '')}",
            "",
            "  HIGH-YIELD SAVINGS:",
        ]
        for sav in self.savings_recommendations:
            lines.append(f"    • {sav.get('name', '')}: {sav.get('apy', '')} APY — {sav.get('notes', '')}")
        if self.business_banking:
            lines += [
                "",
                "  BUSINESS BANKING:",
                f"    {self.business_banking.get('name', '')}: {self.business_banking.get('why', '')}",
            ]
        lines += ["", "  ACTION ITEMS:"]
        for item in self.action_items:
            lines.append(f"  → {item}")
        return "\n".join(lines)


@dataclass
class BankingRights:
    """Complete guide to consumer banking rights."""
    regulations: List[Dict[str, str]]
    dispute_process: List[str]
    chexsystems_guide: List[str]
    cfpb_complaint_steps: List[str]

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 70 + "╗",
            "║  CONSUMER BANKING RIGHTS" + " " * 45 + "║",
            "╚" + "═" * 70 + "╝",
            "",
            "  KEY REGULATIONS:",
        ]
        for reg in self.regulations:
            lines.append(f"  • {reg.get('name', '')}: {reg.get('rights', '')}")
        lines += ["", "  DISPUTE PROCESS (FCBA/Reg E):"]
        for step in self.dispute_process:
            lines.append(f"  {step}")
        lines += ["", "  CHEXSYSTEMS DISPUTE:"]
        for step in self.chexsystems_guide:
            lines.append(f"  {step}")
        lines += ["", "  FILE CFPB COMPLAINT:"]
        for step in self.cfpb_complaint_steps:
            lines.append(f"  {step}")
        return "\n".join(lines)


@dataclass
class PaymentSystemsGuide:
    """Guide to all major payment systems and rails."""
    systems: List[Dict[str, Any]]
    processor_comparison: List[Dict[str, str]]

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 70 + "╗",
            "║  PAYMENT SYSTEMS GUIDE" + " " * 47 + "║",
            "╚" + "═" * 70 + "╝",
            "",
            "  PAYMENT SYSTEMS:",
        ]
        for sys in self.systems:
            lines.append(f"  ┌─ {sys.get('name', '')}")
            lines.append(f"  │  Speed: {sys.get('speed', '')} | Cost: {sys.get('cost', '')}")
            lines.append(f"  │  Best for: {sys.get('best_for', '')}")
            lines.append(f"  └─ Max amount: {sys.get('max_amount', 'No limit')}")
        lines += ["", "  PAYMENT PROCESSOR COMPARISON:"]
        lines.append(f"  {'PROCESSOR':<20} {'RATE':<15} {'MONTHLY FEE':<15} NOTES")
        lines.append("  " + "─" * 65)
        for proc in self.processor_comparison:
            lines.append(
                f"  {proc.get('name', ''):<20} {proc.get('rate', ''):<15} "
                f"{proc.get('monthly_fee', ''):<15} {proc.get('notes', '')}"
            )
        return "\n".join(lines)


@dataclass
class WealthBankingStrategy:
    """Wealth management and private banking strategy."""
    net_worth_tier: str
    recommended_banks: List[Dict[str, str]]
    trust_recommendations: List[str]
    asset_protection_strategies: List[str]
    offshore_guidance: List[str]

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 70 + "╗",
            "║  WEALTH BANKING STRATEGY" + " " * 45 + "║",
            "╚" + "═" * 70 + "╝",
            "",
            f"  Net Worth Tier: {self.net_worth_tier}",
            "",
            "  RECOMMENDED BANKING RELATIONSHIPS:",
        ]
        for bank in self.recommended_banks:
            lines.append(f"  • {bank.get('name', '')}")
            lines.append(f"    Minimum: {bank.get('minimum', '')} | Services: {bank.get('services', '')}")
        lines += ["", "  TRUST & ESTATE STRUCTURES:"]
        for rec in self.trust_recommendations:
            lines.append(f"  → {rec}")
        lines += ["", "  ASSET PROTECTION:"]
        for strat in self.asset_protection_strategies:
            lines.append(f"  • {strat}")
        if self.offshore_guidance:
            lines += ["", "  OFFSHORE BANKING (LEGAL/COMPLIANT):"]
            for item in self.offshore_guidance:
                lines.append(f"  • {item}")
        return "\n".join(lines)


class BankingIntelligence:
    """
    Master the banking system — from retail checking to private banking.
    Covers banking rights, payment systems, fee avoidance, and wealth banking.

    Example:
        bi = BankingIntelligence()
        strategy = bi.bank_account_optimizer({"has_business": True, "monthly_balance": 5000})
        rights = bi.banking_rights_guide()
    """

    def banking_system_explainer(self) -> BankingSystemGuide:
        """Comprehensive guide to how the US banking system works."""
        sections = {
            "Federal Reserve System": [
                "The Fed is the central bank — controls monetary policy (interest rates, money supply)",
                "12 regional Federal Reserve Banks serve different districts",
                "Federal Funds Rate: overnight lending rate between banks — affects ALL interest rates",
                "Quantitative Easing (QE): Fed buys securities to inject money into economy",
                "The Fed controls reserve requirements (currently 0% since 2020)",
                "FOMC (Federal Open Market Committee): Sets interest rate policy 8x/year",
            ],
            "Fractional Reserve Banking": [
                "Banks hold only a fraction of deposits as reserves; lend the rest",
                "Money multiplier effect: $1,000 deposit can create $10,000+ in loans",
                "Banks create money through lending — this is how the money supply expands",
                "Bank runs: When depositors withdraw faster than reserves — why FDIC insurance exists",
                "Interbank lending: Banks borrow from each other in the Fed Funds market overnight",
            ],
            "FDIC Insurance": [
                "FDIC insures deposits up to $250,000 per depositor, per institution, per account category",
                "Account categories: Individual, Joint, Retirement (IRA), Trust, Business",
                "Maximize coverage: Individual ($250K) + Joint ($500K) + IRA ($250K) = $1M+ at one bank",
                "Credit union equivalent: NCUA insures up to $250,000",
                "NOT covered by FDIC: Stocks, bonds, mutual funds, annuities, crypto, safe deposit box contents",
                "If bank fails: FDIC typically makes depositors whole within 1–2 business days",
            ],
            "Payment Rails — How Money Moves": [
                "ACH (Automated Clearing House): Batch processing, 1–3 business days, $0.20–$1.50/transaction",
                "Same-Day ACH: Available since 2016, deadline 2:45 PM ET, up to $1M per transaction",
                "Fedwire: Real-time gross settlement, same-day, unlimited amount, $25–$35/wire",
                "SWIFT: International wire standard, 1–5 days, $25–$50 per wire + intermediary fees",
                "RTP (Real-Time Payments): Instant 24/7/365, up to $1M, faster than ACH",
                "FedNow: Federal Reserve's instant payment system (launched 2023) — 24/7 up to $500K",
                "Check 21: Electronic check processing — cleared in 1 business day",
            ],
        }
        return BankingSystemGuide(sections=sections)

    def bank_account_optimizer(self, needs: dict) -> BankingStrategy:
        """
        Recommend optimal banking setup based on individual needs.

        Args:
            needs: dict with monthly_balance, has_business, transaction_volume,
                   prefers_online, prefers_credit_union, state, cash_usage_frequency

        Returns:
            BankingStrategy with specific account recommendations
        """
        balance = needs.get("monthly_balance", 1000)
        has_business = needs.get("has_business", False)
        prefers_online = needs.get("prefers_online", True)
        cash_heavy = needs.get("cash_usage_frequency", "low") == "high"
        state = needs.get("state", "CA")

        # Primary checking recommendation
        if cash_heavy:
            primary = {
                "name": "Chase Total Checking or Bank of America Advantage",
                "why": "Large ATM network + free cash deposits at branch; waive fee with $1,500 balance",
                "url": "https://www.chase.com",
                "monthly_fee": "$12 (waivable)",
            }
        elif prefers_online:
            primary = {
                "name": "Ally Bank Interest Checking",
                "why": "No monthly fees, earns interest on checking, Allpoint ATM network (55K+ ATMs)",
                "url": "https://www.ally.com",
                "monthly_fee": "$0",
            }
        else:
            primary = {
                "name": "Local Credit Union Checking",
                "why": "Lower fees, better rates, member-owned, personal service, NCUA insured",
                "url": "https://www.ncua.gov/analysis/cuso-research-development/credit-union-locator",
                "monthly_fee": "$0–$5",
            }

        # High-yield savings
        savings = [
            {"name": "Marcus by Goldman Sachs", "apy": "4.50%+", "notes": "No fees, FDIC insured, easy transfer to any bank"},
            {"name": "SoFi Savings", "apy": "4.60%+", "notes": "Direct deposit required for top rate; checking included"},
            {"name": "Ally HYSA", "apy": "4.35%+", "notes": "No minimum, no fees, same-day transfers to Ally checking"},
            {"name": "Synchrony Bank", "apy": "4.75%+", "notes": "ATM card available; good for larger balances"},
            {"name": "Fidelity Cash Management", "apy": "4.96%+", "notes": "Brokerage + checking + FDIC via partner banks; unlimited ATM fee reimbursement"},
        ]

        # Business banking
        business_banking = None
        if has_business:
            business_banking = {
                "name": "Mercury (Tech/Startup) or Relay (Small Business)",
                "why": "Mercury: No fees, API access, sub-accounts, great for tech/SaaS. Relay: 20 checking accounts, no fees, virtual cards",
                "url": "https://mercury.com | https://relayfi.com",
                "monthly_fee": "$0",
                "notes": "For established businesses needing SBA loans: maintain relationship at Chase or BofA",
            }

        fee_savings = 25.0 if not prefers_online else 12.0

        action_items = [
            "Open a separate high-yield savings account and auto-transfer 10–20% of each paycheck",
            "Set up all direct deposits to trigger fee waivers at traditional banks",
            "Enroll in free credit union membership (often just need to live/work in area)",
            "Enable 2FA on all bank accounts — use authenticator app, not SMS",
            "Set up bank account alerts for every transaction over $25",
            "Never pay ATM fees — use in-network ATMs or get ATM fee reimbursement account",
        ]
        if has_business:
            action_items.append("Keep business and personal accounts COMPLETELY separate for tax/legal protection")
            action_items.append("Open a business account with Mercury or Relay (no fees, FDIC insured)")

        return BankingStrategy(
            primary_checking=primary,
            savings_recommendations=savings,
            business_banking=business_banking,
            total_monthly_fees_saved=fee_savings,
            action_items=action_items,
        )

    def banking_rights_guide(self) -> BankingRights:
        """Complete guide to consumer banking rights and protections."""
        regulations = [
            {
                "name": "Regulation E (Electronic Fund Transfers)",
                "rights": "Unauthorized debit card/ACH transactions: report within 2 days = max $50 liability; 2–60 days = max $500; 60+ days = unlimited",
            },
            {
                "name": "FCBA (Fair Credit Billing Act)",
                "rights": "Credit card billing errors: dispute within 60 days; creditor must resolve within 2 billing cycles; max $50 liability for unauthorized charges",
            },
            {
                "name": "Regulation CC (Funds Availability)",
                "rights": "Banks must make funds available: next day for cash/wires; 2 business days for local checks; 5 days for non-local",
            },
            {
                "name": "CFPB Consumer Rights",
                "rights": "Right to file complaints at ConsumerFinance.gov; CFPB can investigate and take action against banks",
            },
            {
                "name": "Truth in Savings Act (Regulation DD)",
                "rights": "Banks must disclose APY, fees, and terms BEFORE you open an account",
            },
        ]

        dispute_process = [
            "Step 1: Call bank immediately — document date, time, rep name, and confirmation number",
            "Step 2: Follow up in writing — dispute letter via certified mail (paper trail is crucial)",
            "Step 3: Bank must acknowledge within 10 business days (Reg E / FCBA)",
            "Step 4: Bank must resolve within 45 business days (Reg E) or 90 days (Reg E for POS)",
            "Step 5: If bank denies: Get written reason; escalate to CFPB or state banking regulator",
            "Step 6: File CFPB complaint at ConsumerFinance.gov — banks typically respond within 15 days",
            "Step 7: Small claims court for amounts under $5,000–$10,000 (varies by state)",
        ]

        chexsystems = [
            "ChexSystems: Consumer reporting agency for banking history — bank accounts, overdrafts, fraud",
            "Step 1: Get FREE ChexSystems report at ConsumerDebit.com (free annually)",
            "Step 2: Review for errors — wrong amounts, accounts you don't recognize, duplicate listings",
            "Step 3: Dispute errors directly to ChexSystems: ChexSystems, Inc., PO Box 583399, Minneapolis, MN 55458",
            "Step 4: Dispute to the reporting bank directly — they must investigate within 30 days",
            "Step 5: ChexSystems items typically fall off after 5 years",
            "Step 6: 'Second chance' checking: Chime, Varo, Juno, OneUnited, many credit unions",
            "Step 7: Pay off any legitimate overdrafts — some banks will remove reports after payment",
        ]

        cfpb_steps = [
            "1. Go to ConsumerFinance.gov/complaint",
            "2. Select product: Checking/Savings account, Credit card, Mortgage, etc.",
            "3. Describe the issue clearly with dates, amounts, and what resolution you want",
            "4. Company has 15 days to respond and 60 days to resolve",
            "5. CFPB forwards complaint to company and tracks response",
            "6. Success rate: Companies resolve ~97% of CFPB complaints",
            "7. Also file with your state banking regulator for dual pressure",
        ]

        return BankingRights(
            regulations=regulations,
            dispute_process=dispute_process,
            chexsystems_guide=chexsystems,
            cfpb_complaint_steps=cfpb_steps,
        )

    def payment_systems_guide(self) -> PaymentSystemsGuide:
        """Complete guide to all payment systems and processors."""
        systems = [
            {
                "name": "ACH (Standard)",
                "speed": "1–3 business days",
                "cost": "$0.20–$1.50 (bank); free for consumer",
                "best_for": "Payroll, bill pay, recurring payments, large transfers",
                "max_amount": "$25,000,000 (standard); lower for consumer accounts",
            },
            {
                "name": "Same-Day ACH",
                "speed": "Same business day (deadline 2:45 PM ET)",
                "cost": "$1–$5",
                "best_for": "Urgent payroll, same-day bill payment",
                "max_amount": "$1,000,000 per transaction",
            },
            {
                "name": "Domestic Wire Transfer (Fedwire)",
                "speed": "Same day (if initiated by 5 PM ET)",
                "cost": "$15–$35 sending; $0–$15 receiving",
                "best_for": "Real estate closings, large business payments, urgent transfers",
                "max_amount": "No limit",
            },
            {
                "name": "International Wire (SWIFT)",
                "speed": "1–5 business days",
                "cost": "$25–$50 + intermediary fees + currency conversion",
                "best_for": "International business payments, remittances",
                "max_amount": "Varies by bank; FBAR if >$10K cumulative",
            },
            {
                "name": "Zelle",
                "speed": "Minutes (real-time)",
                "cost": "Free for consumers",
                "best_for": "Person-to-person payments between US bank accounts",
                "max_amount": "$2,500–$5,000/day (varies by bank)",
            },
            {
                "name": "RTP / FedNow (Instant Payments)",
                "speed": "Seconds, 24/7/365",
                "cost": "$0.01–$0.045 per transaction",
                "best_for": "Business-to-business instant payments, payroll, invoice payment",
                "max_amount": "$1,000,000 (RTP); $500,000 (FedNow)",
            },
        ]

        processor_comparison = [
            {"name": "Stripe", "rate": "2.9% + $0.30", "monthly_fee": "$0", "notes": "Best for online/SaaS; excellent API; 135+ currencies"},
            {"name": "Square", "rate": "2.6% + $0.10", "monthly_fee": "$0", "notes": "Best for in-person/retail; free POS hardware; easy setup"},
            {"name": "PayPal Business", "rate": "3.49% + $0.49", "monthly_fee": "$0", "notes": "Good for freelancers; buyer protection; widely trusted"},
            {"name": "Helcim", "rate": "Interchange+0.15%", "monthly_fee": "$0", "notes": "Best interchange-plus pricing; good for high volume"},
            {"name": "Braintree", "rate": "2.59% + $0.49", "monthly_fee": "$0", "notes": "PayPal-owned; good for marketplaces and mobile"},
            {"name": "Clover", "rate": "2.3% + $0.10", "monthly_fee": "$14.95+", "notes": "Restaurant/retail POS; advanced inventory management"},
        ]

        return PaymentSystemsGuide(systems=systems, processor_comparison=processor_comparison)

    def wealth_management_banking(self, net_worth: float) -> WealthBankingStrategy:
        """
        Banking strategy for high-net-worth individuals.

        Args:
            net_worth: Total net worth in dollars

        Returns:
            WealthBankingStrategy with private banking and asset protection guidance
        """
        if net_worth >= 100_000_000:
            tier = "Ultra High Net Worth ($100M+)"
            banks = [
                {"name": "Citi Private Bank", "minimum": "$25M liquid assets", "services": "Full family office services, lending, real estate, philanthropy"},
                {"name": "JPMorgan Private Bank", "minimum": "$10M+", "services": "Investment management, banking, trust, tax, philanthropy"},
                {"name": "Goldman Sachs Private Wealth", "minimum": "$10M+", "services": "Institutional-quality investment management, bespoke strategies"},
                {"name": "Family Office (Establish or Multi-Family)", "minimum": "$50M+ for single family office", "services": "Consolidated wealth management, legal, tax, concierge"},
            ]
            trust_recs = [
                "Irrevocable Life Insurance Trust (ILIT) — keep life insurance out of taxable estate",
                "Grantor Retained Annuity Trust (GRAT) — transfer appreciation to heirs gift-tax free",
                "Charitable Remainder Trust (CRT) — income stream + charity + estate reduction",
                "Dynasty Trust — perpetual trust across generations (Nevada, South Dakota, Delaware best)",
                "Family Limited Partnership (FLP) — valuation discounts on transferred assets",
            ]
            offshore = [
                "Cayman Islands, Singapore, Liechtenstein bank accounts — LEGAL but must file FBAR + FATCA",
                "FBAR: FinCEN Form 114 — required if foreign accounts >$10K at any point in year",
                "FATCA: US persons must report foreign assets on Form 8938 if >$200K",
                "CRS (Common Reporting Standard): Most countries share data with IRS automatically",
                "Offshore is NOT tax avoidance — all income must be reported to IRS regardless of location",
                "Legitimate uses: Currency diversification, political risk hedging, estate planning structures",
            ]
        elif net_worth >= 10_000_000:
            tier = "High Net Worth ($10M–$100M)"
            banks = [
                {"name": "Merrill Lynch Private Banking", "minimum": "$1M–$10M", "services": "Investment management, trust, credit"},
                {"name": "US Bank Private Wealth Management", "minimum": "$3M", "services": "Portfolio management, trust, tax, insurance"},
                {"name": "Northern Trust", "minimum": "$5M", "services": "Investment, trust, banking, family office services"},
            ]
            trust_recs = [
                "Revocable Living Trust — avoid probate, maintain control, privacy",
                "ILIT — life insurance proceeds outside estate ($11.7M exemption per person 2024)",
                "Consider GRAT for appreciated assets",
                "529 Plans for education — superfund with 5-year election ($90K per child)",
            ]
            offshore = ["Report all foreign accounts via FBAR and FATCA", "Consult international tax attorney for any offshore structures"]
        elif net_worth >= 1_000_000:
            tier = "Millionaire ($1M–$10M)"
            banks = [
                {"name": "Chase Private Client", "minimum": "$250K+ in deposits/investments", "services": "Priority service, better rates, dedicated advisor, fee waivers"},
                {"name": "Fidelity Wealth Services", "minimum": "$250K invested", "services": "0.5%–1.5% AUM, dedicated advisor, comprehensive planning"},
                {"name": "Vanguard Personal Advisor Services", "minimum": "$50K", "services": "0.3% AUM, hybrid advisor model, low-cost index focus"},
            ]
            trust_recs = [
                "Revocable Living Trust — avoid probate, simple estate plan foundation",
                "Pour-over will with trust",
                "Healthcare directive and financial POA",
                "Annual gifting: $18,000/person/year gift-tax exclusion (2024)",
            ]
            offshore = []
        else:
            tier = "Mass Affluent (under $1M)"
            banks = [
                {"name": "High-Yield Online Bank (Marcus, Ally, SoFi)", "minimum": "$0", "services": "4.5%+ APY, no fees, FDIC insured"},
                {"name": "Local Credit Union", "minimum": "$5–$25 share", "services": "Better loan rates, lower fees, personal service"},
            ]
            trust_recs = ["Basic will and beneficiary designations on all accounts", "Healthcare POA and advance directive"]
            offshore = []

        asset_protection = [
            "Maximize contributions to protected retirement accounts (401k, IRA — protected from creditors in most states)",
            "Homestead exemption — primary residence protected in FL, TX, and others (unlimited in FL/TX)",
            "LLC for rental properties and business assets — keeps liability separate from personal assets",
            "Umbrella insurance policy: $1M–$5M umbrella for $200–$400/year — essential for any net worth",
            "Tenancy by Entirety (married couples) — property can't be seized for one spouse's debts in applicable states",
            "Life insurance cash value — protected from creditors in most states",
            "Avoid commingling business and personal funds — pierces corporate veil",
        ]

        return WealthBankingStrategy(
            net_worth_tier=tier,
            recommended_banks=banks,
            trust_recommendations=trust_recs,
            asset_protection_strategies=asset_protection,
            offshore_guidance=offshore,
        )
