// Unit tests for the transport layer. We inject a fake `fetch` and a no-op
// `sleep`, so these run in plain Node with no network and no real backoff delay.

import assert from "node:assert/strict";
import { test } from "node:test";

import { ApiClient, type FetchFn } from "../api/ApiClient";
import {
  OfflineError,
  ServerError,
  TimeoutError,
  ValidationError,
} from "../api/errors";

const noSleep = async (): Promise<void> => {};

function okJson(data: unknown, status = 200): Response {
  return {
    ok: true,
    status,
    statusText: "OK",
    json: async () => data,
    text: async () => JSON.stringify(data),
  } as unknown as Response;
}

function errorResponse(status: number, statusText: string, body = ""): Response {
  return {
    ok: false,
    status,
    statusText,
    json: async () => {
      throw new Error("not json");
    },
    text: async () => body,
  } as unknown as Response;
}

// A fetch that returns each scripted step in turn (repeats the last step).
function scriptedFetch(steps: Array<() => Promise<Response>>): {
  fetchFn: FetchFn;
  calls: () => number;
} {
  let i = 0;
  const fetchFn = (async () => {
    const step = steps[Math.min(i, steps.length - 1)];
    i++;
    return step();
  }) as unknown as FetchFn;
  return { fetchFn, calls: () => i };
}

test("postJson returns parsed JSON on success", async () => {
  const { fetchFn } = scriptedFetch([async () => okJson({ hello: "world" })]);
  const client = new ApiClient({ baseUrl: "http://x", fetchFn, sleep: noSleep });
  const res = await client.postJson<{ hello: string }>("/p", { a: 1 });
  assert.equal(res.hello, "world");
});

test("retries a network failure, then succeeds", async () => {
  const { fetchFn, calls } = scriptedFetch([
    async () => {
      throw new Error("ECONNREFUSED");
    },
    async () => okJson({ ok: true }),
  ]);
  const client = new ApiClient({ baseUrl: "http://x", fetchFn, sleep: noSleep, maxRetries: 2 });
  const res = await client.postJson<{ ok: boolean }>("/p", {});
  assert.equal(res.ok, true);
  assert.equal(calls(), 2); // failed once, retried once
});

test("does NOT retry a 4xx validation error (fails fast)", async () => {
  const { fetchFn, calls } = scriptedFetch([
    async () => errorResponse(422, "Unprocessable Entity", "bad field"),
  ]);
  const client = new ApiClient({ baseUrl: "http://x", fetchFn, sleep: noSleep, maxRetries: 2 });
  await assert.rejects(
    () => client.postJson("/p", {}),
    (err: unknown) => {
      assert.ok(err instanceof ValidationError);
      assert.equal((err as ValidationError).status, 422);
      return true;
    }
  );
  assert.equal(calls(), 1);
});

test("retries a 5xx, then throws ServerError after exhausting retries", async () => {
  const { fetchFn, calls } = scriptedFetch([
    async () => errorResponse(500, "Internal Server Error"),
  ]);
  const client = new ApiClient({ baseUrl: "http://x", fetchFn, sleep: noSleep, maxRetries: 2 });
  await assert.rejects(
    () => client.postJson("/p", {}),
    (err: unknown) => err instanceof ServerError
  );
  assert.equal(calls(), 3); // 1 initial + 2 retries
});

test("maps a timeout (aborted request) to TimeoutError", async () => {
  const hangingFetch = ((_url: string, init: { signal?: AbortSignal }) =>
    new Promise<Response>((_, reject) => {
      init.signal?.addEventListener("abort", () => reject(new Error("aborted")));
    })) as unknown as FetchFn;
  const client = new ApiClient({
    baseUrl: "http://x",
    fetchFn: hangingFetch,
    sleep: noSleep,
    timeoutMs: 10,
    maxRetries: 0,
  });
  await assert.rejects(
    () => client.postJson("/p", {}),
    (err: unknown) => err instanceof TimeoutError
  );
});

test("exhausts retries on persistent offline, then throws OfflineError", async () => {
  const { fetchFn, calls } = scriptedFetch([
    async () => {
      throw new Error("ECONNREFUSED");
    },
  ]);
  const client = new ApiClient({ baseUrl: "http://x", fetchFn, sleep: noSleep, maxRetries: 2 });
  await assert.rejects(
    () => client.postJson("/p", {}),
    (err: unknown) => err instanceof OfflineError
  );
  assert.equal(calls(), 3);
});
