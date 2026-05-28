"use client";

import { config } from "./config";
import { getAccessToken } from "./auth";

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown, message: string) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

async function parseError(r: Response): Promise<ApiError> {
  let body: unknown = null;
  let text = "";
  try {
    text = await r.text();
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  const message =
    (body && typeof body === "object" && "message" in body && typeof body.message === "string"
      ? body.message
      : null) ?? `HTTP ${r.status}`;
  return new ApiError(r.status, body, message);
}

async function request<T>(
  path: string,
  init: RequestInit & { auth?: boolean } = {}
): Promise<T> {
  const { auth = true, headers, ...rest } = init;
  const finalHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(headers as Record<string, string>),
  };
  if (auth) {
    const token = getAccessToken();
    if (token) finalHeaders["Authorization"] = `Bearer ${token}`;
  }
  const r = await fetch(`${config.gatewayUrl}${path}`, {
    ...rest,
    headers: finalHeaders,
  });
  if (!r.ok) {
    throw await parseError(r);
  }
  if (r.status === 204) return undefined as T;
  return (await r.json()) as T;
}

type ApiInit = RequestInit & { auth?: boolean };

export const api = {
  get: <T>(path: string, init?: ApiInit) => request<T>(path, { ...init, method: "GET" }),
  post: <T>(path: string, body?: unknown, init?: ApiInit) =>
    request<T>(path, {
      ...init,
      method: "POST",
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  delete: <T = void>(path: string, init?: ApiInit) =>
    request<T>(path, { ...init, method: "DELETE" }),
};

// ---------------------------------------------------------------------------
// Resource shapes (kept in sync with v3/[inst][v3] Car Rental System.yml)
// ---------------------------------------------------------------------------

export type CarType = "SEDAN" | "SUV" | "MINIVAN" | "ROADSTER";

export interface Car {
  carUid: string;
  brand: string;
  model: string;
  registrationNumber: string;
  power: number | null;
  type: CarType;
  price: number;
  available: boolean;
}

export interface CarsPage {
  page: number;
  pageSize: number;
  totalElements: number;
  items: Car[];
}

export type RentalStatus = "IN_PROGRESS" | "FINISHED" | "CANCELED";

export interface RentalCar {
  carUid: string;
  brand?: string;
  model?: string;
  registrationNumber?: string;
}

export interface RentalPayment {
  paymentUid: string;
  status?: "PAID" | "CANCELED";
  price?: number;
}

export interface Rental {
  rentalUid: string;
  status: RentalStatus;
  dateFrom: string;
  dateTo: string;
  car: RentalCar;
  payment: RentalPayment;
}

export interface CreateRentalRequest {
  carUid: string;
  dateFrom: string; // YYYY-MM-DD
  dateTo: string;
}

export interface CreateRentalResponse {
  rentalUid: string;
  status: RentalStatus;
  carUid: string;
  dateFrom: string;
  dateTo: string;
  payment: RentalPayment;
}

// ---------------------------------------------------------------------------
// Endpoint helpers
// ---------------------------------------------------------------------------

export const cars = {
  list: (page = 1, size = 10, showAll = false) =>
    api.get<CarsPage>(
      `/api/v1/cars?page=${page}&size=${size}&showAll=${showAll ? "true" : "false"}`,
      { auth: true }
    ),
};

export const rentals = {
  list: () => api.get<Rental[]>("/api/v1/rental"),
  get: (uid: string) => api.get<Rental>(`/api/v1/rental/${uid}`),
  create: (req: CreateRentalRequest) =>
    api.post<CreateRentalResponse>("/api/v1/rental", req),
  cancel: (uid: string) => api.delete(`/api/v1/rental/${uid}`),
  finish: (uid: string) => api.post(`/api/v1/rental/${uid}/finish`),
};

// ---------------------------------------------------------------------------
// Statistics (gateway proxies to statistics-service, admin-only)
// ---------------------------------------------------------------------------

export interface StatisticsSummary {
  totals: {
    events: number;
    rentalsCreated: number;
    rentalsFinished: number;
    rentalsCanceled: number;
    rentalsFailed: number;
    revenue: number;
    uniqueUsers: number;
  };
  byEventType: Record<string, number>;
}

export interface EventLogEntry {
  eventId: string;
  eventType: string;
  timestamp: string;
  userId: string;
  username: string;
  correlationId: string;
  payload: Record<string, unknown>;
}

export interface EventsPage {
  count: number;
  next: string | null;
  previous: string | null;
  results: EventLogEntry[];
}

export interface UserStatistics {
  userId: string;
  username: string;
  totals: {
    events: number;
    rentalsCreated: number;
    rentalsFinished: number;
    rentalsCanceled: number;
    spent: number;
  };
  byEventType: Record<string, number>;
  lastEventAt: string | null;
}

export const statistics = {
  summary: () => api.get<StatisticsSummary>("/api/v1/statistics/summary"),
  events: (filters: { eventType?: string; from?: string; to?: string; page?: number; size?: number } = {}) => {
    const qs = new URLSearchParams();
    if (filters.eventType) qs.set("eventType", filters.eventType);
    if (filters.from) qs.set("from", filters.from);
    if (filters.to) qs.set("to", filters.to);
    qs.set("page", String(filters.page ?? 1));
    qs.set("size", String(filters.size ?? 20));
    return api.get<EventsPage>(`/api/v1/statistics/events?${qs}`);
  },
  user: (userId: string) =>
    api.get<UserStatistics>(`/api/v1/statistics/users/${userId}`),
};
