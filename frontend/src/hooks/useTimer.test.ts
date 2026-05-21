import { describe, expect, it } from "vitest";
import { formatTimer } from "@/hooks/useTimer";

describe("formatTimer", () => {
  it("formats below a minute", () => {
    expect(formatTimer(7)).toBe("00:07");
    expect(formatTimer(0)).toBe("00:00");
  });
  it("formats minutes and seconds", () => {
    expect(formatTimer(125)).toBe("02:05");
    expect(formatTimer(3600)).toBe("60:00");
  });
});
