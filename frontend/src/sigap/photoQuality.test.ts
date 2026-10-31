import { describe, expect, it } from "vitest";

import { assessPhotoMetrics } from "./photoQuality";

describe("photo preflight assessment", () => {
  it("uses the stricter minimum image side for visible-pest mode", () => {
    const metrics = { width: 300, height: 300, meanLuminance: 120, detailScore: 12 };
    expect(assessPhotoMetrics(metrics, "disease").resolution).toBe("good");
    expect(assessPhotoMetrics(metrics, "pest").resolution).toBe("warning");
  });

  it("flags extreme lighting and weak image detail as advisory warnings", () => {
    const result = assessPhotoMetrics(
      { width: 800, height: 600, meanLuminance: 20, detailScore: 2 },
      "pest",
    );
    expect(result.lighting).toBe("warning");
    expect(result.lightingKind).toBe("dark");
    expect(result.detail).toBe("warning");
  });
});
