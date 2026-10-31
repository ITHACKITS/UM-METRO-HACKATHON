/* Detection-overlay geometry tests. */
import { describe, expect, it } from "vitest";

import { toPercentBox } from "./geometry";

describe("toPercentBox", () => {
  it("scales pixel coordinates against the analyzed image", () => {
    expect(
      toPercentBox({ x_min: 100, y_min: 50, x_max: 300, y_max: 150 }, 400, 200),
    ).toEqual({ left: 25, top: 25, width: 50, height: 50 });
  });

  it("supports normalized boxes and clamps them to the visible image", () => {
    expect(
      toPercentBox({ x_min: 0.25, y_min: 0.1, x_max: 1.2, y_max: 0.8 }, 640, 480),
    ).toEqual({ left: 25, top: 10, width: 75, height: 70 });
  });
});
