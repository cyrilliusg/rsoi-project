"use client";

/**
 * IdP-direct API client (admin actions).
 *
 * Decision (docs/plan.md §"Решения"): admin user management lives only on
 * Identity Provider, and the frontend talks to IdP directly with the same
 * access token issued by IdP itself.
 */
import { config } from "./config";
import { getAccessToken } from "./auth";
import { ApiError } from "./api";

export interface IdpUser {
  sub: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: "USER" | "ADMIN";
}

export interface CreateUserPayload {
  username: string;
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
  role?: "USER" | "ADMIN";
}

async function idpRequest<T>(path: string, init: RequestInit): Promise<T> {
  const token = getAccessToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const r = await fetch(`${config.idpIssuer}${path}`, { ...init, headers });
  if (!r.ok) {
    let body: unknown = null;
    let text = "";
    try {
      text = await r.text();
      body = text ? JSON.parse(text) : null;
    } catch {
      body = text;
    }
    const message =
      (body && typeof body === "object" && "detail" in body && typeof (body as { detail?: unknown }).detail === "string"
        ? (body as { detail: string }).detail
        : null) ?? `HTTP ${r.status}`;
    throw new ApiError(r.status, body, message);
  }
  if (r.status === 204) return undefined as T;
  return (await r.json()) as T;
}

export const idpUsers = {
  list: () => idpRequest<IdpUser[]>("/api/v1/users", { method: "GET" }),
  create: (payload: CreateUserPayload) =>
    idpRequest<IdpUser>("/api/v1/users", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
