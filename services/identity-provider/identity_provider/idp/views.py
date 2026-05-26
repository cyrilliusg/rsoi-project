"""
Identity Provider views.

Endpoints:
  - GET  /.well-known/openid-configuration  (discovery)
  - GET  /api/v1/jwks                       (JWKs)
  - GET  /api/v1/authorize                  (start auth code flow)
  - GET  /login + POST /login               (form-based login screen)
  - POST /api/v1/token                      (code -> JWT)
  - GET  /api/v1/userinfo                   (Bearer-protected)
  - GET/POST /api/v1/users                  (admin only)

Public contract: docs/identity-provider.md.
"""
from __future__ import annotations

import logging
from urllib.parse import urlencode, urlparse

from django.conf import settings
from django.contrib.auth import authenticate, login as session_login, logout as session_logout
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status, views
from rest_framework.response import Response

from .auth import IsAdmin, JWTAuthentication
from .jwt_utils import issue_token
from .keys import jwks as build_jwks
from .models import AuthorizationCode, Client
from .pkce import verify_challenge
from .serializers import CreateUserSerializer, UserSerializer

logger = logging.getLogger(__name__)


def _abs(path: str) -> str:
    return settings.IDP_ISSUER.rstrip("/") + path


def discovery(request: HttpRequest) -> JsonResponse:
    return JsonResponse({
        "issuer": settings.IDP_ISSUER,
        "authorization_endpoint": _abs("/api/v1/authorize"),
        "token_endpoint": _abs("/api/v1/token"),
        "userinfo_endpoint": _abs("/api/v1/userinfo"),
        "end_session_endpoint": _abs("/api/v1/logout"),
        "jwks_uri": _abs("/api/v1/jwks"),
        "response_types_supported": ["code"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "scopes_supported": ["openid", "profile", "email"],
        "token_endpoint_auth_methods_supported": ["none"],
        "code_challenge_methods_supported": ["S256", "plain"],
        "grant_types_supported": ["authorization_code"],
    })


def jwks(request: HttpRequest) -> JsonResponse:
    return JsonResponse(build_jwks())


# ---------------------------------------------------------------------------
# Authorization Code Flow
# ---------------------------------------------------------------------------

REQUIRED_AUTHORIZE_PARAMS = ("response_type", "client_id", "redirect_uri", "scope", "state")


def _authorize_redirect_error(redirect_uri: str, state: str, error: str, description: str) -> HttpResponseRedirect:
    qs = urlencode({"error": error, "error_description": description, "state": state})
    return HttpResponseRedirect(f"{redirect_uri}?{qs}")


@csrf_exempt
def authorize(request: HttpRequest) -> HttpResponse:
    """
    GET /api/v1/authorize — start authorization code flow.
    Renders a login form if no session; redirects on success.
    """
    params = request.GET
    missing = [p for p in REQUIRED_AUTHORIZE_PARAMS if not params.get(p)]
    if missing:
        return JsonResponse(
            {"error": "invalid_request", "error_description": f"Missing params: {', '.join(missing)}"},
            status=400,
        )

    response_type = params.get("response_type")
    if response_type != "code":
        return JsonResponse(
            {"error": "unsupported_response_type", "error_description": "Only 'code' is supported"},
            status=400,
        )

    client_id = params["client_id"]
    redirect_uri = params["redirect_uri"]
    scope = params["scope"]
    state = params["state"]
    code_challenge = params.get("code_challenge", "")
    code_challenge_method = params.get("code_challenge_method", "")

    try:
        client = Client.objects.get(client_id=client_id)
    except Client.DoesNotExist:
        return JsonResponse(
            {"error": "invalid_client", "error_description": "Unknown client_id"},
            status=400,
        )

    if not client.redirect_uri_allowed(redirect_uri):
        # By spec we MUST NOT redirect to an unregistered URI.
        return JsonResponse(
            {"error": "invalid_request", "error_description": "redirect_uri not registered"},
            status=400,
        )

    if client.is_public and (not code_challenge or code_challenge_method not in ("S256", "plain")):
        return _authorize_redirect_error(
            redirect_uri, state, "invalid_request",
            "code_challenge with method S256 or plain is required for public clients",
        )

    if not request.user.is_authenticated:
        # Bounce through login. The original query string contains `&`, so we
        # MUST urlencode it — otherwise the browser parses `/login?next=...&`
        # as multiple query params and `next` only sees the first segment.
        next_url = request.get_full_path()
        login_url = "/login?" + urlencode({"next": next_url})
        return HttpResponseRedirect(login_url)

    # Issue authorization code, redirect.
    ac = AuthorizationCode.issue(
        user=request.user,
        client=client,
        redirect_uri=redirect_uri,
        scope=scope,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
    )
    qs = urlencode({"code": ac.code, "state": state})
    return HttpResponseRedirect(f"{redirect_uri}?{qs}")


def login_view(request: HttpRequest) -> HttpResponse:
    """
    Minimal browser-facing login screen used as the IdP authentication step
    inside the authorization code flow.
    """
    error = None
    next_url = request.GET.get("next") or request.POST.get("next") or "/"

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is None:
            error = "Неверный логин или пароль"
        else:
            session_login(request, user)
            return HttpResponseRedirect(next_url)

    return render(request, "idp/login.html", {"next": next_url, "error": error})


def _post_logout_uri_allowed(uri: str) -> bool:
    """A URI is allowed if its scheme+host+port matches one of the
    redirect_uris of *any* registered client. Lightweight check that
    avoids us needing a separate `post_logout_redirect_uris` column."""
    try:
        candidate = urlparse(uri)
    except Exception:
        return False
    if not candidate.scheme or not candidate.netloc:
        return False
    candidate_origin = f"{candidate.scheme}://{candidate.netloc}"
    for client in Client.objects.all():
        for registered in (client.redirect_uris or []):
            try:
                p = urlparse(registered)
            except Exception:
                continue
            if not p.scheme or not p.netloc:
                continue
            if f"{p.scheme}://{p.netloc}" == candidate_origin:
                return True
    return False


@csrf_exempt
def logout_view(request: HttpRequest) -> HttpResponse:
    """
    GET /api/v1/logout — RP-Initiated Logout.

    Always tears down the IdP session cookie (idempotent — works even if
    no session). When `post_logout_redirect_uri` is supplied AND its
    origin matches a registered client redirect_uri, we 302 the browser
    back to that URI (optionally preserving `state`).

    Anonymous calls return 204 with the session cookie cleared.
    """
    post_logout = request.GET.get("post_logout_redirect_uri", "").strip()
    state = request.GET.get("state", "")

    session_logout(request)

    if post_logout:
        if not _post_logout_uri_allowed(post_logout):
            return JsonResponse(
                {"error": "invalid_request", "error_description": "post_logout_redirect_uri not allowed"},
                status=400,
            )
        target = post_logout
        if state:
            sep = "&" if "?" in target else "?"
            target = f"{target}{sep}{urlencode({'state': state})}"
        return HttpResponseRedirect(target)

    return JsonResponse({"status": "logged_out"})


@csrf_exempt
def token(request: HttpRequest) -> JsonResponse:
    """
    POST /api/v1/token — exchange authorization_code for JWT.
    Body: application/x-www-form-urlencoded or application/json.
    """
    if request.method != "POST":
        return JsonResponse({"error": "invalid_request", "error_description": "POST only"}, status=405)

    if request.content_type == "application/json":
        try:
            import json
            data = json.loads(request.body or b"{}")
        except Exception:
            return JsonResponse({"error": "invalid_request"}, status=400)
    else:
        data = request.POST

    grant_type = data.get("grant_type")
    if grant_type != "authorization_code":
        return JsonResponse(
            {"error": "unsupported_grant_type", "error_description": "Only authorization_code is supported"},
            status=400,
        )

    code_str = data.get("code") or ""
    redirect_uri = data.get("redirect_uri") or ""
    client_id = data.get("client_id") or ""
    code_verifier = data.get("code_verifier") or ""

    try:
        ac = AuthorizationCode.objects.select_related("client", "user").get(code=code_str)
    except AuthorizationCode.DoesNotExist:
        return JsonResponse({"error": "invalid_grant", "error_description": "Unknown code"}, status=400)

    if ac.consumed:
        return JsonResponse({"error": "invalid_grant", "error_description": "Code already used"}, status=400)
    if ac.is_expired:
        return JsonResponse({"error": "invalid_grant", "error_description": "Code expired"}, status=400)
    if ac.client.client_id != client_id:
        return JsonResponse({"error": "invalid_grant", "error_description": "Client mismatch"}, status=400)
    if ac.redirect_uri != redirect_uri:
        return JsonResponse({"error": "invalid_grant", "error_description": "redirect_uri mismatch"}, status=400)

    if ac.code_challenge:
        if not verify_challenge(
            code_verifier=code_verifier,
            code_challenge=ac.code_challenge,
            method=ac.code_challenge_method or "plain",
        ):
            return JsonResponse({"error": "invalid_grant", "error_description": "PKCE check failed"}, status=400)

    ac.consumed = True
    ac.save(update_fields=["consumed"])

    jwt_str, claims = issue_token(user=ac.user, client_id=client_id, scope=ac.scope)
    return JsonResponse({
        "access_token": jwt_str,
        "id_token": jwt_str,
        "token_type": "Bearer",
        "expires_in": int(claims["exp"] - claims["iat"]),
        "scope": claims["scope"],
    })


# ---------------------------------------------------------------------------
# Protected endpoints
# ---------------------------------------------------------------------------

class UserInfoView(views.APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        scope = getattr(request, "jwt_scope", set())
        data = {"sub": str(user.sub), "preferred_username": user.username, "role": user.role}
        if "profile" in scope:
            full_name = " ".join(p for p in (user.first_name, user.last_name) if p)
            data["name"] = full_name or user.username
        if "email" in scope and user.email:
            data["email"] = user.email
        return Response(data)


class UsersView(views.APIView):
    """Admin-only user management."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        users = request.user.__class__.objects.all().order_by("id")
        return Response(UserSerializer(users, many=True).data)

    def post(self, request):
        ser = CreateUserSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
