import { useAuthStore } from "@/store/authStore";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "/api/v1";

export class ApiError extends Error {
  status: number;
  code: string;
  details: unknown;
  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

let refreshing: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  const { refreshToken, setTokens, clear } = useAuthStore.getState();
  if (!refreshToken) return false;
  if (!refreshing) {
    refreshing = (async () => {
      try {
        const r = await fetch(`${BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!r.ok) {
          await clear();
          return false;
        }
        const t = await r.json();
        await setTokens(t.access_token, t.refresh_token);
        return true;
      } finally {
        refreshing = null;
      }
    })();
  }
  return refreshing;
}

type RequestInit2 = Omit<RequestInit, "body"> & { body?: BodyInit | object };

export async function api<T = unknown>(
  path: string,
  init: RequestInit2 = {},
): Promise<T> {
  const { accessToken } = useAuthStore.getState();
  const isFormData = typeof FormData !== "undefined" && init.body instanceof FormData;
  const headers: Record<string, string> = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    ...((init.headers as Record<string, string>) ?? {}),
  };
  const body =
    init.body && !isFormData && typeof init.body === "object"
      ? JSON.stringify(init.body)
      : (init.body as BodyInit | undefined);

  const res = await fetch(`${BASE}${path}`, { ...init, headers, body });
  if (res.status === 401) {
    const refreshed = await tryRefresh();
    if (refreshed) return api<T>(path, init);
    throw new ApiError(401, "unauthorized", "Session expired");
  }
  if (!res.ok) {
    let payload: { error?: { code?: string; message?: string; details?: unknown } } = {};
    try {
      payload = await res.json();
    } catch {
      /* fall through */
    }
    const err = payload.error ?? {};
    throw new ApiError(
      res.status,
      err.code ?? "app_error",
      err.message ?? `Request failed (${res.status})`,
      err.details,
    );
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
