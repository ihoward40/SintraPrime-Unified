# Contributing to SintraPrime-Unified

Thank you for your interest in contributing to the most comprehensive AI governance system ever built. Every contribution helps make SintraPrime more capable, more accurate, and more beneficial to users navigating complex legal and financial terrain.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Development Setup](#development-setup)
3. [How to Contribute](#how-to-contribute)
4. [Adding Trust Law Knowledge](#adding-trust-law-knowledge)
5. [Adding Legal Templates](#adding-legal-templates)
6. [Adding Financial Templates](#adding-financial-templates)
7. [Expanding Conscience Rules](#expanding-conscience-rules)
8. [Testing Standards](#testing-standards)
9. [Documentation Standards](#documentation-standards)
10. [Pull Request Process](#pull-request-process)

---

## Code of Conduct

All contributors must:
- Treat all users and contributors with respect
- Ensure all legal and financial content is accurate and appropriately disclaimed
- Not introduce content that gives harmful or misleading legal/financial advice
- Respect jurisdictional differences and avoid overgeneralizing legal concepts

---

## Development Setup

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/SintraPrime-Unified.git
cd SintraPrime-Unified

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR: .\venv\Scripts\Activate.ps1  # Windows

# 3. Install dev dependencies
pip install -e ".[dev]"

# 4. Install pre-commit hooks
pre-commit install

# 5. Verify setup
pytest artifacts/tests/ -v
```

---

## How to Contribute

### Bug Reports
Use the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.yml).

### Feature Requests
Use the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.yml).

### Pull Requests
1. Create a branch: `git checkout -b feature/my-feature`
2. Make your changes
3. Run tests: `pytest artifacts/tests/ -v --cov=artifacts`
4. Submit PR using the [PR Template](.github/PULL_REQUEST_TEMPLATE.md)

---

## Adding Trust Law Knowledge

Trust law templates and analysis rules live in:
- `artifacts/legal_document_library.py` — Document templates
- `trust_law/` — Reasoning engine (planned module)

### Template Requirements

When adding a new trust document:
1. Include all required jurisdictional elements
2. Use `[BRACKET]` notation for ALL fillable fields
3. Add signature blocks and notarization blocks
4. Include a reference to the governing statute (e.g., "Uniform Trust Code § 402")
5. Add a disclaimer if provisions vary by state

```python
# Example: Adding a new trust type
def _spendthrift_trust(self) -> str:
    return """\
                    SPENDTHRIFT TRUST AGREEMENT
    
    [FULL TEMPLATE CONTENT — minimum 500 words]
    [All fillable fields in [BRACKET] notation]
    [Governing law reference]
    [Notarization block]
    """
```

5. Register the template in `_build_index()`:
```python
self._templates["spendthrift_trust"] = self._spendthrift_trust()
```

6. Add at least 3 tests in `artifacts/tests/test_artifacts.py`

---

## Adding Legal Templates

### Requirements for All Legal Templates

- [ ] Minimum 200 words (most should be 500+)
- [ ] All fillable fields in `[BRACKET]` notation
- [ ] Proper signature blocks
- [ ] Appropriate notarization language where required
- [ ] Governing law clause
- [ ] Disclaimer: "This template is for informational purposes only"
- [ ] State-specific notes where relevant

### Naming Convention

```python
# File: artifacts/legal_document_library.py
# Method names:
_template_name_snake_case()

# Template keys in _build_index():
"template_name_snake_case"
```

---

## Adding Financial Templates

Financial templates live in `artifacts/financial_report_templates.py`.

### Requirements

- [ ] Unicode box-drawing characters for tables (`╔╠╣╚║═`)
- [ ] Professional currency formatting (`$X,XXX.XX`)
- [ ] `[BRACKET]` fields for all user-specific values
- [ ] Disclaimer at the bottom of each template
- [ ] Tested with both zero and nonzero values

### Style Guide

```python
def my_new_report(self, data: Dict[str, Any]) -> str:
    """Generate a [DESCRIPTION] report.
    
    Args:
        data: Dictionary with keys: name, date, [other required fields]
        
    Returns:
        Formatted string report with Unicode table borders.
    """
    W = self.WIDTH  # Always use self.WIDTH for consistency
    
    # Always handle missing data gracefully:
    name = data.get("name", "[NAME]")
    amount = data.get("amount", 0)
    
    # Use _fmt_currency() for all money values
    # Use _box_title(), _box_row(), etc. for consistent formatting
```

---

## Expanding Conscience Rules

The Conscience Engine evaluates all outputs. Rules live in:
`conscience/rules/` (planned module)

### Adding a Rule

```python
@conscience_rule(
    domain="legal",
    severity="high",
    description="Warn when advice may not apply across jurisdictions"
)
def check_jurisdiction_scope(output: str, context: dict) -> ConscienceResult:
    if "all states" in output.lower() and "vary by state" not in output.lower():
        return ConscienceResult(
            passed=False,
            warning="Output may overgeneralize across jurisdictions",
            suggested_addition="Note: Laws vary significantly by state."
        )
    return ConscienceResult(passed=True)
```

---

## Testing Standards

### Requirements

- Minimum **90% code coverage** for new modules
- At least **3 tests per new template**
- Tests must be **deterministic** (no random data without seed)
- Test **edge cases**: empty input, None values, missing keys

### Test Naming Convention

```python
class TestMyNewFeature:
    def test_feature_basic_functionality(self, fixture):
        """Test the happy path."""
        
    def test_feature_with_empty_data(self, fixture):
        """Test graceful handling of empty/missing data."""
        
    def test_feature_output_has_required_section(self, fixture):
        """Test that required sections are present."""
        
    def test_feature_bracket_fields_present(self, fixture):
        """Test that fillable fields use [BRACKET] notation."""
```

### Running Tests

```bash
# All tests
pytest artifacts/tests/ -v

# Specific class
pytest artifacts/tests/test_artifacts.py::TestLegalDocumentLibrary -v

# With coverage
pytest artifacts/tests/ -v --cov=artifacts --cov-report=html

# Fast mode (parallel)
pytest artifacts/tests/ -n auto
```

---

## Documentation Standards

### Docstrings

All public methods must have docstrings:

```python
def get_template(self, doc_type: str) -> str:
    """Return the complete template for the given document type.
    
    Args:
        doc_type: Template key (use list_templates() to see all available).
        
    Returns:
        Complete template string with [BRACKET] notation for fillable fields.
        
    Raises:
        KeyError: If doc_type is not found in the library.
        
    Example:
        >>> lib = LegalDocumentLibrary()
        >>> trust = lib.get_template("revocable_living_trust")
        >>> "[TRUSTOR FULL LEGAL NAME]" in trust
        True
    """
```

### README Updates

If you add a new major feature, update:
1. The "What SintraPrime Can Do" bullet list
2. The comparison table (if applicable)
3. The API Examples section
4. The Roadmap (move from roadmap to current features)

---

## Pull Request Process

1. **Branch naming:**
   - `feature/add-delaware-trust-law`
   - `fix/credit-dashboard-score-display`
   - `docs/update-contributing-guide`

2. **Commit messages:**
   ```
   feat(trust-law): add Delaware Statutory Trust template (#123)
   fix(credit): correct utilization bar display for 0% usage (#456)
   docs: update CONTRIBUTING with financial template guide
   ```

3. **PR requirements:**
   - All CI checks pass
   - At least one reviewer approval
   - Legal/financial content reviewed by domain expert (for legal/financial PRs)
   - Tests included
   - Documentation updated

4. **Merge strategy:** Squash and merge to keep history clean

---

## Questions?

Open a [Discussion](https://github.com/sintraprime/SintraPrime-Unified/discussions) or join our community channels.

*Thank you for helping build the most capable AI governance system on Earth.*
