import { runAgent, getAuditLog } from "./api";

const mockFetch = jest.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockReset();
});

describe("runAgent", () => {
  it("sends prompt and returns response", async () => {
    const mockResponse = {
      tool: "categorize_transactions",
      args: {},
      diff: { type: "update_cells", changes: [] },
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const result = await runAgent("categorize all");

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8888/agent/run",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: "categorize all" }),
      }),
    );
    expect(result).toEqual(mockResponse);
  });

  it("throws on non-ok response with detail", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: () => Promise.resolve({ detail: "No matching tool" }),
    });

    await expect(runAgent("do something random")).rejects.toThrow("No matching tool");
  });

  it("throws generic message when response has no detail", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: () => Promise.reject(new Error("parse error")),
    });

    await expect(runAgent("bad")).rejects.toThrow("Request failed");
  });
});

describe("getAuditLog", () => {
  it("fetches and returns audit entries", async () => {
    const mockLog = [{ prompt: "test", tool: "t", args: {}, diff: {}, timestamp: "" }];

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockLog),
    });

    const result = await getAuditLog();

    expect(mockFetch).toHaveBeenCalledWith("http://localhost:8888/audit/log");
    expect(result).toEqual(mockLog);
  });

  it("throws on failure", async () => {
    mockFetch.mockResolvedValueOnce({ ok: false });

    await expect(getAuditLog()).rejects.toThrow("Failed to fetch audit log");
  });
});
