"""
Federal Agency Navigator Module for SintraPrime-Unified

Comprehensive guides and analysis tools for IRS, SEC, FTC, CFPB, and DOJ:
- IRS: Audit defense, OIC, installment agreements, penalty abatement
- SEC: Offering exemptions, registration, insider trading, enforcement
- FTC/CFPB: Debt collection violations, FCRA, complaint navigation
- DOJ: Grand jury defense, qui tam, FOIA, asset forfeiture
"""

from .irs_navigator import IRSNavigator
from .sec_navigator import SECNavigator
from .cfpb_ftc_navigator import CFPBNavigator, FTCNavigator
from .doj_navigator import DOJNavigator

__all__ = [
    "IRSNavigator",
    "SECNavigator",
    "CFPBNavigator",
    "FTCNavigator",
    "DOJNavigator",
]

__version__ = "1.0.0"
