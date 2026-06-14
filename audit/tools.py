"""MCP tools for submitting stage results via structured tool calls.

Each stage gets one ``submit_<stage>_result`` tool.  When the LLM calls
the tool the arguments are saved into a module-level store; the runner
reads them after the session and populates ``AgentResult.payload`` from
them.  If the LLM does not call the tool (e.g. old prompt), the runner
falls back to JSON extraction from the final text.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.types import CallToolResult, TextContent, Tool

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Per-stage result store
# ---------------------------------------------------------------------------
# Key: stage name (e.g. "hunt", "validate").  Populated by the MCP tool
# handler and consumed by the runner via get_result().
_results_store: dict[str, dict[str, Any]] = {}


def get_result(stage: str) -> dict[str, Any] | None:
    """Return (and remove) the result submitted for *stage*, or None."""
    return _results_store.pop(stage, None)


# ---------------------------------------------------------------------------
# Tool-name / tool-description per stage
# ---------------------------------------------------------------------------

_STAGE_TOOL_NAMES: dict[str, str] = {
    "recon":    "submit_recon_result",
    "hunt":     "submit_hunt_result",
    "validate": "submit_validation_result",
    "gapfill":  "submit_gapfill_result",
    "dedupe":   "submit_dedupe_result",
    "trace":    "submit_trace_result",
    "feedback": "submit_feedback_result",
    "report":   "submit_report_result",
    "merge":    "submit_merge_result",
}

_STAGE_TOOL_DESCRIPTIONS: dict[str, str] = {
    "recon": (
        "Submit the reconnaissance results for the codebase audit pipeline. "
        "Call this tool exactly once at the end of your analysis with the "
        "complete output: subsystems, architecture, and initial_tasks."
    ),
    "hunt": (
        "Submit vulnerability hunting results for a single attack-class task. "
        "Call this tool exactly once at the end with your findings and any "
        "gaps_observed."
    ),
    "validate": (
        "Submit the validation verdict for a single finding. "
        "Call this tool exactly once after adversarial review with your "
        "verdict, rationale, and confidence."
    ),
    "gapfill": (
        "Submit new gap-fill hunt tasks to cover under-explored areas. "
        "Call this tool exactly once with new_tasks and coverage_analysis."
    ),
    "dedupe": (
        "Submit deduplication groups for confirmed findings. "
        "Call this tool exactly once with the group assignments."
    ),
    "trace": (
        "Submit the reachability trace for a single canonical finding. "
        "Call this tool exactly once with entry_points, call_chain, and "
        "reachability verdict."
    ),
    "feedback": (
        "Submit new feedback-driven hunt tasks based on sibling patterns. "
        "Call this tool exactly once with new_hunt_tasks and rationale_per_task."
    ),
    "report": (
        "Submit the final vulnerability report. "
        "Call this tool exactly once with findings and summary."
    ),
    "merge": (
        "Submit the merged (consolidated) task list. "
        "Call this tool exactly once with merged_tasks and merge_notes."
    ),
}


def tool_name_for_stage(stage: str) -> str:
    """Return the tool name for a stage, e.g. ``"submit_hunt_result"``."""
    return _STAGE_TOOL_NAMES[stage]


def _tool_description_for_stage(stage: str) -> str:
    return _STAGE_TOOL_DESCRIPTIONS.get(
        stage, f"Submit results for the {stage} stage."
    )


# ---------------------------------------------------------------------------
# Schema loading
# ---------------------------------------------------------------------------

_SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"

# Map stage name → schema filename (without .schema.json suffix)
_STAGE_SCHEMA_FILES: dict[str, str] = {
    "recon":    "recon_output",
    "hunt":     "finding",
    "validate": "validation",
    "gapfill":  "gapfill_output",
    "dedupe":   "dedupe_output",
    "trace":    "trace",
    "feedback": "feedback_output",
    "report":   "report",
    "merge":    "merge_output",
}


def load_tool_input_schema(stage: str) -> dict[str, Any]:
    """Load the JSON Schema for a stage and adapt it as an MCP tool input schema.

    The stage's output schema (e.g. ``schemas/finding.schema.json``) defines
    what the LLM should produce.  We reuse it directly as the tool's
    ``inputSchema`` so the tool accepts exactly the same shape.
    """
    schema_name = _STAGE_SCHEMA_FILES[stage]
    schema_path = _SCHEMAS_DIR / f"{schema_name}.schema.json"
    raw = json.loads(schema_path.read_text())
    # MCP tools need a top-level "object" type schema.
    if raw.get("type") != "object":
        raw = {"type": "object", "properties": {"result": raw}}
    # Ensure title and description are present (the CLI uses them for the
    # tool description in the model's context).
    raw.setdefault("title", f"{stage}_output")
    raw.setdefault("description", f"Structured output for the {stage} stage.")
    return raw


# ---------------------------------------------------------------------------
# MCP server factory
# ---------------------------------------------------------------------------

def create_submit_tool_server(stage: str) -> dict[str, Any]:
    """Create an MCP server config for the given *stage*.

    Returns a dict suitable for ``ClaudeAgentOptions.mcp_servers``::

        {"submit-harness": {"type": "sdk", "name": "submit-harness",
                            "instance": <mcp.server.Server>}}
    """
    tool_name = tool_name_for_stage(stage)
    tool_desc = _tool_description_for_stage(stage)
    input_schema = load_tool_input_schema(stage)

    server = Server("submit-harness", version="1.0.0")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name=tool_name,
                description=tool_desc,
                inputSchema=input_schema,
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
        _results_store[stage] = arguments
        log.debug("submit tool %r called for stage %r — result stored", name, stage)
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=(
                        f"Results for {stage} submitted successfully. "
                        f"The pipeline will now process your output."
                    ),
                )
            ],
            isError=False,
        )

    return {
        "submit-harness": {
            "type": "sdk",
            "name": "submit-harness",
            "instance": server,
        }
    }
