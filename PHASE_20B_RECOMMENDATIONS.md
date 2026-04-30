# Phase 20B: Actionable Recommendations

**Generated:** 2026-04-29  
**Status:** Ready for Implementation  

---

## Quick Reference: External Code Status

| Module | Files | Status | Priority | Action Required |
|--------|-------|--------|----------|-----------------|
| ike-bot | 61 | Manually Copied | HIGH | Add LICENSE, Convert to subtree |
| trust_law | 23 | Mixed Internal/External | MEDIUM | Clarify sources, Document |
| ikeos_integration | 8 | Manually Copied | HIGH | Add LICENSE, Convert to subtree |
| trust_compliance_gateway | 8 | Native | LOW | None needed |
| ike-trust-agent | 2 | Minimal (metadata) | MEDIUM | Complete or remove |
| hermes_adapter | 1 | Manually Copied | HIGH | Verify license, Add attribution |
| **TOTAL** | **103** | - | - | - |

---

## Phase 20C: Licensing & Attribution (Next Phase)

### Task 1: Create ATTRIBUTION.md

**File:** `/agent/home/ATTRIBUTION.md`

```markdown
# Code Attribution & Licensing

## External Code Sources

### 1. IKE-Bot
- **Source:** https://github.com/ihoward40/ike-bot
- **Author:** Ian Howard (ihoward40)
- **Location:** apps/ike-bot/
- **Files:** 61
- **License:** [TO BE VERIFIED]
- **Integrated:** [Commit e0bebe03, ccb7987d, d4ab1231]
- **Components:** TypeScript API, Python backend, AI services

### 2. IkeOS Receipt Bridge
- **Source:** https://github.com/ihoward40/ikeos (inferred)
- **Author:** Ian Howard (ihoward40)
- **Location:** phase18/ikeos_integration/
- **Files:** 8
- **License:** [TO BE VERIFIED]
- **Integrated:** [Commit 7d4f332]
- **Components:** Receipt processing, validation bridge

### 3. Hermes Agent Integration
- **Source:** https://github.com/NousResearch/hermes-agent
- **Author:** Nous Research
- **Location:** local_llm/hermes_adapter.py
- **Files:** 1
- **License:** [LIKELY Apache 2.0 or MIT]
- **Integrated:** [Commit 476fb97, Sierra-2 phase]
- **Components:** LLM integration, offline processing

### 4. IKE-Trust-Agent (Partial)
- **Source:** https://github.com/ihoward40/ike-trust-agent
- **Author:** Ian Howard (ihoward40)
- **Location:** apps/ike-trust-agent/, trust_law/
- **Files:** 25 (2 in ike-trust-agent/, 23 in trust_law/)
- **License:** [TO BE VERIFIED]
- **Integrated:** [Commit 7743610 and earlier]
- **Components:** Trust reasoning, document generation, compliance

## SintraPrime Native Code
- **Location:** All other directories
- **Files:** 1,950
- **License:** SintraPrime Project License
- **Status:** Fully attributed to SintraPrime team

## Third-Party Dependencies
See requirements.txt and package.json for full dependency list.
```

**Checklist:**
- [ ] Verify ike-bot license from GitHub repository
- [ ] Verify ikeos license from GitHub repository
- [ ] Verify hermes-agent license from Nous Research
- [ ] Verify ike-trust-agent license from GitHub repository
- [ ] Add license compatibility assessment
- [ ] Create LICENSE symlinks in external code directories

---

### Task 2: Add LICENSE Files

**Action 1: Create `/agent/home/apps/ike-bot/LICENSE`**
```
Add full license text from: https://github.com/ihoward40/ike-bot/blob/main/LICENSE
Include: Copyright notice, license terms, SintraPrime integration note
```

**Action 2: Create `/agent/home/phase18/ikeos_integration/LICENSE`**
```
Add full license text from: https://github.com/ihoward40/ikeos/blob/main/LICENSE
Include: Copyright notice, license terms, SintraPrime integration note
```

**Action 3: Create `/agent/home/local_llm/LICENSE.hermes`**
```
Add full license text from: https://github.com/NousResearch/hermes-agent
Include: Copyright notice, license terms, SintraPrime integration note
```

**Action 4: Create `/agent/home/apps/ike-trust-agent/LICENSE`**
```
Add full license text from: https://github.com/ihoward40/ike-trust-agent/blob/main/LICENSE
Include: Copyright notice, license terms, SintraPrime integration note
```

**Action 5: Add inline attribution to key files**
```python
# apps/ike-bot/main/main.py
"""
IKE-Bot Integration Module
Originally from: https://github.com/ihoward40/ike-bot
Integrated into SintraPrime-Unified for [purpose]
License: [See LICENSE file]
"""
```

---

### Task 3: Update Documentation

**Update main `/README.md`:**
Add section:
```markdown
## External Code Integration

This repository includes code from the following external sources:

- **ike-bot** (apps/ike-bot/) - Ian Howard
- **ikeos_integration** (phase18/ikeos_integration/) - Ian Howard  
- **hermes-agent** (local_llm/hermes_adapter.py) - Nous Research
- **ike-trust-agent** (apps/ike-trust-agent/, trust_law/) - Ian Howard

See ATTRIBUTION.md and REPO_PROVENANCE.md for complete details.
All external code is properly licensed and attributed.
```

**Create `/EXTERNAL_DEPENDENCIES.md`:**
Document all external sources, versions, and integration notes.

---

## Phase 20D: Git Subtree Conversion (Recommended)

### Why Convert to Git Subtrees?

✅ **Benefits:**
- Clean separation of external code
- Easy to track upstream changes
- Maintainable update process (`git subtree pull`)
- Clear version history with `--squash`
- No git submodule complexity

### Conversion Steps

**Step 1: Backup current state**
```bash
git tag backup/phase20b-pre-subtree-conversion
```

**Step 2: Remove old code**
```bash
# After backup, if proceeding:
git rm -r apps/ike-bot
git commit -m "remove: IKE-Bot (preparing for subtree conversion)"
```

**Step 3: Add as subtree**
```bash
git subtree add --prefix=vendors/ike-bot \
  https://github.com/ihoward40/ike-bot.git main --squash
git commit -m "import: IKE-Bot as git subtree"
```

**Step 4: Update imports**
- Change relative imports from `apps/ike-bot` to `vendors/ike-bot`
- Update CI/CD paths
- Update documentation

### Conversion Plan

**Batch 1 (Week 1): IKE-Bot**
```bash
git subtree add --prefix=vendors/ike-bot \
  https://github.com/ihoward40/ike-bot.git main --squash
```

**Batch 2 (Week 2): IkeOS**
```bash
git subtree add --prefix=vendors/ikeos \
  https://github.com/ihoward40/ikeos.git main --squash
```

**Batch 3 (Week 3): Hermes Agent**
```bash
git subtree add --prefix=vendors/hermes-agent \
  https://github.com/NousResearch/hermes-agent.git main --squash
```

**Batch 4 (Week 4): IKE-Trust-Agent**
```bash
git subtree add --prefix=vendors/ike-trust-agent \
  https://github.com/ihoward40/ike-trust-agent.git main --squash
```

### Future Updates

After conversion, update external code with:
```bash
git subtree pull --prefix=vendors/ike-bot \
  https://github.com/ihoward40/ike-bot.git main --squash
```

---

## Phase 20E: Code Organization

### Directory Structure (Target)

```
SintraPrime-Unified/
├── vendors/                          # External code (git subtrees)
│   ├── ike-bot/                     # Git subtree from ihoward40/ike-bot
│   ├── ikeos/                       # Git subtree from ihoward40/ikeos
│   ├── hermes-agent/                # Git subtree from NousResearch
│   └── ike-trust-agent/             # Git subtree from ihoward40
├── src/                             # SintraPrime native code
│   ├── agents/
│   ├── legal_intelligence/
│   ├── trust_law/                   # (Modified: remove duplicates with vendor)
│   └── ...
├── docs/
│   ├── REPO_PROVENANCE.md           # Complete source documentation
│   ├── ATTRIBUTION.md               # All attributions
│   └── EXTERNAL_DEPENDENCIES.md     # External code versions
├── CODEOWNERS                        # Code ownership for external modules
├── .gitignore                        # Updated with build artifacts
└── README.md                         # Updated with external code section
```

### CODEOWNERS File

Create `/CODEOWNERS`:
```
# External Code
vendors/ike-bot/ @ihoward40
vendors/ikeos/ @ihoward40
vendors/hermes-agent/ @NousResearch
vendors/ike-trust-agent/ @ihoward40

# Core SintraPrime
src/ @ihoward40
docs/ @ihoward40

# Build & Config
.github/ @ihoward40
docker/ @ihoward40
```

---

## Phase 20F: CI/CD Integration

### GitHub Actions Workflow

Create `.github/workflows/provenance-audit.yml`:

```yaml
name: Code Provenance Audit

on:
  schedule:
    - cron: '0 0 1 * *'  # Monthly audit
  workflow_dispatch:

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0  # Full history
      
      - name: Audit Code Provenance
        run: |
          python3 scripts/audit_provenance.py
          echo "✅ Provenance audit complete"
      
      - name: Check Licenses
        run: |
          python3 scripts/check_licenses.py
          echo "✅ License check complete"
      
      - name: Detect Duplicates
        run: |
          python3 scripts/detect_duplicates.py
          echo "✅ Duplicate detection complete"
      
      - name: Generate Report
        if: always()
        run: |
          python3 scripts/generate_provenance_report.py
      
      - name: Upload Report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: provenance-report
          path: reports/provenance-*.md
```

### Audit Scripts

**`scripts/audit_provenance.py`:**
```python
#!/usr/bin/env python3
"""Automated code provenance audit"""

import subprocess
import json
from pathlib import Path

def audit():
    """Run complete provenance audit"""
    
    # 1. Get file tree
    result = subprocess.run(
        ['git', 'ls-tree', '-r', 'HEAD'],
        capture_output=True,
        text=True
    )
    
    # 2. Categorize by source
    sources = categorize_files(result.stdout)
    
    # 3. Verify licenses
    verify_licenses(sources)
    
    # 4. Check commits
    verify_commits(sources)
    
    print("✅ Audit complete")
    return sources

def categorize_files(git_output):
    """Categorize files by external source"""
    # Implementation: categorize based on path prefixes
    pass

def verify_licenses(sources):
    """Verify license files exist for external code"""
    pass

def verify_commits(sources):
    """Verify commit history for external code"""
    pass

if __name__ == '__main__':
    audit()
```

---

## Implementation Timeline

### Week 1-2: Immediate Actions
- [ ] Review audit report with team
- [ ] Verify licenses for all external code
- [ ] Create ATTRIBUTION.md
- [ ] Add LICENSE files to external directories

### Week 3-4: Documentation
- [ ] Update main README.md
- [ ] Create EXTERNAL_DEPENDENCIES.md
- [ ] Create CODEOWNERS file
- [ ] Update CONTRIBUTING.md

### Month 2: Git Subtree Conversion
- [ ] Convert ike-bot to subtree
- [ ] Convert ikeos to subtree
- [ ] Convert hermes-agent to subtree
- [ ] Convert ike-trust-agent to subtree

### Month 2-3: Code Organization
- [ ] Reorganize vendor directories
- [ ] Update all imports
- [ ] Update CI/CD paths
- [ ] Test all builds

### Month 3: CI/CD Integration
- [ ] Create provenance audit workflow
- [ ] Create license compliance check
- [ ] Create duplicate detection
- [ ] Schedule quarterly audits

---

## Success Criteria (Phase 20B+)

✅ **Phase 20B (Complete)**
- [x] All external code identified
- [x] Complete source documentation
- [x] Provenance audit report

⏳ **Phase 20C (Next)**
- [ ] All LICENSE files created
- [ ] ATTRIBUTION.md published
- [ ] All licenses verified
- [ ] Inline attribution added

⏳ **Phase 20D**
- [ ] Git subtrees created
- [ ] All imports updated
- [ ] Clean git history
- [ ] Backup tags created

⏳ **Phase 20E**
- [ ] Vendor directory structure
- [ ] Code organization complete
- [ ] CODEOWNERS file active
- [ ] Documentation updated

⏳ **Phase 20F**
- [ ] CI/CD workflows integrated
- [ ] Automated audits running
- [ ] License compliance checks
- [ ] Quarterly audit schedule

---

## Risk Mitigation

### Risk 1: License Incompatibility
**Mitigation:**
- Verify all licenses before proceeding
- Have legal review external code licenses
- Plan for possible code replacement if needed

### Risk 2: Breaking Changes During Subtree Conversion
**Mitigation:**
- Create backup tags before conversion
- Test thoroughly after each conversion
- Have rollback plan ready

### Risk 3: Import Path Changes
**Mitigation:**
- Use find/replace for systematic updates
- Test all imports before merge
- Update documentation proactively

### Risk 4: Lost Commit History
**Mitigation:**
- Use `--squash` for clean history
- Tag before major changes
- Keep old branches as reference

---

## Questions for Team Review

1. **IKeOS Source:** Is the repository actually at `ihoward40/ikeos`? Verify before proceeding.
2. **License Verification:** Can someone verify the actual licenses for all external code?
3. **Trust Law Split:** Which portions of trust_law come from ike-trust-agent vs. native development?
4. **Hermes License:** Is Apache 2.0/MIT acceptable for SintraPrime use?
5. **Git Subtrees vs. Submodules:** Team preference? Subtrees recommended for simpler workflow.
6. **Vendor Directory:** Approved location and naming convention?
7. **Timeline:** Can phases 20C-20F be completed within next 3 months?

---

## Related Documents

- `REPO_PROVENANCE.md` - Complete source documentation
- `PHASE_20B_REPORT.md` - Full audit report
- GitHub Issues: [Create issues for each action item]

---

**Next Steps:** Review with team and prioritize Phase 20C actions.

