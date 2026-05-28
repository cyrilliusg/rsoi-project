/**
 * Public runtime configuration — values are inlined at Next.js build time
 * via NEXT_PUBLIC_* env vars. See .env.example for the full list.
 */
export const config = {
  idpIssuer: process.env.NEXT_PUBLIC_IDP_ISSUER ?? "http://localhost:8090",
  gatewayUrl: process.env.NEXT_PUBLIC_GATEWAY_URL ?? "http://localhost:8080",
  clientId: process.env.NEXT_PUBLIC_OAUTH_CLIENT_ID ?? "spa",
  redirectUri:
    process.env.NEXT_PUBLIC_OAUTH_REDIRECT_URI ?? "http://localhost:3000/auth/callback",
  scope: "openid profile email",
};
