"""Auth setup web UI — local server for managing OAuth connections.

Run directly:
    python -m shared.auth.setup
    # Opens http://localhost:8919 in browser

Provides a simple UI to:
  - View connection status for each service (Gmail, GitHub)
  - Initiate OAuth flows via browser
  - Disconnect (delete stored tokens)
"""

import asyncio
import logging
import time
import webbrowser
from contextlib import asynccontextmanager
from urllib.parse import urlencode

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from shared.auth.credentials import load_config
from shared.auth.token_store import StoredToken, TokenStore
from shared.types import AuthConfig, ToolSource

logger = logging.getLogger(__name__)

OAUTH_ENDPOINTS: dict[str, dict[str, str]] = {
    ToolSource.GMAIL: {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
    },
    ToolSource.GITHUB: {
        "auth_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
    },
}

SERVICE_LABELS: dict[str, dict[str, str]] = {
    ToolSource.GMAIL: {"name": "Gmail", "icon": "📧", "color": "#EA4335"},
    ToolSource.GITHUB: {"name": "GitHub", "icon": "🐙", "color": "#24292e"},
}


def _build_token_store() -> TokenStore:
    return TokenStore()


def _get_service_status(store: TokenStore, service: str) -> dict:
    """Check connection status for a service."""
    token = store.load(service)
    if token is None:
        return {"connected": False, "expired": False}

    expired = token.expires_at > 0 and time.time() > token.expires_at
    return {
        "connected": True,
        "expired": expired,
        "scopes": token.scopes,
        "expires_at": token.expires_at,
    }


def _render_page(store: TokenStore, message: str = "") -> str:
    """Render the setup UI HTML page."""
    services_html = ""
    for service_key in [ToolSource.GMAIL, ToolSource.GITHUB]:
        label = SERVICE_LABELS[service_key]
        status = _get_service_status(store, service_key)
        config = load_config(ToolSource(service_key))
        has_credentials = bool(config.client_id)

        if status["connected"] and not status["expired"]:
            status_badge = '<span class="badge connected">연결됨</span>'
            action = (
                f'<a href="/disconnect/{service_key}" class="btn btn-disconnect">'
                f'연결 해제</a>'
            )
        elif status["connected"] and status["expired"]:
            status_badge = '<span class="badge expired">만료됨</span>'
            action = (
                f'<a href="/connect/{service_key}" class="btn btn-connect">'
                f'재연결</a>'
                f'<a href="/disconnect/{service_key}" class="btn btn-disconnect">'
                f'해제</a>'
            )
        elif not has_credentials:
            status_badge = '<span class="badge no-creds">자격증명 없음</span>'
            action = '<span class="hint">환경변수를 설정하세요</span>'
        else:
            status_badge = '<span class="badge disconnected">미연결</span>'
            action = (
                f'<a href="/connect/{service_key}" class="btn btn-connect">'
                f'연결하기</a>'
            )

        env_hint = _get_env_hint(service_key, has_credentials)

        services_html += f"""
        <div class="service-card">
            <div class="service-header">
                <span class="service-icon">{label['icon']}</span>
                <span class="service-name">{label['name']}</span>
                {status_badge}
            </div>
            <div class="service-actions">{action}</div>
            {env_hint}
        </div>
        """

    message_html = f'<div class="message">{message}</div>' if message else ""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>agent-forge: Service Setup</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        .container {{
            width: 480px;
            padding: 40px;
        }}
        h1 {{
            font-size: 24px;
            font-weight: 600;
            color: #f0f6fc;
            margin-bottom: 8px;
        }}
        .subtitle {{
            font-size: 14px;
            color: #8b949e;
            margin-bottom: 32px;
        }}
        .message {{
            background: #1c2333;
            border: 1px solid #388bfd;
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 24px;
            font-size: 14px;
            color: #a5d6ff;
        }}
        .service-card {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
        }}
        .service-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 12px;
        }}
        .service-icon {{ font-size: 24px; }}
        .service-name {{
            font-size: 18px;
            font-weight: 600;
            color: #f0f6fc;
            flex: 1;
        }}
        .badge {{
            font-size: 12px;
            padding: 4px 10px;
            border-radius: 12px;
            font-weight: 500;
        }}
        .badge.connected {{ background: #238636; color: #fff; }}
        .badge.disconnected {{ background: #30363d; color: #8b949e; }}
        .badge.expired {{ background: #9e6a03; color: #fff; }}
        .badge.no-creds {{ background: #da3633; color: #fff; }}
        .service-actions {{
            display: flex;
            gap: 8px;
        }}
        .btn {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            text-decoration: none;
            cursor: pointer;
            transition: background 0.15s;
        }}
        .btn-connect {{
            background: #238636;
            color: #fff;
        }}
        .btn-connect:hover {{ background: #2ea043; }}
        .btn-disconnect {{
            background: #21262d;
            color: #f85149;
            border: 1px solid #f8514933;
        }}
        .btn-disconnect:hover {{ background: #30363d; }}
        .hint {{
            font-size: 13px;
            color: #8b949e;
        }}
        .env-hint {{
            margin-top: 12px;
            padding: 10px 12px;
            background: #0d1117;
            border-radius: 6px;
            font-size: 12px;
            font-family: 'SF Mono', 'Fira Code', monospace;
            color: #8b949e;
            line-height: 1.6;
        }}
        .env-hint .set {{ color: #7ee787; }}
        .env-hint .unset {{ color: #f85149; }}
        .footer {{
            margin-top: 32px;
            text-align: center;
            font-size: 12px;
            color: #484f58;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>agent-forge</h1>
        <p class="subtitle">Service Connection Setup</p>
        {message_html}
        {services_html}
        <div class="footer">토큰은 로컬에 암호화되어 저장됩니다 (~/.agent-forge/tokens/)</div>
    </div>
</body>
</html>"""


def _get_env_hint(service: str, has_credentials: bool) -> str:
    """Generate environment variable hint for a service."""
    if has_credentials:
        return ""

    if service == ToolSource.GMAIL:
        return """
        <div class="env-hint">
            필요한 환경변수:<br>
            <span class="unset">GMAIL_CLIENT_ID</span> — Google Cloud Console에서 생성<br>
            <span class="unset">GMAIL_CLIENT_SECRET</span> — OAuth 2.0 클라이언트 시크릿
        </div>"""
    elif service == ToolSource.GITHUB:
        return """
        <div class="env-hint">
            필요한 환경변수 (택 1):<br>
            <span class="unset">GITHUB_TOKEN</span> — Personal Access Token<br>
            또는 OAuth:<br>
            <span class="unset">GITHUB_CLIENT_ID</span> / <span class="unset">GITHUB_CLIENT_SECRET</span>
        </div>"""
    return ""


def _build_auth_url(config: AuthConfig, service: str, redirect_uri: str) -> str:
    """Build the OAuth authorization URL."""
    endpoints = OAUTH_ENDPOINTS[service]
    params = {
        "client_id": config.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(config.scopes),
    }
    if service == ToolSource.GMAIL:
        params["access_type"] = "offline"
        params["prompt"] = "consent"
    return f"{endpoints['auth_url']}?{urlencode(params)}"


async def _exchange_code(
    config: AuthConfig, service: str, code: str, redirect_uri: str
) -> StoredToken:
    """Exchange authorization code for tokens."""
    import httpx

    endpoints = OAUTH_ENDPOINTS[service]
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": config.client_id,
        "client_secret": config.client_secret.get_secret_value(),
    }
    headers = {}
    if service == ToolSource.GITHUB:
        headers["Accept"] = "application/json"

    async with httpx.AsyncClient() as client:
        response = await client.post(endpoints["token_url"], data=data, headers=headers)
        response.raise_for_status()
        result = response.json()

    expires_in = result.get("expires_in", 0)
    return StoredToken(
        access_token=result["access_token"],
        refresh_token=result.get("refresh_token", ""),
        token_type=result.get("token_type", "Bearer"),
        expires_at=int(time.time()) + expires_in if expires_in else 0,
        scopes=config.scopes,
    )


def create_app() -> FastAPI:
    """Create the setup FastAPI application."""
    store = _build_token_store()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield

    app = FastAPI(title="agent-forge setup", lifespan=lifespan)

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        message = request.query_params.get("message", "")
        return HTMLResponse(_render_page(store, message))

    @app.get("/connect/{service}")
    async def connect(service: str, request: Request):
        try:
            config = load_config(ToolSource(service))
        except ValueError:
            return RedirectResponse(f"/?message=알 수 없는 서비스: {service}")

        if not config.client_id:
            return RedirectResponse(f"/?message=환경변수가 설정되지 않았습니다 ({service})")

        redirect_uri = str(request.base_url) + f"callback/{service}"
        auth_url = _build_auth_url(config, service, redirect_uri)
        return RedirectResponse(auth_url)

    @app.get("/callback/{service}")
    async def callback(service: str, request: Request):
        error = request.query_params.get("error")
        if error:
            desc = request.query_params.get("error_description", "Authorization denied")
            return RedirectResponse(f"/?message=인증 실패: {desc}")

        code = request.query_params.get("code")
        if not code:
            return RedirectResponse("/?message=인증 코드가 없습니다")

        try:
            config = load_config(ToolSource(service))
            redirect_uri = str(request.base_url) + f"callback/{service}"
            token = await _exchange_code(config, service, code, redirect_uri)
            store.save(service, token)
            label = SERVICE_LABELS.get(service, {}).get("name", service)
            return RedirectResponse(f"/?message={label} 연결 완료!")
        except Exception as e:
            logger.exception("Token exchange failed for %s", service)
            return RedirectResponse(f"/?message=토큰 교환 실패: {e}")

    @app.get("/disconnect/{service}")
    async def disconnect(service: str):
        store.delete(service)
        label = SERVICE_LABELS.get(service, {}).get("name", service)
        return RedirectResponse(f"/?message={label} 연결이 해제되었습니다")

    return app


def main() -> None:
    """Launch the setup UI server and open browser."""
    from dotenv import load_dotenv
    load_dotenv()

    port = 8919
    print(f"[agent-forge] Setup UI: http://localhost:{port}")
    webbrowser.open(f"http://localhost:{port}")
    uvicorn.run(create_app(), host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
