/**
 * Decode a JWT *without verifying its signature*.
 *
 * This is only for UI logic (show username, hide admin links, etc).
 * The backend always re-validates the token via JWKs — never trust
 * these claims for authorization decisions.
 */
export interface JwtClaims {
  sub: string;
  preferred_username?: string;
  name?: string;
  email?: string;
  role?: "USER" | "ADMIN";
  exp?: number;
  iat?: number;
  scope?: string;
}

function base64UrlDecode(input: string): string {
  const padded = input + "=".repeat((4 - (input.length % 4)) % 4);
  const b64 = padded.replace(/-/g, "+").replace(/_/g, "/");
  if (typeof atob !== "undefined") {
    return decodeURIComponent(
      atob(b64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
  }
  return Buffer.from(b64, "base64").toString("utf-8");
}

export function decodeJwt(token: string): JwtClaims | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    return JSON.parse(base64UrlDecode(parts[1])) as JwtClaims;
  } catch {
    return null;
  }
}

export function isExpired(claims: JwtClaims): boolean {
  if (!claims.exp) return true;
  return claims.exp * 1000 < Date.now();
}
