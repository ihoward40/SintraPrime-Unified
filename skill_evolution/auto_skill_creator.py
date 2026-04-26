"""
AutoSkillCreator – Autonomous skill generation for SintraPrime-Unified.

Manus-style skill creation from examples, workflows, patterns, and templates.

Capabilities:
- Create skills from input/output examples
- Convert manual workflow steps to executable skills
- Learn patterns from successful executions
- Generate legal domain-specific skills
- Validate safety before registration
"""

from __future__ import annotations

import json
import re
import textwrap
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .skill_types import (
    Skill,
    SkillCategory,
    SkillExecution,
    SkillStatus,
    ValidationResult,
)


# ---------------------------------------------------------------------------
# Code templates
# ---------------------------------------------------------------------------

TEMPLATES: Dict[str, str] = {
    "document_processor": textwrap.dedent("""\
        # Document Processor Skill
        # Input: params['text'] (str), params.get('options', {})
        text = params.get('text', '')
        options = params.get('options', {})

        if not text:
            result = {'error': 'No text provided', 'output': None}
        else:
            # Process the document
            processed = text.strip()
            word_count = len(processed.split())
            result = {
                'output': processed,
                'word_count': word_count,
                'char_count': len(processed),
                'success': True,
            }
    """),

    "api_caller": textwrap.dedent("""\
        # API Caller Skill (uses only params, no live network in sandbox)
        # Input: params['endpoint'] (str), params.get('payload', {})
        endpoint = params.get('endpoint', '')
        payload = params.get('payload', {})
        headers = params.get('headers', {})

        # Build the request representation
        result = {
            'request': {
                'endpoint': endpoint,
                'payload': payload,
                'headers': headers,
            },
            'status': 'prepared',
            'note': 'Execute this request using an HTTP client outside the sandbox.',
        }
    """),

    "data_extractor": textwrap.dedent("""\
        # Data Extractor Skill
        # Input: params['data'] (dict or str), params.get('fields', [])
        import json as _json

        raw = params.get('data', {})
        fields = params.get('fields', [])

        if isinstance(raw, str):
            try:
                data = _json.loads(raw)
            except Exception:
                data = {'raw': raw}
        else:
            data = raw

        if fields:
            extracted = {f: data.get(f) for f in fields}
        else:
            extracted = data

        result = {
            'extracted': extracted,
            'fields_found': [f for f in fields if f in data] if fields else list(data.keys()),
            'success': True,
        }
    """),

    "report_generator": textwrap.dedent("""\
        # Report Generator Skill
        # Input: params['title'] (str), params['sections'] (list of dicts with 'heading' and 'content')
        title = params.get('title', 'Untitled Report')
        sections = params.get('sections', [])
        author = params.get('author', 'System')

        lines = [
            f'# {title}',
            f'Generated: {str(datetime.utcnow())[:19]} UTC',
            f'Author: {author}',
            '---',
            '',
        ]

        for section in sections:
            heading = section.get('heading', 'Section')
            content = section.get('content', '')
            lines.append(f'## {heading}')
            lines.append(content)
            lines.append('')

        result = {
            'report': '\\n'.join(lines),
            'section_count': len(sections),
            'success': True,
        }
    """),
}

LEGAL_TEMPLATES: Dict[str, str] = {
    "contract_analyzer": textwrap.dedent("""\
        # Contract Analyzer Skill
        # Input: params['contract_text'] (str), params.get('focus_areas', [])
        contract_text = params.get('contract_text', '')
        focus_areas = params.get('focus_areas', ['parties', 'dates', 'obligations', 'penalties'])

        findings = {}

        # Simple keyword extraction
        for area in focus_areas:
            area_lower = area.lower()
            hits = [line.strip() for line in contract_text.splitlines()
                    if area_lower in line.lower()]
            findings[area] = hits[:5]   # Top 5 matches

        result = {
            'contract_length': len(contract_text),
            'findings': findings,
            'focus_areas_analyzed': focus_areas,
            'success': True,
        }
    """),

    "deadline_tracker": textwrap.dedent("""\
        # Deadline Tracker Skill
        # Input: params['filing_date'] (str YYYY-MM-DD), params['deadline_type'] (str)
        from datetime import datetime as _dt, timedelta as _td

        filing_date_str = params.get('filing_date', '')
        deadline_type = params.get('deadline_type', 'response')

        DEADLINES = {
            'response': 30,
            'appeal': 45,
            'discovery': 90,
            'trial': 180,
            'statute_of_limitations': 365 * 2,
        }

        try:
            filing = _dt.strptime(filing_date_str, '%Y-%m-%d')
            days = DEADLINES.get(deadline_type.lower(), 30)
            deadline = filing + _td(days=days)
            result = {
                'filing_date': filing_date_str,
                'deadline_type': deadline_type,
                'deadline_date': deadline.strftime('%Y-%m-%d'),
                'days_from_filing': days,
                'success': True,
            }
        except ValueError as _ve:
            result = {'error': str(_ve), 'success': False}
    """),

    "statute_finder": textwrap.dedent("""\
        # Statute Finder Skill
        # Input: params['topic'] (str), params.get('state', 'federal')
        topic = params.get('topic', '').lower()
        state = params.get('state', 'federal').lower()

        # Common statute mappings (illustrative)
        STATUTE_MAP = {
            'employment': {'federal': ['29 U.S.C. § 201 (FLSA)', '42 U.S.C. § 2000e (Title VII)']},
            'contract': {'federal': ['UCC Article 2'], 'california': ['Cal. Civ. Code § 1549']},
            'privacy': {'federal': ['18 U.S.C. § 2701 (SCA)', '5 U.S.C. § 552a (Privacy Act)']},
            'bankruptcy': {'federal': ['11 U.S.C. § 101 et seq.']},
        }

        matches = []
        for key, by_state in STATUTE_MAP.items():
            if key in topic or topic in key:
                for st, statutes in by_state.items():
                    if state in st or st == 'federal':
                        matches.extend(statutes)

        result = {
            'topic': topic,
            'jurisdiction': state,
            'statutes_found': matches or ['No statutes found for this topic/jurisdiction combination'],
            'note': 'Verify with official legal databases before use.',
            'success': True,
        }
    """),
}

FORBIDDEN_IN_SKILL = [
    "__import__", "eval(", "compile(", "exec(",
    "os.system", "subprocess.run", "subprocess.Popen",
    "open(", "socket.socket", "shutil.rmtree", "sys.exit",
]


class AutoSkillCreator:
    """
    Autonomously generates new skills from examples, workflows, and patterns.
    """

    # ------------------------------------------------------------------
    # Core creation methods
    # ------------------------------------------------------------------

    def from_example(
        self,
        name: str,
        example_input: Dict[str, Any],
        example_output: Any,
        description: str,
        category: SkillCategory = SkillCategory.AUTOMATION,
        author: str = "auto",
    ) -> Skill:
        """
        Create a skill from an input/output example.

        Generates code that replicates the transformation.
        """
        # Build a simple demonstration skill
        code = textwrap.dedent(f"""\
            # Auto-generated from example
            # Example input : {json.dumps(example_input, default=str)[:200]}
            # Example output: {json.dumps(example_output, default=str)[:200]}

            # Retrieve parameters (mirror the example structure)
            _input = dict(params)

            # Apply transformation (developer: replace this stub with real logic)
            _expected_output = {json.dumps(example_output, default=str)}

            result = {{
                'output': _expected_output,
                'input_received': _input,
                'note': 'This is an auto-generated stub. Refine the logic.',
                'success': True,
            }}
        """)

        skill = Skill(
            name=name,
            description=description,
            category=category,
            code=code,
            parameters={k: {"type": type(v).__name__, "required": True} for k, v in example_input.items()},
            author=author,
            tags=["auto-generated", "example-based"],
            status=SkillStatus.EXPERIMENTAL,
        )
        return skill

    def from_workflow(
        self,
        workflow_steps: List[str],
        name: str = None,
        category: SkillCategory = SkillCategory.AUTOMATION,
        author: str = "workflow",
    ) -> Skill:
        """
        Convert a list of manual workflow steps into an executable skill.

        Each step becomes a commented section with a stub implementation.
        """
        if not workflow_steps:
            raise ValueError("workflow_steps cannot be empty")

        skill_name = name or "workflow_" + uuid.uuid4().hex[:6]

        lines = [
            "# Auto-generated from workflow",
            f"# Steps: {len(workflow_steps)}",
            "",
            "results = []",
            "",
        ]

        for i, step in enumerate(workflow_steps, 1):
            clean_step = step.strip()
            var_name = f"_step_{i}_result"
            lines += [
                f"# Step {i}: {clean_step}",
                f"# TODO: Implement step {i}",
                f"{var_name} = None",
                f"results.append({{'step': {i}, 'description': {json.dumps(clean_step)}, 'result': {var_name}}})",
                "",
            ]

        lines += [
            "result = {",
            "    'workflow_complete': True,",
            "    'steps_executed': len(results),",
            "    'step_results': results,",
            "    'success': True,",
            "}",
        ]

        skill = Skill(
            name=skill_name,
            description=f"Workflow skill with {len(workflow_steps)} steps: {'; '.join(workflow_steps[:3])}{'...' if len(workflow_steps) > 3 else ''}",
            category=category,
            code="\n".join(lines),
            parameters={},
            author=author,
            tags=["auto-generated", "workflow"],
            status=SkillStatus.EXPERIMENTAL,
        )
        return skill

    def from_pattern(
        self,
        successful_executions: List[SkillExecution],
        name: str = None,
        category: SkillCategory = SkillCategory.AUTOMATION,
    ) -> Optional[Skill]:
        """
        Derive a new skill from a set of successful executions.

        Extracts common parameter patterns and output structures.
        """
        if not successful_executions:
            return None

        successes = [e for e in successful_executions if e.success]
        if not successes:
            return None

        # Find common param keys
        all_keys = [set(e.input_params.keys()) for e in successes]
        common_keys = set.intersection(*all_keys) if all_keys else set()

        skill_name = name or f"pattern_skill_{uuid.uuid4().hex[:6]}"

        lines = [
            "# Auto-generated from execution pattern analysis",
            f"# Based on {len(successes)} successful executions",
            f"# Common parameters: {sorted(common_keys)}",
            "",
        ]

        for key in sorted(common_keys):
            lines.append(f"{key} = params.get({json.dumps(key)})")

        lines += [
            "",
            "# Core logic (derived from successful pattern)",
            "# TODO: Implement based on the common parameter handling",
            "result = {",
        ]

        for key in sorted(common_keys):
            lines.append(f"    {json.dumps(key)}: {key},")

        lines += [
            "    'success': True,",
            "}",
        ]

        skill = Skill(
            name=skill_name,
            description=f"Pattern-derived skill from {len(successes)} successful executions",
            category=category,
            code="\n".join(lines),
            parameters={k: {"type": "any", "required": True} for k in common_keys},
            author="pattern-analyzer",
            tags=["auto-generated", "pattern"],
            status=SkillStatus.EXPERIMENTAL,
        )
        return skill

    def generate_legal_skill(
        self,
        skill_type: str,
        author: str = "legal-generator",
    ) -> Skill:
        """
        Generate a legal domain-specific skill from built-in templates.

        skill_type: 'contract_analyzer', 'deadline_tracker', 'statute_finder'
        """
        skill_type_clean = skill_type.lower().replace(" ", "_").replace("-", "_")

        if skill_type_clean not in LEGAL_TEMPLATES:
            available = list(LEGAL_TEMPLATES.keys())
            raise ValueError(f"Unknown legal skill type '{skill_type}'. Available: {available}")

        code = LEGAL_TEMPLATES[skill_type_clean]

        # Derive metadata
        display_name = skill_type_clean.replace("_", " ").title()
        descriptions = {
            "contract_analyzer": "Extracts key terms, obligations, and parties from contract text.",
            "deadline_tracker": "Computes legal deadlines from a filing date and deadline type.",
            "statute_finder": "Identifies relevant statutes for a given legal topic and jurisdiction.",
        }

        skill = Skill(
            name=skill_type_clean,
            description=descriptions.get(skill_type_clean, f"Auto-generated {display_name} legal skill."),
            category=SkillCategory.LEGAL,
            code=code,
            parameters={},
            author=author,
            tags=["legal", "auto-generated", skill_type_clean],
            status=SkillStatus.EXPERIMENTAL,
        )
        return skill

    def from_template(
        self,
        template_name: str,
        name: str = None,
        description: str = "",
        category: SkillCategory = SkillCategory.AUTOMATION,
        author: str = "template",
    ) -> Skill:
        """
        Create a skill from a named built-in template.

        Templates: document_processor, api_caller, data_extractor, report_generator
        """
        if template_name not in TEMPLATES:
            raise ValueError(f"Unknown template '{template_name}'. Available: {list(TEMPLATES.keys())}")

        skill_name = name or f"{template_name}_{uuid.uuid4().hex[:4]}"

        skill = Skill(
            name=skill_name,
            description=description or f"Skill based on {template_name} template.",
            category=category,
            code=TEMPLATES[template_name],
            author=author,
            tags=["template", template_name],
            status=SkillStatus.ACTIVE,
        )
        return skill

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_skill(self, skill: Skill) -> ValidationResult:
        """
        Safety and quality validation before a skill is registered.

        Checks for forbidden patterns, code structure, and metadata completeness.
        """
        errors: List[str] = []
        warnings: List[str] = []

        # Metadata checks
        if not skill.name or len(skill.name) < 2:
            errors.append("Skill name is too short (min 2 chars).")
        if not skill.description or len(skill.description) < 10:
            warnings.append("Description is very short or missing.")
        if not skill.code or len(skill.code.strip()) < 5:
            errors.append("Skill code is empty or too short.")

        # Safety scan
        for pattern in FORBIDDEN_IN_SKILL:
            if pattern in skill.code:
                errors.append(f"Forbidden pattern in code: '{pattern}'")

        # Syntax check
        try:
            compile(skill.code, f"<skill:{skill.name}>", "exec")
        except SyntaxError as e:
            errors.append(f"Syntax error in code: {e}")

        # Check for 'result' assignment
        if "result" not in skill.code:
            warnings.append("Code does not assign 'result'. The skill will return None.")

        # Score: deduct for each issue
        safety_score = max(0.0, 1.0 - (len(errors) * 0.3) - (len(warnings) * 0.1))

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            safety_score=safety_score,
        )
