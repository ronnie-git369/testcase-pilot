// Transport: a small, robust HTTP client for the backend.
//
// Responsibilities (and ONLY these): build the URL, enforce a timeout, retry
// transient failures, map raw failures to the typed errors in errors.ts, and
// parse JSON. It knows nothing about `vscode`, the UI, or which endpoints mean
// what — that's the service layer's job (M4). Keeping it pure makes it fully
// unit-testable in plain Node by injecting a fake `fetch` (see apiClient.test.ts).
//
// Retry policy: only OFFLINE / TIMEOUT / 5xx are retried (they may be transient).
// A 4xx (validation) or a malformed body will not fix itself, so we fail fast.

import {
  ApiError,
  InvalidResponseError,
  OfflineError,
  ServerError,
  TimeoutError,
  ValidationError,
} from "./errors";
import { buildUrl } from "./endpoints";

export type FetchFn = typeof fetch;

export interface ApiClientOptions {
  baseUrl: string;
  timeoutMs?: number;
  maxRetries?: number;
  /** Injectable for tests; defaults to the global fetch. */
  fetchFn?: FetchFn;
  /** Injectable for tests so backoff doesn't actually wait. */
  sleep?: (ms: number) => Promise<void>;
}

const DEFAULT_TIMEOUT_MS = 15_000;
const DEFAULT_MAX_RETRIES = 2;
const BASE_BACKOFF_MS = 250;

export class ApiClient {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly maxRetries: number;
  private readonly fetchFn: FetchFn;
  private readonly sleep: (ms: number) => Promise<void>;

  constructor(options: ApiClientOptions) {
    this.baseUrl = options.baseUrl;
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.maxRetries = options.maxRetries ?? DEFAULT_MAX_RETRIES;
    this.fetchFn = options.fetchFn ?? fetch;
    this.sleep =
      options.sleep ?? ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
  }

  postJson<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>("POST", path, body);
  }

  getJson<T>(path: string): Promise<T> {
    return this.request<T>("GET", path);
  }

  private async request<T>(
    method: "GET" | "POST",
    path: string,
    body?: unknown
  ): Promise<T> {
    const url = buildUrl(this.baseUrl, path);
    let lastError: ApiError | undefined;

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      if (attempt > 0) {
        await this.sleep(this.backoffMs(attempt));
      }
      try {
        return await this.attempt<T>(method, url, body);
      } catch (err) {
        const apiError = err as ApiError;
        lastError = apiError;
        if (!this.isRetryable(apiError)) {
          throw apiError;
        }
      }
    }

    // Exhausted retries on a retryable error.
    throw lastError;
  }

  private async attempt<T>(
    method: "GET" | "POST",
    url: string,
    body?: unknown
  ): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);

    let response: Response;
    try {
      response = await this.fetchFn(url, {
        method,
        headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
    } catch {
      // fetch rejects on network failure OR when the signal aborts.
      if (controller.signal.aborted) {
        throw new TimeoutError(this.timeoutMs);
      }
      throw new OfflineError(url);
    } finally {
      clearTimeout(timer);
    }

    if (!response.ok) {
      if (response.status >= 500) {
        throw new ServerError(response.status, response.statusText);
      }
      throw new ValidationError(response.status, await this.safeText(response));
    }

    try {
      return (await response.json()) as T;
    } catch {
      throw new InvalidResponseError("response was not valid JSON");
    }
  }

  private isRetryable(error: ApiError): boolean {
    return (
      error.code === "offline" ||
      error.code === "timeout" ||
      error.code === "server"
    );
  }

  /** Exponential backoff with jitter: ~250ms, ~500ms, ~1000ms (+/- jitter). */
  private backoffMs(attempt: number): number {
    const base = BASE_BACKOFF_MS * 2 ** (attempt - 1);
    return base + Math.floor(Math.random() * base);
  }

  private async safeText(response: Response): Promise<string> {
    try {
      return (await response.text()).slice(0, 200);
    } catch {
      return "";
    }
  }
}
