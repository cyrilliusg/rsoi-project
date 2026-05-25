"""
End-to-end checks for IdP — full OIDC Authorization Code Flow + PKCE,
JWKs verification, admin protection.

Covers Phase 1 acceptance from docs/plan.md §1.8.
Run with: python manage.py test
"""
import base64
import hashlib
import json
import secrets
from urllib.parse import parse_qs, urlencode, urlparse

import jwt
from django.test import TestCase, override_settings

from .keys import get_keypair, jwks as build_jwks
from .models import Client as OAuthClient, User


def _pkce_pair():
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


@override_settings(IDP_ISSUER="http://testserver", IDP_ACCESS_TOKEN_TTL=3600)
class OIDCFlowTests(TestCase):
    REDIRECT_URI = "http://localhost:3000/auth/callback"

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(
            username="kirill", email="kirill@example.com",
            first_name="Kirill", last_name="Ivanov", role="USER",
        )
        cls.user.set_password("secret123")
        cls.user.save()

        cls.admin = User.objects.create(
            username="admin", email="admin@example.com", role="ADMIN",
            is_staff=True, is_superuser=True,
        )
        cls.admin.set_password("admin123")
        cls.admin.save()

        cls.client_app = OAuthClient.objects.create(
            client_id="spa",
            redirect_uris=[cls.REDIRECT_URI],
            scopes=["openid", "profile", "email"],
            is_public=True,
        )

    def test_discovery(self):
        r = self.client.get("/.well-known/openid-configuration")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["issuer"], "http://testserver")
        self.assertIn("RS256", data["id_token_signing_alg_values_supported"])
        self.assertIn("S256", data["code_challenge_methods_supported"])

    def test_jwks(self):
        r = self.client.get("/api/v1/jwks")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(len(data["keys"]), 1)
        key = data["keys"][0]
        self.assertEqual(key["kty"], "RSA")
        self.assertEqual(key["alg"], "RS256")
        self.assertTrue(key["kid"])

    def _full_flow(self, *, scope="openid profile email"):
        verifier, challenge = _pkce_pair()
        state = secrets.token_urlsafe(16)

        # 1. Login (sets session cookie)
        login = self.client.post("/login", {
            "username": "kirill", "password": "secret123", "next": "/",
        })
        self.assertEqual(login.status_code, 302)

        # 2. /authorize → 302 redirect with code+state
        qs = urlencode({
            "response_type": "code",
            "client_id": "spa",
            "redirect_uri": self.REDIRECT_URI,
            "scope": scope,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        })
        auth = self.client.get(f"/api/v1/authorize?{qs}")
        self.assertEqual(auth.status_code, 302)
        location = auth["Location"]
        parsed = urlparse(location)
        self.assertEqual(f"{parsed.scheme}://{parsed.netloc}{parsed.path}", self.REDIRECT_URI)
        params = parse_qs(parsed.query)
        self.assertEqual(params["state"], [state])
        code = params["code"][0]

        # 3. /token
        token_resp = self.client.post("/api/v1/token", {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.REDIRECT_URI,
            "client_id": "spa",
            "code_verifier": verifier,
        })
        self.assertEqual(token_resp.status_code, 200, token_resp.content)
        body = token_resp.json()
        self.assertIn("access_token", body)
        self.assertEqual(body["token_type"], "Bearer")
        return body["access_token"], verifier

    def test_authorization_code_flow_and_jwt_verifies_against_jwks(self):
        access_token, _ = self._full_flow()

        kp = get_keypair()
        header = jwt.get_unverified_header(access_token)
        self.assertEqual(header["alg"], "RS256")
        self.assertEqual(header["kid"], kp.kid)

        # The kid we sign with must match the kid advertised in /jwks.
        jwks_kid = build_jwks()["keys"][0]["kid"]
        self.assertEqual(jwks_kid, header["kid"])

        claims = jwt.decode(
            access_token,
            key=kp.public_pem,
            algorithms=["RS256"],
            audience="spa",
            issuer="http://testserver",
        )
        self.assertEqual(claims["sub"], str(self.user.sub))
        self.assertEqual(claims["preferred_username"], "kirill")
        self.assertEqual(claims["role"], "USER")
        self.assertEqual(claims["email"], "kirill@example.com")
        self.assertEqual(claims["name"], "Kirill Ivanov")

    def test_authorization_code_is_single_use(self):
        verifier, challenge = _pkce_pair()
        state = secrets.token_urlsafe(16)
        self.client.post("/login", {"username": "kirill", "password": "secret123", "next": "/"})
        qs = urlencode({
            "response_type": "code", "client_id": "spa", "redirect_uri": self.REDIRECT_URI,
            "scope": "openid", "state": state,
            "code_challenge": challenge, "code_challenge_method": "S256",
        })
        loc = self.client.get(f"/api/v1/authorize?{qs}")["Location"]
        code = parse_qs(urlparse(loc).query)["code"][0]

        body = {
            "grant_type": "authorization_code", "code": code,
            "redirect_uri": self.REDIRECT_URI, "client_id": "spa",
            "code_verifier": verifier,
        }
        self.assertEqual(self.client.post("/api/v1/token", body).status_code, 200)
        self.assertEqual(self.client.post("/api/v1/token", body).status_code, 400)

    def test_pkce_mismatch_fails(self):
        verifier, challenge = _pkce_pair()
        state = secrets.token_urlsafe(16)
        self.client.post("/login", {"username": "kirill", "password": "secret123", "next": "/"})
        qs = urlencode({
            "response_type": "code", "client_id": "spa", "redirect_uri": self.REDIRECT_URI,
            "scope": "openid", "state": state,
            "code_challenge": challenge, "code_challenge_method": "S256",
        })
        loc = self.client.get(f"/api/v1/authorize?{qs}")["Location"]
        code = parse_qs(urlparse(loc).query)["code"][0]

        r = self.client.post("/api/v1/token", {
            "grant_type": "authorization_code", "code": code,
            "redirect_uri": self.REDIRECT_URI, "client_id": "spa",
            "code_verifier": "wrong-verifier",
        })
        self.assertEqual(r.status_code, 400)

    def test_userinfo_without_token_is_unauthorized(self):
        r = self.client.get("/api/v1/userinfo")
        self.assertEqual(r.status_code, 401)

    def test_userinfo_returns_scoped_claims(self):
        access_token, _ = self._full_flow(scope="openid email")
        r = self.client.get("/api/v1/userinfo", HTTP_AUTHORIZATION=f"Bearer {access_token}")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["preferred_username"], "kirill")
        self.assertEqual(data["email"], "kirill@example.com")
        self.assertNotIn("name", data)  # 'profile' scope not requested

    def _login_as(self, username, password):
        self.client.logout()
        verifier, challenge = _pkce_pair()
        state = secrets.token_urlsafe(16)
        self.client.post("/login", {"username": username, "password": password, "next": "/"})
        qs = urlencode({
            "response_type": "code", "client_id": "spa", "redirect_uri": self.REDIRECT_URI,
            "scope": "openid profile email", "state": state,
            "code_challenge": challenge, "code_challenge_method": "S256",
        })
        loc = self.client.get(f"/api/v1/authorize?{qs}")["Location"]
        code = parse_qs(urlparse(loc).query)["code"][0]
        body = self.client.post("/api/v1/token", {
            "grant_type": "authorization_code", "code": code,
            "redirect_uri": self.REDIRECT_URI, "client_id": "spa",
            "code_verifier": verifier,
        }).json()
        return body["access_token"]

    def test_users_endpoint_requires_admin(self):
        user_token = self._login_as("kirill", "secret123")
        r = self.client.get("/api/v1/users", HTTP_AUTHORIZATION=f"Bearer {user_token}")
        self.assertEqual(r.status_code, 403)

    def test_admin_can_create_user(self):
        admin_token = self._login_as("admin", "admin123")
        r = self.client.post(
            "/api/v1/users",
            data=json.dumps({
                "username": "alice", "email": "alice@example.com",
                "password": "alicepw1", "role": "USER",
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {admin_token}",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["username"], "alice")
        self.assertTrue(User.objects.filter(username="alice").exists())

    def test_authorize_redirects_anonymous_to_login_preserving_full_query(self):
        """
        Regression: /authorize must urlencode the `next` parameter when
        bouncing through /login, otherwise the `&` separators in the OAuth
        query string get parsed as separate `/login` query params and the
        client_id / redirect_uri / state are lost on the return trip.
        """
        verifier, challenge = _pkce_pair()
        state = secrets.token_urlsafe(16)
        qs = urlencode({
            "response_type": "code", "client_id": "spa", "redirect_uri": self.REDIRECT_URI,
            "scope": "openid", "state": state,
            "code_challenge": challenge, "code_challenge_method": "S256",
        })

        # 1. Anonymous request to /authorize → 302 to /login?next=<encoded>
        r = self.client.get(f"/api/v1/authorize?{qs}")
        self.assertEqual(r.status_code, 302)
        login_redirect = r["Location"]
        self.assertTrue(login_redirect.startswith("/login?"))

        # 2. Hitting that login URL must surface the *full* original path
        #    via request.GET["next"].
        login_page = self.client.get(login_redirect)
        self.assertEqual(login_page.status_code, 200)
        # The original query string survived round-tripping.
        self.assertIn("client_id=spa", login_page.context["next"])
        self.assertIn(f"state={state}", login_page.context["next"])
        self.assertIn("code_challenge=", login_page.context["next"])

        # 3. POST /login with that `next` → user is logged in and bounced
        #    to /api/v1/authorize?<full query>, which now succeeds.
        next_value = login_page.context["next"]
        post = self.client.post("/login", {
            "username": "kirill", "password": "secret123", "next": next_value,
        })
        self.assertEqual(post.status_code, 302)
        # Follow the redirect to /authorize: should issue a code now.
        bounced = self.client.get(post["Location"])
        self.assertEqual(bounced.status_code, 302)
        self.assertTrue(bounced["Location"].startswith(self.REDIRECT_URI))
        params = parse_qs(urlparse(bounced["Location"]).query)
        self.assertEqual(params["state"], [state])
        self.assertIn("code", params)

    def test_expired_token_rejected(self):
        import time
        kp = get_keypair()
        token = jwt.encode(
            {
                "iss": "http://testserver",
                "sub": str(self.user.sub),
                "aud": "spa",
                "exp": int(time.time()) - 60,
                "iat": int(time.time()) - 3600,
                "scope": "openid",
                "preferred_username": "kirill",
                "role": "USER",
            },
            key=kp.private_pem,
            algorithm="RS256",
            headers={"kid": kp.kid},
        )
        r = self.client.get("/api/v1/userinfo", HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(r.status_code, 401)
