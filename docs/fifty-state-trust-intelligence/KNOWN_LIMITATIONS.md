# Known Limitations

- New Jersey, New York, and Pennsylvania have not received real licensed-attorney legal review.
- Delaware and Connecticut have not received real licensed-attorney legal review.
- New Jersey, New York, Pennsylvania, Delaware, and Connecticut remain `TESTED`, not `HUMAN_REVIEWED` and not `PRODUCTION_ELIGIBLE`.
- All other states, the District of Columbia, and federal overlays remain `NOT_STARTED`.
- N.J.A.C. 17:33 was constrained by official-source access. Official OAL/Treasury sources identify the official Administrative Code access path and adoption notice, but Phase 2A did not capture full current official text.
- Several creditor and exemption authorities remain source-limited records pending official compiled-source review.
- Wage execution, bank levy, support, government claim, tax claim, pension, property exemption, insurance, annuity, tenancy-by-entirety, homestead, IRA, and bankruptcy intersections are issue spotting only.
- Federal bankruptcy rules are labeled for federal bankruptcy review; no bankruptcy filing advice is encoded.
- New York and Pennsylvania tax overlays are issue spotting only and require professional tax/legal review.
- The UCC filing assessment is nonpersistent in Phase 2B and does not prove attachment, enforceability, ownership, perfection, priority, or collateral validity.
- The frontend production build dependency issue was repaired by pinning `@babel/runtime` to `7.24.8`; future dependency upgrades should revisit whether the pin remains necessary.
- Unsupported private-law claims are quarantined and cannot be approved without source reclassification and professional review.
