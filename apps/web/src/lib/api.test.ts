import { describe, expect, it } from "vitest";

import { getApiErrorMessage } from "./api";

describe("getApiErrorMessage", () => {
  it("returns fallback for unknown errors", () => {
    expect(getApiErrorMessage({}, "fallback")).toBe("fallback");
  });

  it("returns Error message", () => {
    expect(getApiErrorMessage(new Error("boom"))).toBe("boom");
  });
});
