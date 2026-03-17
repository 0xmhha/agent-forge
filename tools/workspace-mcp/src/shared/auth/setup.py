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
from shared.batch.config import load_batch_config, update_watcher_config
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

    batch_config = load_batch_config()
    batch_html = _render_batch_settings(batch_config)

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
        .section-title {{
            font-size: 18px;
            font-weight: 600;
            color: #f0f6fc;
            margin: 32px 0 16px;
        }}
        .watcher-row {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 0;
            border-bottom: 1px solid #21262d;
        }}
        .watcher-name {{
            flex: 1;
            font-size: 14px;
            color: #c9d1d9;
        }}
        .watcher-interval {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 13px;
            color: #8b949e;
        }}
        .watcher-interval input {{
            width: 60px;
            padding: 4px 8px;
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 4px;
            color: #c9d1d9;
            font-size: 13px;
            text-align: center;
        }}
        .toggle {{
            position: relative;
            width: 40px;
            height: 22px;
        }}
        .toggle input {{
            opacity: 0;
            width: 0;
            height: 0;
        }}
        .toggle-slider {{
            position: absolute;
            cursor: pointer;
            top: 0; left: 0; right: 0; bottom: 0;
            background: #30363d;
            border-radius: 11px;
            transition: 0.2s;
        }}
        .toggle-slider:before {{
            content: "";
            position: absolute;
            height: 16px;
            width: 16px;
            left: 3px;
            bottom: 3px;
            background: #c9d1d9;
            border-radius: 50%;
            transition: 0.2s;
        }}
        .toggle input:checked + .toggle-slider {{
            background: #238636;
        }}
        .toggle input:checked + .toggle-slider:before {{
            transform: translateX(18px);
        }}
        .btn-save {{
            background: #1f6feb;
            color: #fff;
            border: none;
            margin-top: 12px;
        }}
        .btn-save:hover {{ background: #388bfd; }}
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
        {batch_html}
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


_WATCHER_LABELS = {
    "github_review": {"name": "GitHub Review Requests", "icon": "👀"},
}


def _render_batch_settings(batch_config) -> str:
    """Render the batch watcher settings section."""
    rows = ""
    for watcher_name, watcher_cfg in batch_config.watchers.items():
        label = _WATCHER_LABELS.get(watcher_name, {"name": watcher_name, "icon": "⚙️"})
        checked = "checked" if watcher_cfg.enabled else ""
        rows += f"""
        <div class="watcher-row">
            <span>{label['icon']}</span>
            <span class="watcher-name">{label['name']}</span>
            <div class="watcher-interval">
                <input type="number" id="interval-{watcher_name}"
                       value="{watcher_cfg.interval_minutes}" min="1" max="60">
                <span>분</span>
            </div>
            <label class="toggle">
                <input type="checkbox" id="enabled-{watcher_name}" {checked}
                       onchange="saveWatcher('{watcher_name}')">
                <span class="toggle-slider"></span>
            </label>
        </div>"""

    return f"""
    <h2 class="section-title">Batch Watchers</h2>
    <div class="service-card">
        {rows}
        <script>
        async function saveWatcher(name) {{
            const enabled = document.getElementById('enabled-' + name).checked;
            const interval = document.getElementById('interval-' + name).value;
            const params = new URLSearchParams({{
                enabled: enabled, interval: interval
            }});
            const resp = await fetch('/batch/' + name + '?' + params);
            if (resp.redirected) window.location = resp.url;
        }}
        // Save on interval change (debounced)
        document.querySelectorAll('.watcher-interval input').forEach(input => {{
            let timer;
            input.addEventListener('change', () => {{
                clearTimeout(timer);
                timer = setTimeout(() => {{
                    const name = input.id.replace('interval-', '');
                    saveWatcher(name);
                }}, 500);
            }});
        }});
        </script>
    </div>"""


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

    @app.get("/batch/{watcher_name}")
    async def update_batch(watcher_name: str, request: Request):
        enabled = request.query_params.get("enabled", "true") == "true"
        interval = int(request.query_params.get("interval", "10"))
        interval = max(1, min(60, interval))

        update_watcher_config(watcher_name, enabled=enabled, interval_minutes=interval)
        label = _WATCHER_LABELS.get(watcher_name, {}).get("name", watcher_name)
        status = "활성화" if enabled else "비활성화"
        return RedirectResponse(f"/?message={label}: {status}, {interval}분 간격")

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
