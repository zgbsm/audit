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

from jsonschema import Draft7Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7
from mcp.server import Server
from mcp.types import CallToolResult, TextContent, Tool

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Per-stage result store
# ---------------------------------------------------------------------------
# Key: stage name (e.g. "hunt", "validate").  Populated by the MCP tool
# handler and consumed by the runner via get_result().
_results_store: dict[str, dict[str, Any]] = {}

# Cache for compiled JSON Schema validators (built once per stage).
_validators: dict[str, Draft7Validator] = {}


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
        "Submit reconnaissance results. You MUST call this exactly once "
        "at the end of your analysis. Required arguments: 'subsystems' "
        "(array of module objects with name/path/language/purpose), "
        "'architecture' (object with build_commands, entry_points, "
        "trust_boundaries), 'initial_tasks' (array of hunt task objects "
        "each with task_id/attack_class/scope_hint/target_files/rationale/"
        "priority). If the call fails, read the error message carefully — "
        "it tells you exactly which field is missing or invalid — then "
        "fix and retry."
    ),
    "hunt": (
        "Submit vulnerability hunting results for one task. Call this "
        "exactly once per task at the end. Required: 'findings' (array "
        "of finding objects, each with finding_id/file/line_start/"
        "line_end/vuln_class/severity/description/evidence_snippet) and "
        "'gaps_observed' (array of areas the hunter couldn't fully cover). "
        "If the call fails, check which field you missed and retry."
    ),
    "validate": (
        "Submit a validation verdict for one finding. Call this exactly "
        "once per finding. Required: 'finding_id', 'verdict' (one of "
        "confirmed/rejected/needs_more_info), 'rationale', "
        "'validator_confidence' (0.0-1.0). If the call fails, check "
        "the error and retry with the correct fields."
    ),
    "gapfill": (
        "Submit gap-fill hunt tasks. Call this exactly once. Required: "
        "'new_tasks' (array of hunt task objects with task_id/attack_class/"
        "scope_hint/target_files/rationale/priority), 'coverage_analysis' "
        "(object with light_subsystems and unattempted_attack_classes). "
        "If the call fails, fix the missing fields and retry."
    ),
    "dedupe": (
        "Submit deduplication groups. Call this exactly once. Required: "
        "'groups' (array of group objects, each with group_id/root_cause/"
        "canonical_finding_id/member_finding_ids). If the call fails, "
        "check the error and retry."
    ),
    "trace": (
        "Submit a reachability trace for one canonical finding. Call "
        "this exactly once per finding. Required: 'finding_id', "
        "'reachable' (boolean), 'confidence' (0.0-1.0), 'rationale', "
        "'entry_points' (array), 'call_chain' (array). If the call "
        "fails, check which field is wrong and retry."
    ),
    "feedback": (
        "Submit feedback-driven hunt tasks. Call this exactly once. "
        "Required: 'new_hunt_tasks' (array of hunt task objects), "
        "'rationale_per_task' (object mapping task_id → rationale). "
        "If the call fails, fix and retry."
    ),
    "report": (
        "Submit the final vulnerability report. Call this exactly once. "
        "Required: 'findings' (array), 'summary' (object with counts "
        "by severity). If the call fails, check the error and retry."
    ),
    "merge": (
        "Submit the consolidated task list after merging. Call this "
        "exactly once. Required: 'merged_tasks' (array of hunt task "
        "objects), 'merge_notes' (array of merge records with "
        "original_task_ids/merged_into/rationale). If the call fails, "
        "check the error and retry."
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

    All ``$ref`` references are inlined recursively so the MCP server /
    Claude CLI never has to resolve external schema files at runtime.
    """
    schema_name = _STAGE_SCHEMA_FILES[stage]
    schema_path = _SCHEMAS_DIR / f"{schema_name}.schema.json"
    raw = json.loads(schema_path.read_text(encoding="utf-8"))
    raw = _inline_refs(raw)
    # MCP tools need a top-level "object" type schema.
    if raw.get("type") != "object":
        raw = {"type": "object", "properties": {"result": raw}}
    # Ensure title and description are present (the CLI uses them for the
    # tool description in the model's context).
    raw.setdefault("title", f"{stage}_output")
    raw.setdefault("description", f"Structured output for the {stage} stage.")
    return raw


def _inline_refs(schema: Any, _seen: frozenset[str] | None = None) -> Any:
    """Recursively replace ``{"$ref": "<file>"}`` with the inlined file contents."""
    if _seen is None:
        _seen = frozenset()
    if isinstance(schema, dict):
        if "$ref" in schema and len(schema) == 1:
            ref = schema["$ref"]
            if ref in _seen:
                raise ValueError(f"Circular $ref detected: {ref}")
            ref_path = _SCHEMAS_DIR / ref
            if ref_path.exists():
                loaded = json.loads(ref_path.read_text(encoding="utf-8"))
                return _inline_refs(loaded, _seen | {ref})
            # If the file doesn't exist, leave the $ref as-is (best-effort).
        return {k: _inline_refs(v, _seen) for k, v in schema.items()}
    if isinstance(schema, list):
        return [_inline_refs(item, _seen) for item in schema]
    return schema


# ---------------------------------------------------------------------------
# MCP server factory
# ---------------------------------------------------------------------------

def create_submit_tool_server(stage: str) -> dict[str, Any]:
    """Create an MCP server config for the given *stage*.

    Returns a dict suitable for ``ClaudeAgentOptions.mcp_servers``::

        {"submit-harness": {"type": "sdk", "name": "submit-harness",
                            "instance": <mcp.server.Server>}}

    The tool's ``call_tool`` handler performs server-side validation
    with LLM-friendly error messages before accepting the result.
    """
    tool_name = tool_name_for_stage(stage)
    tool_desc = _tool_description_for_stage(stage)
    input_schema = load_tool_input_schema(stage)

    # Pre-compile a jsonschema validator for server-side validation.
    validator = _build_validator(stage, input_schema)

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
        # ---- Server-side validation ----
        # Even though Claude Code validates client-side, this catches
        # edge cases and returns friendlier error messages the LLM can
        # act on immediately.
        if validator is not None:
            errors = sorted(validator.iter_errors(arguments), key=lambda e: e.path)
            if errors:
                lines: list[str] = []
                for err in errors[:12]:  # cap at 12 — avoid overwhelming
                    path = (
                        "/".join(str(p) for p in err.absolute_path)
                        if err.absolute_path
                        else "<root>"
                    )
                    msg = _friendly_validation_message(err, path)
                    lines.append(f"  • {msg}")
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=(
                                f"❌ Your call to {name} was rejected because "
                                f"{len(errors)} field(s) are wrong:\n\n"
                                + "\n".join(lines)
                                + f"\n\n👉 Fix these issues and call {name} again "
                                f"with the corrected arguments."
                            ),
                        )
                    ],
                    isError=True,
                )

        # ---- Success ----
        _results_store[stage] = arguments
        log.debug("submit tool %r called for stage %r — result stored", name, stage)
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=(
                        f"✅ {name} succeeded. The {stage} results have been "
                        f"received by the pipeline. Your work on this stage is "
                        f"done — do NOT call this tool again."
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


def _build_validator(
    stage: str, input_schema: dict[str, Any]
) -> Draft7Validator | None:
    """Pre-compile a jsonschema validator with $ref resolution."""
    if stage in _validators:
        return _validators[stage]
    try:
        registry: Registry = Registry()
        for sf in _SCHEMAS_DIR.glob("*.schema.json"):
            raw = json.loads(sf.read_text(encoding="utf-8"))
            registry = registry.with_resource(
                sf.name, Resource.from_contents(raw, default_specification=DRAFT7)
            )
        v = Draft7Validator(input_schema, registry=registry)
        _validators[stage] = v
        return v
    except Exception:
        log.warning(
            "Failed to compile validator for stage %r — "
            "server-side validation disabled for this stage",
            stage, exc_info=True,
        )
        _validators[stage] = None  # type: ignore[assignment]
        return None


def _friendly_validation_message(err: Any, path: str) -> str:
    """Turn a jsonschema ValidationError into a one-line LLM-friendly message."""
    # Map common jsonschema error messages to clearer phrasing.
    msg = err.message
    replacements = {
        "is a required property": f"is required but missing — add '{path}' to your arguments",
        "is not of type": "has the wrong type",
    }
    for old, new in replacements.items():
        if old in msg:
            msg = new
            break

    # Include the actual value if it helps (but keep it short).
    instance = err.instance
    if instance is not None and not isinstance(instance, (dict, list)):
        instance_str = str(instance)
        if len(instance_str) <= 60:
            return f"[{path}] {msg} (got: {instance_str!r})"

    return f"[{path}] {msg}"
