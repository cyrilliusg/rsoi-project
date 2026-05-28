"use client";

/**
 * Browser-side OAuth helpers — PKCE + token storage.
 *
 * Storage trade-off (per docs/plan.md §3.2):
 *   - We use sessionStorage for the access token. Simpler than an
 *     httpOnly cookie BFF and acceptable for a learning project.
 *   - The token lives for 1 hour. No refresh flow.
 */
import { config } from "./config";
import { decodeJwt, isExpired, type JwtClaims } from "./jwt";

const STORAGE_TOKEN = "auth.access_token";
const STORAGE_VERIFIER = "auth.code_verifier";
const STORAGE_STATE = "auth.state";
const STORAGE_RETURN_TO = "auth.return_to";

// ---------------------------------------------------------------------------
// PKCE
// ---------------------------------------------------------------------------

function bytesToBase64Url(bytes: Uint8Array): string {
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function randomBase64Url(n: number): string {
  const arr = new Uint8Array(n);
  crypto.getRandomValues(arr);
  return bytesToBase64Url(arr);
}

async function sha256Base64Url(input: string): Promise<string> {
  const data = new TextEncoder().encode(input);
  const buf = await crypto.subtle.digest("SHA-256", data);
  return bytesToBase64Url(new Uint8Array(buf));
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export async function beginLogin(returnTo: string = "/"): Promise<void> {
  const verifier = randomBase64Url(64);
  const challenge = await sha256Base64Url(verifier);
  const state = randomBase64Url(16);

  sessionStorage.setItem(STORAGE_VERIFIER, verifier);
  sessionStorage.setItem(STORAGE_STATE, state);
  sessionStorage.setItem(STORAGE_RETURN_TO, returnTo);

  const params = new URLSearchParams({
    response_type: "code",
    client_id: config.clientId,
    redirect_uri: config.redirectUri,
    scope: config.scope,
    state,
    code_challenge: challenge,
    code_challenge_method: "S256",
  });

  window.location.assign(`${config.idpIssuer}/api/v1/authorize?${params}`);
}

export async function completeLogin(
  code: string,
  state: string
): Promise<{ accessToken: string; returnTo: string }> {
  const expectedState = sessionStorage.getItem(STORAGE_STATE);
  const verifier = sessionStorage.getItem(STORAGE_VERIFIER);
  const returnTo = sessionStorage.getItem(STORAGE_RETURN_TO) ?? "/";
  sessionStorage.removeItem(STORAGE_STATE);
  sessionStorage.removeItem(STORAGE_VERIFIER);
  sessionStorage.removeItem(STORAGE_RETURN_TO);

  if (!verifier || !expectedState) {
    throw new Error("Missing PKCE verifier / state in session storage");
  }
  if (state !== expectedState) {
    throw new Error("OAuth state mismatch — possible CSRF");
  }

  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    redirect_uri: config.redirectUri,
    client_id: config.clientId,
    code_verifier: verifier,
  });

  const r = await fetch(`${config.idpIssuer}/api/v1/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`Token exchange failed: ${r.status} ${text}`);
  }
  const data = (await r.json()) as { access_token: string };
  sessionStorage.setItem(STORAGE_TOKEN, data.access_token);
  return { accessToken: data.access_token, returnTo };
}

/**
 * Logout — clears our access token AND the IdP session cookie via
 * RP-Initiated Logout. Without the IdP round-trip the next /authorize
 * call would silently re-issue a token because the IdP still has a
 * valid session.
 *
 * `returnTo` is the URL the IdP redirects to after killing its session.
 * Defaults to the SPA root.
 */
export function logout(returnTo: string = "/"): void {
  sessionStorage.removeItem(STORAGE_TOKEN);
  sessionStorage.removeItem(STORAGE_STATE);
  sessionStorage.removeItem(STORAGE_VERIFIER);
  sessionStorage.removeItem(STORAGE_RETURN_TO);

  const postLogoutRedirect = new URL(returnTo, window.location.origin).toString();
  const url = new URL(`${config.idpIssuer}/api/v1/logout`);
  url.searchParams.set("post_logout_redirect_uri", postLogoutRedirect);
  window.location.assign(url.toString());
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  const token = sessionStorage.getItem(STORAGE_TOKEN);
  if (!token) return null;
  const claims = decodeJwt(token);
  if (!claims || isExpired(claims)) {
    sessionStorage.removeItem(STORAGE_TOKEN);
    return null;
  }
  return token;
}

export function getCurrentUser(): JwtClaims | null {
  const token = getAccessToken();
  if (!token) return null;
  return decodeJwt(token);
}
