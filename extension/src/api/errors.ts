// A typed error hierarchy for backend communication.
//
// Why typed errors instead of throwing strings: the UI layer needs to react
// DIFFERENTLY per failure (offline → "start the backend"; timeout → "try again";
// validation → "fix the input"). A discriminated `code` lets callers branch
// without string-matching messages, and the subclasses carry the right context
// (status, url, timeout) for a good user-facing message.
//
// This module is pure (no `vscode`, no `node`), so it is reusable and testable.

export type ApiErrorCode =
  | "offline"
  | "timeout"
  | "validation"
  | "server"
  | "invalid_response";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly code: ApiErrorCode,
    public readonly status?: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** The backend could not be reached at all (connection refused, DNS, etc.). */
export class OfflineError extends ApiError {
  constructor(url: string) {
    super(`Could not reach the backend at ${url}. Is it running?`, "offline");
    this.name = "OfflineError";
  }
}

/** The request exceeded the configured timeout and was aborted. */
export class TimeoutError extends ApiError {
  constructor(timeoutMs: number) {
    super(`Request timed out after ${timeoutMs}ms.`, "timeout");
    this.name = "TimeoutError";
  }
}

/** The backend rejected the request with a 4xx (bad/unprocessable input). */
export class ValidationError extends ApiError {
  constructor(status: number, detail?: string) {
    super(
      `Backend rejected the request (${status})${detail ? `: ${detail}` : ""}.`,
      "validation",
      status
    );
    this.name = "ValidationError";
  }
}

/** The backend failed with a 5xx (its problem, worth retrying). */
export class ServerError extends ApiError {
  constructor(status: number, statusText: string) {
    super(`Backend error ${status} ${statusText}.`, "server", status);
    this.name = "ServerError";
  }
}

/** The response arrived but was not the JSON shape we expected. */
export class InvalidResponseError extends ApiError {
  constructor(detail?: string) {
    super(
      `Backend returned an unexpected response${detail ? `: ${detail}` : ""}.`,
      "invalid_response"
    );
    this.name = "InvalidResponseError";
  }
}
