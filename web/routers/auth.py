"""Auth router — POST /api/auth/check."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from audit.auth import AuthError, configure_auth

from web.schemas import AuthCheckRequest, AuthCheckResponse

router = APIRouter()


@router.post("/auth/check", response_model=AuthCheckResponse)
async def auth_check(req: AuthCheckRequest):
    """Verify Claude Code auth is configured correctly."""
    try:
        status = configure_auth(allow_api_key=req.allow_api_key)
    except AuthError as e:
        return AuthCheckResponse(
            auth_mode="none",
            api_key_scrubbed=False,
            auth_token_scrubbed=False,
            ok=False,
            error=str(e),
        )

    return AuthCheckResponse(
        auth_mode=status.auth_mode,
        api_key_scrubbed=status.api_key_scrubbed,
        auth_token_scrubbed=status.auth_token_scrubbed,
        claude_cli_path=status.claude_cli_path,
        claude_cli_version=status.claude_cli_version,
        credentials_file=str(status.credentials_file) if status.credentials_file else None,
        gateway_base_url=status.gateway_base_url,
        gateway_model=status.gateway_model,
        ok=True,
    )
