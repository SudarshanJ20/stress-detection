import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { fakeCamera, tracksEnded } from "./helpers/camera";

test("preview checks measure synthetic pixels, remain local and release on navigation", async ({
  page,
}) => {
  await fakeCamera(page);
  let writes = 0;
  page.on("request", (request) => {
    if (request.url().includes("/api/local/") && request.method() !== "GET")
      writes++;
  });
  await page.goto("/workspace/camera");
  await expect(page.getByTestId("camera-checks")).toHaveCount(0);
  await page.getByRole("button", { name: "Enable camera" }).click();
  const checks = page.getByTestId("camera-checks");
  await expect(checks).toContainText("480 × 360");
  await expect(checks).toContainText("25.0 fps");
  await expect(checks).toContainText("adjust lighting and framing");
  await expect(checks).not.toContainText("Unavailable");
  expect(writes).toBe(0);
  for (const width of [390, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.screenshot({
      path: `/tmp/still-preview-checks-${width}.png`,
      fullPage: true,
      animations: "disabled",
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
  }
  const audit = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(audit.violations.map((v) => v.id)).toEqual([]);
  await page.getByRole("link", { name: "Your overview", exact: true }).click();
  await expect.poll(() => tracksEnded(page)).toBe(true);
  expect(writes).toBe(0);
});

test("unavailable preview pixels stay unavailable, with reduced motion", async ({
  page,
}) => {
  await fakeCamera(page);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript(() => {
    CanvasRenderingContext2D.prototype.getImageData = () => {
      throw new DOMException("Unavailable", "SecurityError");
    };
  });
  await page.goto("/workspace/camera");
  await page.getByRole("button", { name: "Enable camera" }).click();
  await expect(
    page.getByTestId("camera-checks").getByText("Unavailable", { exact: true }),
  ).toHaveCount(5);
  await expect(
    page.getByRole("button", { name: "Start recording" }),
  ).toBeEnabled();
  await page.goto("/workspace");
});
