import { describe, it, expect, vi, beforeEach, afterEach, beforeAll, afterAll } from "vitest";

// ---------------------------------------------------------------------------
// Module-level mocks (hoisted by vitest)
// ---------------------------------------------------------------------------

// Return a fixed token so ApiClient never reaches Supabase
vi.mock("@/lib/auth-token", () => ({
  getAuthToken: () => "test-token-123",
  setAuthToken: vi.fn(),
  clearAuthToken: vi.fn(),
}));

// Safety net — should never be reached since getAuthToken returns a token
vi.mock("@/lib/supabase/client", () => ({
  createClient: () => {
    throw new Error("Supabase client should not be called in these tests");
  },
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function okResponse(body: unknown = {}): Response {
  return {
    ok: true,
    status: 200,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  } as Response;
}

function errorResponse(status: number, body: string): Response {
  return {
    ok: false,
    status,
    json: () => Promise.reject(new Error("should use text()")),
    text: () => Promise.resolve(body),
  } as Response;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ApiClient", () => {
  const fetchSpy = vi.fn<(...args: Parameters<typeof fetch>) => ReturnType<typeof fetch>>();
  const originalFetch = globalThis.fetch;

  // Import once for groups that use default env (API_URL = "")
  let api: (typeof import("@/lib/api/client"))["api"];
  let ApiError: (typeof import("@/lib/api/client"))["ApiError"];

  beforeAll(async () => {
    const mod = await import("@/lib/api/client");
    api = mod.api;
    ApiError = mod.ApiError;
  });

  afterAll(() => {
    globalThis.fetch = originalFetch;
  });

  beforeEach(() => {
    fetchSpy.mockResolvedValue(okResponse());
    globalThis.fetch = fetchSpy;
  });

  afterEach(() => {
    fetchSpy.mockReset();
  });

  // -------------------------------------------------------------------------
  // Group 1: normalizeEndpoint via URL construction
  // -------------------------------------------------------------------------

  describe("URL prefix normalization", () => {
    it("prepends /api/v1 to endpoint without prefix", async () => {
      await api.get("/sessions");
      expect(fetchSpy).toHaveBeenCalledWith("/api/v1/sessions", expect.any(Object));
    });

    it("does not double prefix when endpoint already has /api/v1", async () => {
      await api.get("/api/v1/sessions");
      expect(fetchSpy).toHaveBeenCalledWith("/api/v1/sessions", expect.any(Object));
    });

    it("handles nested paths correctly", async () => {
      await api.post("/sessions/abc/rate", { rating: "green" });
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/v1/sessions/abc/rate",
        expect.objectContaining({ method: "POST" })
      );
    });

    it("preserves query strings", async () => {
      await api.get("/sessions?page=1&limit=10");
      expect(fetchSpy).toHaveBeenCalledWith("/api/v1/sessions?page=1&limit=10", expect.any(Object));
    });
  });

  // -------------------------------------------------------------------------
  // Group 2: API_URL env var deduplication
  // -------------------------------------------------------------------------

  describe("API_URL env var handling", () => {
    const savedEnv = process.env.NEXT_PUBLIC_API_URL;

    afterEach(() => {
      // Restore env
      if (savedEnv === undefined) {
        delete process.env.NEXT_PUBLIC_API_URL;
      } else {
        process.env.NEXT_PUBLIC_API_URL = savedEnv;
      }
      vi.resetModules();
    });

    it("combines base URL with normalized endpoint", async () => {
      process.env.NEXT_PUBLIC_API_URL = "http://localhost:8000";
      vi.resetModules();
      const { api: freshApi } = await import("@/lib/api/client");
      await freshApi.get("/credits");
      expect(fetchSpy).toHaveBeenCalledWith(
        "http://localhost:8000/api/v1/credits",
        expect.any(Object)
      );
    });

    it("strips trailing /api/v1 from env to avoid duplication", async () => {
      process.env.NEXT_PUBLIC_API_URL = "http://localhost:8000/api/v1";
      vi.resetModules();
      const { api: freshApi } = await import("@/lib/api/client");
      await freshApi.get("/credits");
      expect(fetchSpy).toHaveBeenCalledWith(
        "http://localhost:8000/api/v1/credits",
        expect.any(Object)
      );
    });

    it("handles both env and endpoint having /api/v1", async () => {
      process.env.NEXT_PUBLIC_API_URL = "http://localhost:8000/api/v1";
      vi.resetModules();
      const { api: freshApi } = await import("@/lib/api/client");
      await freshApi.get("/api/v1/credits");
      expect(fetchSpy).toHaveBeenCalledWith(
        "http://localhost:8000/api/v1/credits",
        expect.any(Object)
      );
    });

    it("uses relative URL when env is empty", async () => {
      process.env.NEXT_PUBLIC_API_URL = "";
      vi.resetModules();
      const { api: freshApi } = await import("@/lib/api/client");
      await freshApi.get("/credits");
      expect(fetchSpy).toHaveBeenCalledWith("/api/v1/credits", expect.any(Object));
    });
  });

  // -------------------------------------------------------------------------
  // Group 3: HTTP methods
  // -------------------------------------------------------------------------

  describe("HTTP methods", () => {
    it("get() sends no method or body", async () => {
      await api.get("/test");
      const [, opts] = fetchSpy.mock.calls[0];
      expect(opts).not.toHaveProperty("method");
      expect(opts).not.toHaveProperty("body");
    });

    it("post() with data sends POST method and JSON body", async () => {
      const data = { foo: "bar" };
      await api.post("/test", data);
      const [, opts] = fetchSpy.mock.calls[0];
      expect((opts as RequestInit).method).toBe("POST");
      expect((opts as RequestInit).body).toBe(JSON.stringify(data));
    });

    it("post() without data sends undefined body", async () => {
      await api.post("/test");
      const [, opts] = fetchSpy.mock.calls[0];
      expect((opts as RequestInit).method).toBe("POST");
      expect((opts as RequestInit).body).toBeUndefined();
    });

    it("patch() sends PATCH method with JSON body", async () => {
      await api.patch("/test", { x: 1 });
      const [, opts] = fetchSpy.mock.calls[0];
      expect((opts as RequestInit).method).toBe("PATCH");
      expect((opts as RequestInit).body).toBe(JSON.stringify({ x: 1 }));
    });

    it("put() sends PUT method", async () => {
      await api.put("/test", { x: 1 });
      const [, opts] = fetchSpy.mock.calls[0];
      expect((opts as RequestInit).method).toBe("PUT");
    });

    it("delete() sends DELETE method with no body", async () => {
      await api.delete("/test");
      const [, opts] = fetchSpy.mock.calls[0];
      expect((opts as RequestInit).method).toBe("DELETE");
      expect(opts).not.toHaveProperty("body");
    });
  });

  // -------------------------------------------------------------------------
  // Group 4: Auth headers & error handling
  // -------------------------------------------------------------------------

  describe("auth headers", () => {
    it("includes Bearer token from auth-token cache", async () => {
      await api.get("/test");
      const [, opts] = fetchSpy.mock.calls[0];
      const headers = (opts as RequestInit).headers as Record<string, string>;
      expect(headers["Authorization"]).toBe("Bearer test-token-123");
      expect(headers["Content-Type"]).toBe("application/json");
    });
  });

  describe("error handling", () => {
    it("throws ApiError on non-ok response", async () => {
      fetchSpy.mockResolvedValueOnce(errorResponse(403, "Forbidden"));
      await expect(api.get("/protected")).rejects.toThrow(ApiError);
    });

    it("ApiError carries correct status and message", async () => {
      fetchSpy.mockResolvedValueOnce(errorResponse(404, "Not found"));
      try {
        await api.get("/missing");
        expect.fail("Should have thrown");
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError);
        const apiErr = err as InstanceType<typeof ApiError>;
        expect(apiErr.status).toBe(404);
        expect(apiErr.message).toBe("Not found");
      }
    });
  });
});
