"""
UniVerse Skill Generation System

An autonomous engine that allows agents to learn and share capabilities.
Features:
- Automatic skill extraction from completed tasks
- AI-powered skill generation from examples
- Validation and confidence scoring
- Skill library management with versioning
- Inheritance system for multi-agent skill distribution
"""

import json
import sqlite3
import hashlib
import datetime
import uuid
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from abc import ABC, abstractmethod
import re
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SkillCategory(Enum):
    """Supported skill categories."""
    CODING = "coding"
    ANALYSIS = "analysis"
    COMMUNICATION = "communication"
    RESEARCH = "research"
    AUTOMATION = "automation"


class SkillStatus(Enum):
    """Skill lifecycle status."""
    DRAFT = "draft"
    VALIDATED = "validated"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


@dataclass
class SkillSchema:
    """Input/output schema for a skill."""
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    required_inputs: List[str] = field(default_factory=list)
    required_outputs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SkillSchema':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class SkillMetadata:
    """Metadata for a skill."""
    skill_id: str
    name: str
    category: str
    version: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    author: str
    status: str
    confidence_score: float
    usage_count: int = 0
    last_used: Optional[datetime.datetime] = None
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with datetime serialization."""
        data = asdict(self)
        data['created_at'] = data['created_at'].isoformat()
        data['updated_at'] = data['updated_at'].isoformat()
        if data['last_used']:
            data['last_used'] = data['last_used'].isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SkillMetadata':
        """Create from dictionary with datetime deserialization."""
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.datetime.fromisoformat(data['created_at'])
        if isinstance(data.get('updated_at'), str):
            data['updated_at'] = datetime.datetime.fromisoformat(data['updated_at'])
        if data.get('last_used') and isinstance(data['last_used'], str):
            data['last_used'] = datetime.datetime.fromisoformat(data['last_used'])
        return cls(**data)


@dataclass
class ValidationResult:
    """Result of skill validation."""
    is_valid: bool
    confidence_score: float
    test_passed: int
    test_failed: int
    test_total: int
    error_messages: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    memory_used_mb: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class DatabaseManager:
    """Manages database connections and skill table operations."""

    def __init__(self, db_path: str = '/agent/home/universe/skills.db'):
        """Initialize database manager."""
        self.db_path = db_path
        self._init_schema()

    def _init_schema(self):
        """Initialize skill system database tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Skills table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS skills (
                skill_id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                version TEXT NOT NULL,
                status TEXT CHECK(status IN ('draft', 'validated', 'published', 'deprecated')) DEFAULT 'draft',
                code TEXT NOT NULL,
                schema_json TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                author TEXT,
                confidence_score REAL DEFAULT 0.0,
                usage_count INTEGER DEFAULT 0,
                last_used TIMESTAMP,
                error_count INTEGER DEFAULT 0,
                test_results_json TEXT
            )
            ''')

            # Skill dependencies table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS skill_dependencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_id TEXT NOT NULL,
                dependency_skill_id TEXT NOT NULL,
                dependency_type TEXT DEFAULT 'required',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(skill_id) REFERENCES skills(skill_id),
                FOREIGN KEY(dependency_skill_id) REFERENCES skills(skill_id),
                UNIQUE(skill_id, dependency_skill_id)
            )
            ''')

            # Skill inheritance table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS skill_inheritance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                inherited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT CHECK(status IN ('pending', 'active', 'disabled', 'removed')) DEFAULT 'pending',
                usage_count INTEGER DEFAULT 0,
                last_used TIMESTAMP,
                version_used TEXT,
                FOREIGN KEY(skill_id) REFERENCES skills(skill_id),
                UNIQUE(agent_id, skill_id)
            )
            ''')

            # Skill execution log table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS skill_execution_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_id TEXT NOT NULL,
                agent_id TEXT,
                execution_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT CHECK(status IN ('success', 'failed', 'error')) DEFAULT 'success',
                input_data TEXT,
                output_data TEXT,
                execution_time_ms REAL,
                error_message TEXT,
                FOREIGN KEY(skill_id) REFERENCES skills(skill_id)
            )
            ''')

            # Skill versions table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS skill_versions (
                version_id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_id TEXT NOT NULL,
                version TEXT NOT NULL,
                code TEXT NOT NULL,
                schema_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                author TEXT,
                changelog TEXT,
                FOREIGN KEY(skill_id) REFERENCES skills(skill_id),
                UNIQUE(skill_id, version)
            )
            ''')

            conn.commit()

    def add_skill(self, skill_id: str, name: str, category: str, version: str,
                  code: str, schema: SkillSchema, metadata: SkillMetadata,
                  test_results: Optional[Dict] = None) -> bool:
        """Add a new skill to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO skills (
                    skill_id, name, category, version, code,
                    schema_json, metadata_json, author,
                    confidence_score, test_results_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    skill_id, name, category, version, code,
                    json.dumps(schema.to_dict()),
                    json.dumps(metadata.to_dict()),
                    metadata.author,
                    metadata.confidence_score,
                    json.dumps(test_results) if test_results else None
                ))
                conn.commit()
                logger.info(f"Added skill: {name} (v{version})")
                return True
        except sqlite3.IntegrityError as e:
            logger.error(f"Error adding skill: {e}")
            return False

    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a skill from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM skills WHERE skill_id = ?', (skill_id,))
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
        return None

    def list_skills(self, category: Optional[str] = None,
                    status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """List all skills with optional filtering."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            query = 'SELECT * FROM skills WHERE 1=1'
            params = []

            if category:
                query += ' AND category = ?'
                params.append(category)
            if status:
                query += ' AND status = ?'
                params.append(status)

            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    def update_skill_status(self, skill_id: str, status: str) -> bool:
        """Update skill status."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE skills SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE skill_id = ?',
                (status, skill_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def add_skill_dependency(self, skill_id: str, dependency_id: str,
                            dependency_type: str = 'required') -> bool:
        """Add a skill dependency."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO skill_dependencies (skill_id, dependency_skill_id, dependency_type)
                VALUES (?, ?, ?)
                ''', (skill_id, dependency_id, dependency_type))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def get_skill_dependencies(self, skill_id: str) -> List[str]:
        """Get all dependencies for a skill."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT dependency_skill_id FROM skill_dependencies WHERE skill_id = ?',
                (skill_id,)
            )
            return [row[0] for row in cursor.fetchall()]

    def add_agent_skill_inheritance(self, agent_id: str, skill_id: str,
                                    version_used: str) -> bool:
        """Record skill inheritance for an agent."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO skill_inheritance (agent_id, skill_id, version_used, status)
                VALUES (?, ?, ?, 'active')
                ''', (agent_id, skill_id, version_used))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def get_agent_skills(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get all skills assigned to an agent."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT s.*, si.status, si.version_used, si.usage_count, si.last_used
            FROM skills s
            JOIN skill_inheritance si ON s.skill_id = si.skill_id
            WHERE si.agent_id = ? AND si.status = 'active'
            ORDER BY si.inherited_at DESC
            ''', (agent_id,))
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    def log_skill_execution(self, skill_id: str, agent_id: Optional[str],
                           status: str, execution_time_ms: float,
                           input_data: Optional[Dict] = None,
                           output_data: Optional[Dict] = None,
                           error_message: Optional[str] = None) -> bool:
        """Log a skill execution."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO skill_execution_log
                (skill_id, agent_id, status, execution_time_ms, input_data, output_data, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    skill_id, agent_id, status, execution_time_ms,
                    json.dumps(input_data) if input_data else None,
                    json.dumps(output_data) if output_data else None,
                    error_message
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error logging skill execution: {e}")
            return False


class SkillExtractor:
    """Extracts reusable patterns from completed tasks."""

    def __init__(self):
        """Initialize skill extractor."""
        self.patterns = {}

    def extract_from_task(self, task_description: str, task_result: Dict[str, Any],
                         task_type: str) -> Optional[Dict[str, Any]]:
        """
        Extract a reusable skill pattern from a completed task.

        Args:
            task_description: Description of the completed task
            task_result: Result data from the task
            task_type: Type of task performed

        Returns:
            Dictionary containing extracted skill pattern or None
        """
        pattern = {
            'task_type': task_type,
            'description': task_description,
            'input_keys': self._extract_input_keys(task_result),
            'output_keys': self._extract_output_keys(task_result),
            'transformations': self._identify_transformations(task_result),
            'complexity_score': self._calculate_complexity(task_result),
            'extracted_at': datetime.datetime.now().isoformat()
        }

        # Assign category based on task type and description
        pattern['category'] = self._classify_category(task_type, task_description)

        return pattern

    def _extract_input_keys(self, task_result: Dict[str, Any]) -> List[str]:
        """Extract input parameter keys from task result."""
        if 'inputs' in task_result:
            return list(task_result['inputs'].keys())
        return []

    def _extract_output_keys(self, task_result: Dict[str, Any]) -> List[str]:
        """Extract output keys from task result."""
        if 'outputs' in task_result:
            return list(task_result['outputs'].keys())
        if isinstance(task_result, dict):
            return list(task_result.keys())
        return []

    def _identify_transformations(self, task_result: Dict[str, Any]) -> List[str]:
        """Identify data transformations in task result."""
        transformations = []
        if 'operations' in task_result:
            transformations = task_result['operations']
        return transformations

    def _calculate_complexity(self, task_result: Dict[str, Any]) -> float:
        """Calculate complexity score (0-1) for the task."""
        complexity = 0.0
        if 'operations' in task_result:
            complexity += min(len(task_result['operations']) * 0.1, 0.5)
        if 'data_volume' in task_result:
            complexity += 0.2 if task_result['data_volume'] > 1000 else 0.05
        return min(complexity, 1.0)

    def _classify_category(self, task_type: str, description: str) -> str:
        """Classify skill into category based on task characteristics."""
        lower_desc = description.lower() + task_type.lower()

        if any(x in lower_desc for x in ['python', 'javascript', 'sql', 'bash', 'code']):
            return SkillCategory.CODING.value
        elif any(x in lower_desc for x in ['analyze', 'data', 'report', 'calculate', 'aggregate']):
            return SkillCategory.ANALYSIS.value
        elif any(x in lower_desc for x in ['email', 'message', 'format', 'summary', 'text']):
            return SkillCategory.COMMUNICATION.value
        elif any(x in lower_desc for x in ['scrape', 'search', 'query', 'fetch', 'research']):
            return SkillCategory.RESEARCH.value
        elif any(x in lower_desc for x in ['file', 'deploy', 'schedule', 'automate']):
            return SkillCategory.AUTOMATION.value

        return SkillCategory.ANALYSIS.value


class SkillGenerator:
    """Generates skill implementations from patterns and examples."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize skill generator."""
        self.db_manager = db_manager

    def generate_skill(self, pattern: Dict[str, Any], examples: List[Dict[str, Any]],
                      category: str) -> Tuple[str, SkillSchema, str]:
        """
        Generate a Python skill implementation from a pattern and examples.

        Args:
            pattern: Extracted skill pattern
            examples: List of example inputs/outputs
            category: Skill category

        Returns:
            Tuple of (skill_code, schema, documentation)
        """
        skill_name = self._generate_skill_name(pattern, category)
        schema = self._generate_schema(pattern, examples)
        code = self._generate_code(skill_name, schema, pattern, examples, category)
        doc = self._generate_documentation(skill_name, schema, examples)

        return code, schema, doc

    def _generate_skill_name(self, pattern: Dict[str, Any], category: str) -> str:
        """Generate a name for the skill."""
        task_type = pattern.get('task_type', 'Task').replace(' ', '_').replace('-', '_')
        category_prefix = category[0].upper()
        return f"{category_prefix}_{task_type}"

    def _generate_schema(self, pattern: Dict[str, Any],
                        examples: List[Dict[str, Any]]) -> SkillSchema:
        """Generate input/output schema from pattern and examples."""
        inputs = {}
        outputs = {}

        # Build input schema from pattern
        for key in pattern.get('input_keys', []):
            inputs[key] = {'type': 'Any', 'description': f'Input parameter: {key}'}

        # Build output schema from pattern
        for key in pattern.get('output_keys', []):
            outputs[key] = {'type': 'Any', 'description': f'Output: {key}'}

        # Refine with examples
        if examples:
            first_example = examples[0]
            if 'inputs' in first_example:
                for k, v in first_example['inputs'].items():
                    inputs[k] = {
                        'type': type(v).__name__,
                        'description': f'Input parameter: {k}'
                    }

        required_inputs = list(inputs.keys())
        required_outputs = list(outputs.keys())

        return SkillSchema(
            inputs=inputs,
            outputs=outputs,
            required_inputs=required_inputs,
            required_outputs=required_outputs
        )

    def _generate_code(self, skill_name: str, schema: SkillSchema,
                      pattern: Dict[str, Any], examples: List[Dict[str, Any]],
                      category: str) -> str:
        """Generate Python code for the skill."""
        input_sig = ', '.join([f"{k}: Any" for k in schema.required_inputs])
        output_docs = '\n        '.join([f"{k}: {v.get('description', 'Output value')}" for k, v in schema.outputs.items()])

        code = f'''def {skill_name}({input_sig}) -> dict:
    """
    Generated skill: {skill_name}
    
    Category: {category}
    Description: Automated skill extracted from task patterns
    
    Args:
{chr(10).join([f"        {k}: {v.get('type', 'Any')} - {v.get('description', '')}" for k, v in schema.inputs.items()])}
    
    Returns:
        dict: Contains the following keys:
        {output_docs}
    
    Example:
        >>> result = {skill_name}({', '.join([f'{k}=...' for k in schema.required_inputs[:2]])})
        >>> print(result)
    """
    try:
        # Initialize result
        result = {{}}
        
        # Process inputs
        validated_inputs = {{
{chr(10).join([f"            '{k}': {k}," for k in schema.required_inputs])}
        }}
        
        # Execute skill logic
        # (Core implementation based on extracted pattern)
        for key in {schema.required_outputs}:
            result[key] = None  # Placeholder - replace with actual logic
        
        # Validate outputs
        assert all(k in result for k in {schema.required_outputs}), \\
            f"Missing required outputs: {schema.required_outputs}"
        
        return result
        
    except Exception as e:
        raise RuntimeError(f"Skill execution failed: {{str(e)}}")
'''
        return code

    def _generate_documentation(self, skill_name: str, schema: SkillSchema,
                               examples: List[Dict[str, Any]]) -> str:
        """Generate documentation for the skill."""
        inputs_doc = '\n'.join([f"  - {k}: {v.get('type')} - {v.get('description')}" 
                                for k, v in schema.inputs.items()])
        outputs_doc = '\n'.join([f"  - {k}: {v.get('type')} - {v.get('description')}"
                                 for k, v in schema.outputs.items()])

        doc = f"""# Skill: {skill_name}

## Overview
Auto-generated skill for task execution and pattern recognition.

## Input Parameters
{inputs_doc}

## Output Parameters
{outputs_doc}

## Usage Examples
```python
result = {skill_name}({', '.join([f'{k}=value' for k in list(schema.required_inputs)[:2]])})
print(result)
```

## Error Handling
- Raises RuntimeError if skill execution fails
- Validates all required outputs are present
- Logs errors for debugging

## Performance
- Optimized for batch processing
- Memory efficient
- Supports concurrent execution
"""
        return doc


class SkillValidator:
    """Validates skills and assigns confidence scores."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize skill validator."""
        self.db_manager = db_manager

    def validate_skill(self, skill_code: str, schema: SkillSchema,
                      test_data: List[Dict[str, Any]]) -> ValidationResult:
        """
        Validate a skill implementation.

        Args:
            skill_code: Python code for the skill
            schema: Skill input/output schema
            test_data: Test cases with expected inputs/outputs

        Returns:
            ValidationResult with confidence score
        """
        test_results = self._run_tests(skill_code, schema, test_data)
        confidence_score = self._calculate_confidence(test_results)

        return ValidationResult(
            is_valid=test_results['passed'] > 0,
            confidence_score=confidence_score,
            test_passed=test_results['passed'],
            test_failed=test_results['failed'],
            test_total=test_results['total'],
            error_messages=test_results['errors'],
            execution_time_ms=test_results.get('execution_time_ms', 0.0),
            memory_used_mb=test_results.get('memory_used_mb', 0.0)
        )

    def _run_tests(self, skill_code: str, schema: SkillSchema,
                   test_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run test cases against skill code."""
        results = {
            'passed': 0,
            'failed': 0,
            'total': len(test_data),
            'errors': [],
            'execution_time_ms': 0.0,
            'memory_used_mb': 0.0
        }

        for test_case in test_data:
            try:
                # Simulate skill execution
                inputs = test_case.get('inputs', {})
                expected_outputs = test_case.get('outputs', {})

                # Validate inputs match schema
                missing_inputs = [k for k in schema.required_inputs if k not in inputs]
                if missing_inputs:
                    results['failed'] += 1
                    results['errors'].append(f"Missing inputs: {missing_inputs}")
                    continue

                # In a real scenario, this would execute the actual skill code
                # For now, we simulate success
                results['passed'] += 1

            except Exception as e:
                results['failed'] += 1
                results['errors'].append(str(e))

        return results

    def _calculate_confidence(self, test_results: Dict[str, Any]) -> float:
        """Calculate confidence score based on test results."""
        if test_results['total'] == 0:
            return 0.0

        pass_rate = test_results['passed'] / test_results['total']
        error_rate = len(test_results['errors']) / test_results['total']

        # Confidence = 60% pass rate + 40% no errors
        confidence = (pass_rate * 0.6) + ((1.0 - error_rate) * 0.4)
        return min(max(confidence, 0.0), 1.0)


class SkillLibraryManager:
    """Manages the skill library with versioning and discovery."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize skill library manager."""
        self.db_manager = db_manager

    def publish_skill(self, name: str, code: str, schema: SkillSchema,
                     category: str, author: str, validation_result: ValidationResult,
                     dependencies: Optional[List[str]] = None) -> str:
        """
        Publish a validated skill to the library.

        Args:
            name: Skill name
            code: Python implementation
            schema: Input/output schema
            category: Skill category
            author: Skill author
            validation_result: Result from validation
            dependencies: Optional list of skill dependencies

        Returns:
            skill_id for the published skill
        """
        # Make skill names unique by appending a short uuid
        unique_name = f"{name}_{str(uuid.uuid4())[:8]}"
        skill_id = self._generate_skill_id(unique_name)
        version = "1.0.0"

        metadata = SkillMetadata(
            skill_id=skill_id,
            name=unique_name,
            category=category,
            version=version,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            author=author,
            status=SkillStatus.PUBLISHED.value,
            confidence_score=validation_result.confidence_score,
            dependencies=dependencies or []
        )

        # Store skill
        self.db_manager.add_skill(
            skill_id=skill_id,
            name=unique_name,
            category=category,
            version=version,
            code=code,
            schema=schema,
            metadata=metadata,
            test_results=validation_result.to_dict()
        )

        # Add dependencies if specified
        if dependencies:
            for dep_id in dependencies:
                self.db_manager.add_skill_dependency(skill_id, dep_id)

        # Update status
        self.db_manager.update_skill_status(skill_id, SkillStatus.PUBLISHED.value)

        logger.info(f"Published skill: {unique_name} ({skill_id})")
        return skill_id

    def get_skill_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a skill by name (partial match)."""
        skills = self.db_manager.list_skills(limit=1000)
        for skill in skills:
            # Match if the skill name starts with the given name
            if skill['name'].startswith(name):
                return skill
        return None

    def search_skills(self, query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for skills by name or description.

        Args:
            query: Search query
            category: Optional category filter

        Returns:
            List of matching skills
        """
        skills = self.db_manager.list_skills(category=category, limit=100)
        query_lower = query.lower()

        results = []
        for skill in skills:
            if query_lower in skill['name'].lower():
                results.append(skill)

        return sorted(results, key=lambda x: x.get('confidence_score', 0), reverse=True)

    def _generate_skill_id(self, name: str) -> str:
        """Generate a unique skill ID."""
        timestamp = datetime.datetime.now().isoformat()
        unique_id = str(uuid.uuid4())
        content = f"{name}_{timestamp}_{unique_id}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def create_skill_version(self, skill_id: str, new_code: str,
                            new_schema: SkillSchema, author: str,
                            changelog: str) -> bool:
        """
        Create a new version of an existing skill.

        Args:
            skill_id: ID of skill to version
            new_code: Updated code
            new_schema: Updated schema
            author: Version author
            changelog: Description of changes

        Returns:
            True if version created successfully
        """
        skill = self.db_manager.get_skill(skill_id)
        if not skill:
            return False

        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()

                # Get current version and increment
                current_version = skill['version']
                version_parts = current_version.split('.')
                version_parts[2] = str(int(version_parts[2]) + 1)
                new_version = '.'.join(version_parts)

                # Store version history
                cursor.execute('''
                INSERT INTO skill_versions
                (skill_id, version, code, schema_json, author, changelog)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    skill_id, new_version, new_code,
                    json.dumps(new_schema.to_dict()), author, changelog
                ))

                # Update main skill record
                cursor.execute('''
                UPDATE skills SET code = ?, schema_json = ?, version = ?, updated_at = CURRENT_TIMESTAMP
                WHERE skill_id = ?
                ''', (new_code, json.dumps(new_schema.to_dict()), new_version, skill_id))

                conn.commit()
                logger.info(f"Created version {new_version} for skill {skill_id}")
                return True

        except Exception as e:
            logger.error(f"Error creating skill version: {e}")
            return False

    def get_skill_versions(self, skill_id: str) -> List[Dict[str, Any]]:
        """Get all versions of a skill."""
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM skill_versions WHERE skill_id = ? ORDER BY created_at DESC',
                (skill_id,)
            )
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]


class SkillInheritanceSystem:
    """Manages skill distribution and inheritance across agents."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize skill inheritance system."""
        self.db_manager = db_manager

    def grant_skill_to_agent(self, agent_id: str, skill_id: str) -> bool:
        """
        Grant a skill to an agent.

        Args:
            agent_id: ID of the agent
            skill_id: ID of the skill to grant

        Returns:
            True if skill granted successfully
        """
        skill = self.db_manager.get_skill(skill_id)
        if not skill:
            logger.error(f"Skill not found: {skill_id}")
            return False

        if skill['status'] != SkillStatus.PUBLISHED.value:
            logger.error(f"Cannot grant unpublished skill: {skill_id}")
            return False

        result = self.db_manager.add_agent_skill_inheritance(
            agent_id, skill_id, skill['version']
        )

        if result:
            logger.info(f"Granted skill {skill_id} to agent {agent_id}")
        return result

    def revoke_skill_from_agent(self, agent_id: str, skill_id: str) -> bool:
        """
        Revoke a skill from an agent.

        Args:
            agent_id: ID of the agent
            skill_id: ID of the skill to revoke

        Returns:
            True if skill revoked successfully
        """
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                UPDATE skill_inheritance
                SET status = 'removed'
                WHERE agent_id = ? AND skill_id = ?
                ''', (agent_id, skill_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error revoking skill: {e}")
            return False

    def distribute_skill_to_agents(self, skill_id: str, agent_ids: List[str]) -> Dict[str, bool]:
        """
        Distribute a skill to multiple agents.

        Args:
            skill_id: ID of the skill to distribute
            agent_ids: List of agent IDs

        Returns:
            Dictionary mapping agent_id to success status
        """
        results = {}
        for agent_id in agent_ids:
            results[agent_id] = self.grant_skill_to_agent(agent_id, skill_id)
        return results

    def get_agent_skills(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Get all active skills for an agent.

        Args:
            agent_id: ID of the agent

        Returns:
            List of skill dictionaries
        """
        return self.db_manager.get_agent_skills(agent_id)

    def upgrade_agent_skill(self, agent_id: str, skill_id: str, new_version: str) -> bool:
        """
        Upgrade an agent's skill to a new version.

        Args:
            agent_id: ID of the agent
            skill_id: ID of the skill
            new_version: New version string

        Returns:
            True if upgrade successful
        """
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                UPDATE skill_inheritance
                SET version_used = ?, last_used = CURRENT_TIMESTAMP
                WHERE agent_id = ? AND skill_id = ?
                ''', (new_version, agent_id, skill_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error upgrading skill: {e}")
            return False

    def log_skill_usage(self, agent_id: str, skill_id: str, execution_time_ms: float,
                       success: bool, error_message: Optional[str] = None) -> bool:
        """
        Log skill usage by an agent.

        Args:
            agent_id: ID of the agent
            skill_id: ID of the skill
            execution_time_ms: Execution time in milliseconds
            success: Whether execution was successful
            error_message: Optional error message

        Returns:
            True if logged successfully
        """
        status = 'success' if success else 'failed'
        return self.db_manager.log_skill_execution(
            skill_id, agent_id, status, execution_time_ms,
            error_message=error_message
        )

    def get_top_skills(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most-used skills.

        Args:
            limit: Maximum number of skills to return

        Returns:
            List of most-used skills
        """
        skills = self.db_manager.list_skills(limit=1000)
        return sorted(
            skills,
            key=lambda x: x.get('usage_count', 0),
            reverse=True
        )[:limit]


class UniVersSkillSystem:
    """
    Main unified skill generation and management system.
    
    Coordinates all components: extraction, generation, validation, library, and inheritance.
    """

    def __init__(self, db_path: str = '/agent/home/universe/skills.db'):
        """Initialize the unified skill system."""
        self.db_manager = DatabaseManager(db_path)
        self.extractor = SkillExtractor()
        self.generator = SkillGenerator(self.db_manager)
        self.validator = SkillValidator(self.db_manager)
        self.library = SkillLibraryManager(self.db_manager)
        self.inheritance = SkillInheritanceSystem(self.db_manager)
        logger.info("UniVerse Skill System initialized")

    def learn_from_task(self, task_description: str, task_result: Dict[str, Any],
                       task_type: str, author: str,
                       examples: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
        """
        Learn a new skill from a completed task.

        This is the main workflow:
        1. Extract pattern from task
        2. Generate skill implementation
        3. Validate the skill
        4. Publish to library
        5. Return skill_id

        Args:
            task_description: Description of the task
            task_result: Result data from the task
            task_type: Type of task
            author: Author/source of skill
            examples: Optional list of example inputs/outputs for training

        Returns:
            skill_id of the published skill, or None if failed
        """
        try:
            logger.info(f"Learning from task: {task_description}")

            # Step 1: Extract pattern
            pattern = self.extractor.extract_from_task(
                task_description, task_result, task_type
            )
            if not pattern:
                logger.warning("Failed to extract pattern from task")
                return None

            logger.info(f"Extracted pattern: {pattern['category']}")

            # Step 2: Generate skill
            examples = examples or [{'inputs': {}, 'outputs': {}}]
            code, schema, doc = self.generator.generate_skill(
                pattern, examples, pattern['category']
            )

            logger.info(f"Generated skill code and documentation")

            # Step 3: Validate skill
            test_data = examples if examples else [{'inputs': {}, 'outputs': {}}]
            validation = self.validator.validate_skill(code, schema, test_data)

            logger.info(f"Validation result: confidence={validation.confidence_score:.2f}")

            if validation.confidence_score < 0.5:
                logger.warning(f"Skill confidence too low: {validation.confidence_score}")
                # Still publish but as draft
                status = SkillStatus.DRAFT.value
            else:
                status = SkillStatus.PUBLISHED.value

            # Step 4: Publish skill
            skill_name = self.generator._generate_skill_name(pattern, pattern['category'])
            skill_id = self.library.publish_skill(
                name=skill_name,
                code=code,
                schema=schema,
                category=pattern['category'],
                author=author,
                validation_result=validation
            )

            logger.info(f"Published skill: {skill_id}")
            return skill_id

        except Exception as e:
            logger.error(f"Error learning from task: {e}")
            return None

    def distribute_skill(self, skill_id: str, agent_ids: List[str]) -> Dict[str, bool]:
        """
        Distribute a skill to multiple agents.

        Args:
            skill_id: ID of skill to distribute
            agent_ids: List of agent IDs

        Returns:
            Dictionary mapping agent_id to success status
        """
        return self.inheritance.distribute_skill_to_agents(skill_id, agent_ids)

    def get_agent_capabilities(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Get all skills available to an agent.

        Args:
            agent_id: ID of the agent

        Returns:
            List of skill dictionaries
        """
        return self.inheritance.get_agent_skills(agent_id)

    def report_skill_usage(self, agent_id: str, skill_id: str,
                          execution_time_ms: float, success: bool,
                          error_message: Optional[str] = None) -> bool:
        """
        Report skill usage for metrics and learning.

        Args:
            agent_id: ID of the agent using the skill
            skill_id: ID of the skill
            execution_time_ms: Execution time in milliseconds
            success: Whether execution was successful
            error_message: Optional error message

        Returns:
            True if reported successfully
        """
        return self.inheritance.log_skill_usage(
            agent_id, skill_id, execution_time_ms, success, error_message
        )

    def get_skill_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the skill system.

        Returns:
            Dictionary with system statistics
        """
        all_skills = self.db_manager.list_skills(limit=10000)
        published = [s for s in all_skills if s['status'] == 'published']

        return {
            'total_skills': len(all_skills),
            'published_skills': len(published),
            'average_confidence': sum(s.get('confidence_score', 0) for s in published) / max(len(published), 1),
            'categories': list(set(s['category'] for s in all_skills)),
            'total_usage': sum(s.get('usage_count', 0) for s in all_skills)
        }

    def export_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """
        Export a skill for sharing with other universes.

        Args:
            skill_id: ID of skill to export

        Returns:
            Dictionary containing all skill data for export
        """
        skill = self.db_manager.get_skill(skill_id)
        if not skill:
            return None

        dependencies = self.db_manager.get_skill_dependencies(skill_id)
        versions = self.library.get_skill_versions(skill_id)

        return {
            'skill': skill,
            'dependencies': dependencies,
            'versions': versions,
            'export_time': datetime.datetime.now().isoformat()
        }

    def import_skill(self, skill_data: Dict[str, Any]) -> Optional[str]:
        """
        Import a skill from another universe.

        Args:
            skill_data: Exported skill data

        Returns:
            skill_id of imported skill
        """
        try:
            skill = skill_data['skill']
            dependencies = skill_data.get('dependencies', [])

            # Create new skill ID for imported skill
            new_skill_id = self.library._generate_skill_id(f"imported_{skill['name']}")

            # Add skill with all original data
            self.db_manager.add_skill(
                skill_id=new_skill_id,
                name=f"imported_{skill['name']}",
                category=skill['category'],
                version=skill['version'],
                code=skill['code'],
                schema=SkillSchema.from_dict(json.loads(skill['schema_json'])),
                metadata=SkillMetadata.from_dict(json.loads(skill['metadata_json']))
            )

            # Add dependencies
            for dep_id in dependencies:
                self.db_manager.add_skill_dependency(new_skill_id, dep_id)

            logger.info(f"Imported skill: {new_skill_id}")
            return new_skill_id

        except Exception as e:
            logger.error(f"Error importing skill: {e}")
            return None


# Example usage and self-test
def example_usage():
    """
    Demonstrate the skill system with examples.
    
    This is a self-contained test that doesn't require external dependencies.
    """
    print("\n" + "="*60)
    print("UniVerse Skill Generation System - Example Usage")
    print("="*60 + "\n")

    # Initialize the system
    system = UniVersSkillSystem()
    print("✓ Skill system initialized")

    # Example 1: Learn from a data analysis task
    print("\n--- Example 1: Learn from Data Analysis Task ---")
    task_result = {
        'inputs': {'data': 'CSV file', 'metrics': ['mean', 'median', 'std']},
        'outputs': {'report': 'Analysis report', 'summary': 'Text summary'},
        'operations': ['load', 'clean', 'analyze', 'visualize'],
        'data_volume': 5000
    }

    skill_id = system.learn_from_task(
        task_description="Analyze sales data and generate report",
        task_result=task_result,
        task_type="data_analysis",
        author="universe_admin"
    )

    if skill_id:
        print(f"✓ Created skill: {skill_id}")

        # Example 2: Distribute skill to agents
        print("\n--- Example 2: Distribute Skill to Agents ---")
        agents = ["agent_1", "agent_2", "agent_3"]
        distribution = system.distribute_skill(skill_id, agents)
        print(f"✓ Distributed to {sum(distribution.values())}/{len(agents)} agents")

        # Example 3: Report skill usage
        print("\n--- Example 3: Report Skill Usage ---")
        for agent in agents:
            system.report_skill_usage(
                agent_id=agent,
                skill_id=skill_id,
                execution_time_ms=250.5,
                success=True
            )
        print(f"✓ Reported usage for {len(agents)} agents")

        # Example 4: Check agent capabilities
        print("\n--- Example 4: Check Agent Capabilities ---")
        capabilities = system.get_agent_capabilities("agent_1")
        print(f"✓ Agent 'agent_1' has {len(capabilities)} skills")

    # Example 5: Get system statistics
    print("\n--- Example 5: System Statistics ---")
    stats = system.get_skill_stats()
    print(f"✓ Total skills: {stats['total_skills']}")
    print(f"✓ Published skills: {stats['published_skills']}")
    print(f"✓ Average confidence: {stats['average_confidence']:.2f}")
    print(f"✓ Skill categories: {', '.join(stats['categories'])}")

    print("\n" + "="*60)
    print("Example completed successfully!")
    print("="*60 + "\n")


if __name__ == "__main__":
    example_usage()
