"""
SintraPrime-Unified Workflow API
FastAPI router providing REST endpoints and WebSocket TUI for workflow management.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from workflow_builder.workflow_engine import (
    WorkflowGraph,
    WorkflowSerializer,
    WorkflowStatus,
    WorkflowTemplateRegistry,
    create_workflow,
)
from workflow_builder.workflow_schema import (
    ReactFlowConverter,
    WorkflowCodeGenerator,
    WorkflowSchemaValidator,
    export_workflow_to_python,
    export_workflow_to_react_flow,
    get_node_styles,
    get_workflow_json_schema,
    import_workflow_from_react_flow,
)
from workflow_builder.web_tui import tui_handler

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database Setup
# ---------------------------------------------------------------------------

DB_PATH = Path("workflow_builder/workflows.db")


def get_db_connection() -> sqlite3.Connection:
    """Create a new SQLite database connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize the workflow database schema."""
    conn = get_db_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                version TEXT DEFAULT '1.0.0',
                author TEXT DEFAULT '',
                status TEXT DEFAULT 'draft',
                tags TEXT DEFAULT '[]',
                workflow_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workflow_executions (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                status TEXT DEFAULT 'running',
                current_node_id TEXT,
                completed_nodes TEXT DEFAULT '[]',
                failed_nodes TEXT DEFAULT '[]',
                variables TEXT DEFAULT '{}',
                error_message TEXT DEFAULT '',
                started_at TEXT NOT NULL,
                completed_at TEXT,
                logs TEXT DEFAULT '[]',
                FOREIGN KEY (workflow_id) REFERENCES workflows(id)
            )
        """)
        conn.commit()
        logger.info("Workflow database initialized.")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class WorkflowCreateRequest(BaseModel):
    """Request body for creating a workflow."""
    name: str = Field(..., min_length=1, max_length=200, description="Workflow name")
    description: str = Field("", description="Workflow description")
    nodes: List[Dict[str, Any]] = Field(default_factory=list, description="React Flow nodes")
    edges: List[Dict[str, Any]] = Field(default_factory=list, description="React Flow edges")
    tags: List[str] = Field(default_factory=list)
    author: str = Field("", description="Workflow author")
    version: str = Field("1.0.0")


class WorkflowUpdateRequest(BaseModel):
    """Request body for updating a workflow."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    edges: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None


class WorkflowRunRequest(BaseModel):
    """Request body for running a workflow."""
    variables: Dict[str, Any] = Field(default_factory=dict, description="Initial workflow variables")
    dry_run: bool = Field(False, description="Simulate execution without running actions")


class WorkflowResponse(BaseModel):
    """Workflow response model."""
    id: str
    name: str
    description: str
    version: str
    author: str
    status: str
    tags: List[str]
    node_count: int
    edge_count: int
    created_at: str
    updated_at: str


class WorkflowExecutionResponse(BaseModel):
    """Workflow execution response model."""
    execution_id: str
    workflow_id: str
    status: str
    current_node_id: Optional[str]
    completed_nodes: List[str]
    failed_nodes: List[str]
    variables: Dict[str, Any]
    error_message: str
    started_at: str
    completed_at: Optional[str]
    logs: List[str]


class WorkflowValidationResponse(BaseModel):
    """Workflow validation response model."""
    valid: bool
    errors: List[str]
    warnings: List[str]
    statistics: Dict[str, Any]


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _save_workflow_to_db(graph: WorkflowGraph, conn: sqlite3.Connection) -> None:
    """Save or update a workflow in the database."""
    now = datetime.utcnow().isoformat()
    rf_data = ReactFlowConverter.graph_to_react_flow(graph)
    workflow_json = json.dumps(rf_data)
    tags_json = json.dumps(graph.tags)

    existing = conn.execute("SELECT id FROM workflows WHERE id = ?", (graph.workflow_id,)).fetchone()
    if existing:
        conn.execute(
            """
            UPDATE workflows
            SET name=?, description=?, version=?, author=?, status=?,
                tags=?, workflow_json=?, updated_at=?
            WHERE id=?
            """,
            (
                graph.name, graph.description, graph.version, graph.author,
                graph.status.value, tags_json, workflow_json, now, graph.workflow_id,
            ),
        )
    else:
        if not graph.created_at:
            graph.created_at = now
        conn.execute(
            """
            INSERT INTO workflows (id, name, description, version, author, status, tags, workflow_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                graph.workflow_id, graph.name, graph.description, graph.version,
                graph.author, graph.status.value, tags_json, workflow_json,
                graph.created_at, now,
            ),
        )
    conn.commit()


def _load_workflow_from_db(workflow_id: str, conn: sqlite3.Connection) -> Optional[WorkflowGraph]:
    """Load a workflow from the database by ID."""
    row = conn.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
    if not row:
        return None
    rf_data = json.loads(row["workflow_json"])
    graph = ReactFlowConverter.react_flow_to_graph(rf_data)
    graph.created_at = row["created_at"]
    graph.updated_at = row["updated_at"]
    return graph


def _row_to_workflow_response(row: sqlite3.Row) -> WorkflowResponse:
    """Convert a database row to a WorkflowResponse."""
    rf_data = json.loads(row["workflow_json"])
    return WorkflowResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        version=row["version"],
        author=row["author"],
        status=row["status"],
        tags=json.loads(row["tags"]),
        node_count=len(rf_data.get("nodes", [])),
        edge_count=len(rf_data.get("edges", [])),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


# ---------------------------------------------------------------------------
# FastAPI Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.on_event("startup")
async def startup_event():
    init_db()


# ---------------------------------------------------------------------------
# GET /workflows — list all workflows
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[WorkflowResponse], summary="List all workflows")
async def list_workflows(
    status_filter: Optional[str] = None,
    tag_filter: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[WorkflowResponse]:
    """
    List all stored workflows with optional filtering.
    - **status_filter**: Filter by workflow status (draft, active, completed, etc.)
    - **tag_filter**: Filter by tag
    - **search**: Full-text search on name and description
    - **limit**: Maximum number of results (default 50)
    - **offset**: Pagination offset
    """
    conn = get_db_connection()
    try:
        query = "SELECT * FROM workflows WHERE 1=1"
        params: List[Any] = []

        if status_filter:
            query += " AND status = ?"
            params.append(status_filter)
        if search:
            query += " AND (name LIKE ? OR description LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        if tag_filter:
            query += " AND tags LIKE ?"
            params.append(f'%"{tag_filter}"%')

        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        return [_row_to_workflow_response(row) for row in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# POST /workflows — create a workflow
# ---------------------------------------------------------------------------

@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED,
             summary="Create a new workflow")
async def create_workflow_endpoint(request: WorkflowCreateRequest) -> WorkflowResponse:
    """
    Create a new workflow from React Flow JSON data.
    The workflow is stored in the SQLite database.
    """
    rf_data = {
        "id": str(uuid.uuid4()),
        "name": request.name,
        "description": request.description,
        "version": request.version,
        "author": request.author,
        "tags": request.tags,
        "nodes": request.nodes,
        "edges": request.edges,
    }

    schema_errors = WorkflowSchemaValidator.validate_react_flow_json(rf_data)
    if schema_errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Invalid workflow schema", "errors": schema_errors},
        )

    try:
        graph = ReactFlowConverter.react_flow_to_graph(rf_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse workflow: {exc}",
        )

    conn = get_db_connection()
    try:
        _save_workflow_to_db(graph, conn)
        row = conn.execute("SELECT * FROM workflows WHERE id = ?", (graph.workflow_id,)).fetchone()
        return _row_to_workflow_response(row)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GET /workflows/templates — list built-in templates
# ---------------------------------------------------------------------------

@router.get("/templates", summary="List built-in workflow templates")
async def list_templates_endpoint(tag_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all built-in legal workflow templates.
    Optionally filter by tag.
    """
    templates = WorkflowTemplateRegistry.list_templates()
    if tag_filter:
        templates = [t for t in templates if tag_filter.lower() in [tag.lower() for tag in t.get("tags", [])]]
    return templates


# ---------------------------------------------------------------------------
# GET /workflows/templates/{template_id} — get template definition
# ---------------------------------------------------------------------------

@router.get("/templates/{template_id}", summary="Get a specific template")
async def get_template_endpoint(template_id: str) -> Dict[str, Any]:
    """
    Get the full React Flow JSON definition of a built-in template.
    """
    template = WorkflowTemplateRegistry.get(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found.",
        )
    return ReactFlowConverter.graph_to_react_flow(template)


# ---------------------------------------------------------------------------
# POST /workflows/templates/{template_id}/clone — clone a template
# ---------------------------------------------------------------------------

@router.post("/templates/{template_id}/clone", response_model=WorkflowResponse,
             status_code=status.HTTP_201_CREATED, summary="Clone a template to a new workflow")
async def clone_template(template_id: str, name: Optional[str] = None) -> WorkflowResponse:
    """
    Clone a built-in template and save it as a new editable workflow.
    """
    template = WorkflowTemplateRegistry.get(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found.",
        )

    import copy
    cloned = copy.deepcopy(template)
    cloned.workflow_id = str(uuid.uuid4())
    cloned.name = name or f"Copy of {template.name}"
    cloned.status = WorkflowStatus.DRAFT

    conn = get_db_connection()
    try:
        _save_workflow_to_db(cloned, conn)
        row = conn.execute("SELECT * FROM workflows WHERE id = ?", (cloned.workflow_id,)).fetchone()
        return _row_to_workflow_response(row)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GET /workflows/schema — get JSON schema
# ---------------------------------------------------------------------------

@router.get("/schema", summary="Get the workflow JSON schema")
async def get_schema() -> Dict[str, Any]:
    """Return the JSON Schema for workflow validation."""
    return get_workflow_json_schema()


# ---------------------------------------------------------------------------
# GET /workflows/node-styles — get node visual styles
# ---------------------------------------------------------------------------

@router.get("/node-styles", summary="Get node visual styles for frontend")
async def get_node_styles_endpoint() -> Dict[str, Any]:
    """Return the visual style definitions for each node type."""
    return get_node_styles()


# ---------------------------------------------------------------------------
# GET /workflows/{id} — get workflow definition
# ---------------------------------------------------------------------------

@router.get("/{workflow_id}", summary="Get a workflow by ID")
async def get_workflow(workflow_id: str) -> Dict[str, Any]:
    """
    Retrieve the full React Flow JSON definition of a workflow.
    """
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow '{workflow_id}' not found.",
            )
        return json.loads(row["workflow_json"])
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# PUT /workflows/{id} — update a workflow
# ---------------------------------------------------------------------------

@router.put("/{workflow_id}", response_model=WorkflowResponse, summary="Update a workflow")
async def update_workflow(workflow_id: str, request: WorkflowUpdateRequest) -> WorkflowResponse:
    """Update an existing workflow's definition."""
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow '{workflow_id}' not found.",
            )

        rf_data = json.loads(row["workflow_json"])

        if request.name is not None:
            rf_data["name"] = request.name
        if request.description is not None:
            rf_data["description"] = request.description
        if request.nodes is not None:
            rf_data["nodes"] = request.nodes
        if request.edges is not None:
            rf_data["edges"] = request.edges
        if request.tags is not None:
            rf_data["tags"] = request.tags

        graph = ReactFlowConverter.react_flow_to_graph(rf_data)
        graph.created_at = row["created_at"]
        if request.status:
            graph.status = WorkflowStatus(request.status)

        _save_workflow_to_db(graph, conn)
        updated_row = conn.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
        return _row_to_workflow_response(updated_row)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# DELETE /workflows/{id} — delete a workflow
# ---------------------------------------------------------------------------

@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete a workflow")
async def delete_workflow(workflow_id: str) -> None:
    """Delete a workflow from the database."""
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT id FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow '{workflow_id}' not found.",
            )
        conn.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
        conn.execute("DELETE FROM workflow_executions WHERE workflow_id = ?", (workflow_id,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# POST /workflows/{id}/run — execute a workflow
# ---------------------------------------------------------------------------

@router.post("/{workflow_id}/run", response_model=WorkflowExecutionResponse,
             summary="Execute a workflow")
async def run_workflow(workflow_id: str, request: WorkflowRunRequest) -> WorkflowExecutionResponse:
    """
    Start a workflow execution.
    Returns an execution ID for status tracking.
    """
    conn = get_db_connection()
    try:
        # Try user workflows first, then templates
        row = conn.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
        if row:
            rf_data = json.loads(row["workflow_json"])
            graph = ReactFlowConverter.react_flow_to_graph(rf_data)
        else:
            template = WorkflowTemplateRegistry.get(workflow_id)
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Workflow '{workflow_id}' not found.",
                )
            graph = template

        # Validate before running
        validation_errors = graph.validate()
        if validation_errors:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "Workflow validation failed",
                    "errors": validation_errors,
                },
            )

        execution_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        topo_order = graph.topological_sort()
        start_node_id = topo_order[0] if topo_order else None

        logs = []
        if request.dry_run:
            logs.append(f"[DRY RUN] Simulating workflow: {graph.name}")
            for nid in topo_order:
                node = graph.nodes[nid]
                logs.append(f"[DRY RUN] Would execute: {node.label} [{node.node_type.value}]")
            exec_status = "completed"
            completed_nodes = topo_order
            completed_at = datetime.utcnow().isoformat()
        else:
            logs.append(f"Starting workflow: {graph.name}")
            logs.append(f"Execution ID: {execution_id}")
            exec_status = "running"
            completed_nodes = []
            completed_at = None

        conn.execute(
            """
            INSERT INTO workflow_executions
            (id, workflow_id, status, current_node_id, completed_nodes, failed_nodes,
             variables, error_message, started_at, completed_at, logs)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                execution_id, workflow_id, exec_status, start_node_id,
                json.dumps(completed_nodes), json.dumps([]),
                json.dumps(request.variables), "",
                now, completed_at, json.dumps(logs),
            ),
        )
        conn.commit()

        return WorkflowExecutionResponse(
            execution_id=execution_id,
            workflow_id=workflow_id,
            status=exec_status,
            current_node_id=start_node_id,
            completed_nodes=completed_nodes,
            failed_nodes=[],
            variables=request.variables,
            error_message="",
            started_at=now,
            completed_at=completed_at,
            logs=logs,
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GET /workflows/{id}/status — execution status
# ---------------------------------------------------------------------------

@router.get("/{workflow_id}/status", summary="Get workflow execution status")
async def get_workflow_status(workflow_id: str) -> List[WorkflowExecutionResponse]:
    """
    Get all execution records for a workflow, most recent first.
    """
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM workflow_executions WHERE workflow_id = ? ORDER BY started_at DESC LIMIT 20",
            (workflow_id,),
        ).fetchall()

        results = []
        for row in rows:
            results.append(WorkflowExecutionResponse(
                execution_id=row["id"],
                workflow_id=row["workflow_id"],
                status=row["status"],
                current_node_id=row["current_node_id"],
                completed_nodes=json.loads(row["completed_nodes"]),
                failed_nodes=json.loads(row["failed_nodes"]),
                variables=json.loads(row["variables"]),
                error_message=row["error_message"],
                started_at=row["started_at"],
                completed_at=row["completed_at"],
                logs=json.loads(row["logs"]),
            ))
        return results
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GET /workflows/{id}/validate — validate workflow
# ---------------------------------------------------------------------------

@router.get("/{workflow_id}/validate", response_model=WorkflowValidationResponse,
            summary="Validate a workflow")
async def validate_workflow(workflow_id: str) -> WorkflowValidationResponse:
    """
    Validate a workflow and return any errors or warnings.
    """
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
        if not row:
            template = WorkflowTemplateRegistry.get(workflow_id)
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Workflow '{workflow_id}' not found.",
                )
            graph = template
        else:
            rf_data = json.loads(row["workflow_json"])
            graph = ReactFlowConverter.react_flow_to_graph(rf_data)

        errors = graph.validate()
        stats = graph.get_statistics()

        warnings = []
        if stats["total_nodes"] > 50:
            warnings.append("Workflow has many nodes (>50) — consider splitting into sub-workflows.")
        if stats["total_nodes"] < 3:
            warnings.append("Workflow has very few nodes — ensure it is complete.")

        return WorkflowValidationResponse(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            statistics=stats,
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GET /workflows/{id}/export/python — export as Python code
# ---------------------------------------------------------------------------

@router.get("/{workflow_id}/export/python", summary="Export workflow as Python code")
async def export_workflow_python(workflow_id: str):
    """Export the workflow as runnable Python code."""
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
        if not row:
            template = WorkflowTemplateRegistry.get(workflow_id)
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Workflow '{workflow_id}' not found.",
                )
            graph = template
        else:
            rf_data = json.loads(row["workflow_json"])
            graph = ReactFlowConverter.react_flow_to_graph(rf_data)

        python_code = WorkflowCodeGenerator.generate(graph)
        return JSONResponse(
            content={"workflow_id": workflow_id, "code": python_code},
            headers={"Content-Disposition": f'attachment; filename="{graph.name}.py"'},
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GET /workflows/{id}/export/json — export as React Flow JSON
# ---------------------------------------------------------------------------

@router.get("/{workflow_id}/export/json", summary="Export workflow as React Flow JSON")
async def export_workflow_json(workflow_id: str):
    """Export the workflow as React Flow compatible JSON."""
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
        if not row:
            template = WorkflowTemplateRegistry.get(workflow_id)
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Workflow '{workflow_id}' not found.",
                )
            graph = template
        else:
            rf_data = json.loads(row["workflow_json"])
            graph = ReactFlowConverter.react_flow_to_graph(rf_data)

        return JSONResponse(
            content=ReactFlowConverter.graph_to_react_flow(graph),
            headers={"Content-Disposition": f'attachment; filename="{graph.name}.json"'},
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GET /workflows/executions/{execution_id} — get specific execution
# ---------------------------------------------------------------------------

@router.get("/executions/{execution_id}", response_model=WorkflowExecutionResponse,
            summary="Get a specific workflow execution")
async def get_execution(execution_id: str) -> WorkflowExecutionResponse:
    """Get details of a specific workflow execution by execution ID."""
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT * FROM workflow_executions WHERE id = ?", (execution_id,)
        ).fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution '{execution_id}' not found.",
            )
        return WorkflowExecutionResponse(
            execution_id=row["id"],
            workflow_id=row["workflow_id"],
            status=row["status"],
            current_node_id=row["current_node_id"],
            completed_nodes=json.loads(row["completed_nodes"]),
            failed_nodes=json.loads(row["failed_nodes"]),
            variables=json.loads(row["variables"]),
            error_message=row["error_message"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            logs=json.loads(row["logs"]),
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# WebSocket /workflows/tui — web terminal
# ---------------------------------------------------------------------------

@router.websocket("/tui")
async def workflow_tui(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for the web-based terminal UI.
    Provides xterm.js-compatible terminal with full ANSI color support.
    """
    try:
        await tui_handler.handle(websocket)
    except WebSocketDisconnect:
        logger.info("TUI WebSocket disconnected")
    except Exception as exc:
        logger.exception(f"TUI WebSocket error: {exc}")


# ---------------------------------------------------------------------------
# Module initialization
# ---------------------------------------------------------------------------

def create_workflow_router() -> APIRouter:
    """Create and configure the workflow API router."""
    init_db()
    return router
