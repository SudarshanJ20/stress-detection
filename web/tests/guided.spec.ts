import { test, expect, Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { genuineSessions, report, scoreGad, Session } from "../lib/session";
import { fakeCamera, tracksEnded } from "./helpers/camera";
async function review(page: Page) {
  await page.goto("/workspace/guided");
  await expect(
    page.getByRole("button", { name: "Next question" }),
  ).toBeDisabled();
  for (let i = 0; i < 7; i++) {
    await page.getByRole("radio", { name: /Several days/ }).check();
    await page
      .getByRole("button", {
        name: i === 6 ? "Review answers" : "Next question",
      })
      .click();
  }
}
async function setup(page: Page) {
  await review(page);
  await page.getByRole("button", { name: "Continue to camera" }).click();
  await expect(
    page.getByRole("button", { name: "Continue to camera" }),
  ).toBeDisabled();
  await page.getByRole("checkbox", { name: /I consent to processing/ }).check();
  await page.getByRole("button", { name: "Continue to camera" }).click();
  await expect(
    page.getByRole("button", { name: "Enable camera" }),
  ).toBeVisible();
}

test("developer fixtures and incomplete combined assessments cannot become genuine saved results or reports", () => {
  const real: Session = {
    id: "test",
    date: "2026-11-16",
    mode: "genuine",
    screening: scoreGad([1, 1, 1, 1, 1, 1, 1]),
    camera: null,
    note: "",
    assessment_type: "questionnaire_only",
  };
  const fixture: Session = { ...real, mode: "demo" };
  const incomplete: Session = { ...real, assessment_type: "combined" };
  expect(genuineSessions([fixture, incomplete, real])).toEqual([real]);
  expect(() => report(fixture)).toThrow(/fixtures/);
  expect(() => report(incomplete)).toThrow(/Complete/);
  const exported = report(real);
  expect(exported.section_labels).toEqual({
    questionnaire: "Questionnaire results",
    webcam: "Video analysis",
  });
  expect(exported.assessment_type).toBe("questionnaire_only");
  expect(exported).not.toHaveProperty("illustrative_example");
  expect(exported).not.toHaveProperty("demo_capture");
});

test("review/edit/resume, consent before capture and no skip into combined results", async ({
  page,
}) => {
  await fakeCamera(page);
  await review(page);
  await page.getByRole("button", { name: /1. Feeling nervous/ }).click();
  await page.getByRole("radio", { name: /Nearly every day/ }).check();
  await page.getByRole("button", { name: "Next question" }).click();
  await page.getByRole("button", { name: "Back", exact: true }).click();
  await expect(
    page.getByRole("radio", { name: /Nearly every day/ }),
  ).toBeChecked();
  await page.getByRole("link", { name: "Your overview" }).click();
  await page
    .getByRole("link", { name: "Guided assessment", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: /1. Feeling nervous/ }),
  ).toContainText("Nearly every day");
  await page.getByRole("button", { name: "Continue to camera" }).click();
  expect(
    await page.evaluate(
      () => (window as unknown as { cameraCalls: number }).cameraCalls,
    ),
  ).toBe(0);
  await expect(
    page.getByRole("button", { name: "Continue to camera" }),
  ).toBeDisabled();
  await expect(
    page
      .getByRole("navigation", { name: "Assessment progress" })
      .getByRole("listitem"),
  ).toHaveCount(6);
  await expect(
    page.getByRole("button", { name: /questionnaire only/i }),
  ).toHaveCount(0);
  await page.getByRole("link", { name: "Your results", exact: true }).click();
  await expect(
    page.getByRole("heading", {
      name: "Complete the recording and local processing.",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Save this session/ }),
  ).toHaveCount(0);
  await page
    .getByRole("link", { name: "Questionnaire only", exact: true })
    .click();
  await page
    .getByRole("link", { name: /Calculate my screening result/ })
    .click();
  await expect(page.getByTestId("screening-score")).toHaveText("9");
  await expect(
    page.getByRole("heading", { name: "Video analysis" }),
  ).toBeVisible();
  await expect(
    page
      .getByText(
        "Questionnaire-only session. No video was recorded for this result.",
      )
      .first(),
  ).toBeVisible();
});

for (const [cause, message] of [
  ["NotAllowedError", "permission was denied"],
  ["NotFoundError", "No camera was found"],
  ["NotReadableError", "camera is busy"],
])
  test(`combined capture handles ${cause} without skipping recording`, async ({
    page,
  }) => {
    await page.addInitScript(
      (name) =>
        Object.defineProperty(navigator.mediaDevices, "getUserMedia", {
          value: async () => {
            throw new DOMException("Test camera error", name);
          },
        }),
      cause,
    );
    await setup(page);
    await page.getByRole("button", { name: "Enable camera" }).click();
    await expect(page.locator('.error[role="alert"]')).toContainText(message);
    await expect(
      page.getByRole("button", { name: /Continue with questionnaire only/ }),
    ).toHaveCount(0);
    await page.getByRole("button", { name: "Cancel assessment" }).click();
    await expect(page).toHaveURL(/\/workspace$/);
  });

test("countdown cancellation, early stop, retry, recorder error and navigation stop tracks", async ({
  page,
}) => {
  await fakeCamera(page);
  await setup(page);
  let jobs = 0;
  page.on("request", (r) => {
    if (r.method() === "POST" && r.url().endsWith("/api/local/jobs")) jobs++;
  });
  await page.getByRole("button", { name: "Enable camera" }).click();
  await page.getByRole("button", { name: "Start recording" }).click();
  await expect(page.getByText("Preparation · not recording yet")).toBeVisible();
  await page.getByRole("button", { name: "Cancel countdown" }).click();
  await expect.poll(() => tracksEnded(page)).toBe(true);
  await page.getByRole("button", { name: "Enable camera" }).click();
  await page.getByRole("checkbox").uncheck();
  await page.getByRole("button", { name: "Start recording" }).click();
  await page
    .getByRole("button", { name: "Stop recording", exact: true })
    .click();
  await expect(page.locator('.error[role="alert"]')).toContainText(
    "Incomplete recording",
  );
  expect(jobs).toBe(0);
  await expect.poll(() => tracksEnded(page)).toBe(true);
  await page.getByRole("button", { name: "Retry camera" }).click();
  await page.evaluate(() =>
    Object.defineProperty(window, "MediaRecorder", {
      configurable: true,
      value: class {
        static isTypeSupported() {
          return true;
        }
        constructor() {
          throw Error("Recorder test failure");
        }
      },
    }),
  );
  await page.getByRole("button", { name: "Start recording" }).click();
  await expect(page.locator('.error[role="alert"]')).toContainText(
    "Recorder test failure",
  );
  await expect.poll(() => tracksEnded(page)).toBe(true);
  await page.getByRole("button", { name: "Retry camera" }).click();
  await expect(page.getByText("Camera ready", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Your overview" }).click();
  await expect.poll(() => tracksEnded(page)).toBe(true);
});

test("background interruption and delayed permission response release capture", async ({
  page,
}) => {
  await fakeCamera(page);
  await setup(page);
  await page.evaluate(() => {
    const native = navigator.mediaDevices.getUserMedia.bind(
      navigator.mediaDevices,
    );
    (window as unknown as { originalCamera: typeof native }).originalCamera =
      native;
    Object.defineProperty(navigator.mediaDevices, "getUserMedia", {
      configurable: true,
      value: async (c: MediaStreamConstraints) => {
        await new Promise<void>((resolve) => {
          (window as unknown as { resolveCamera: () => void }).resolveCamera =
            resolve;
        });
        return native(c);
      },
    });
  });
  await page.getByRole("button", { name: "Enable camera" }).click();
  await page.getByRole("link", { name: "Your overview" }).click();
  await page.evaluate(() =>
    (window as unknown as { resolveCamera: () => void }).resolveCamera(),
  );
  await expect
    .poll(() =>
      page.evaluate(
        () => (window as unknown as { cameraCalls: number }).cameraCalls,
      ),
    )
    .toBe(1);
  await expect.poll(() => tracksEnded(page)).toBe(true);
  await page
    .getByRole("link", { name: "Guided assessment", exact: true })
    .click();
  await page.getByRole("button", { name: "Continue to camera" }).click();
  await page.getByRole("checkbox", { name: /I consent/ }).check();
  await page.getByRole("button", { name: "Continue to camera" }).click();
  await page.evaluate(() => {
    Object.defineProperty(navigator.mediaDevices, "getUserMedia", {
      value: (
        window as unknown as {
          originalCamera: (
            constraints: MediaStreamConstraints,
          ) => Promise<MediaStream>;
        }
      ).originalCamera,
    });
  });
  await page.getByRole("button", { name: "Enable camera" }).click();
  await page.getByRole("checkbox").uncheck();
  await page.getByRole("button", { name: "Start recording" }).click();
  await page.evaluate(() => {
    Object.defineProperty(document, "hidden", {
      configurable: true,
      value: true,
    });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await expect(page.locator('.error[role="alert"]')).toContainText(
    "interrupted while this tab was hidden",
  );
  await expect.poll(() => tracksEnded(page)).toBe(true);
});

for (const width of [390, 768, 1440])
  test(`combined consent and camera layout, keyboard and reduced motion at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await review(page);
    await page.getByRole("button", { name: "Continue to camera" }).click();
    await expect(
      page.getByRole("heading", { name: "Ready when you are." }),
    ).toBeFocused();
    await page.getByRole("checkbox", { name: /I consent/ }).focus();
    await page.keyboard.press("Space");
    await page.getByRole("button", { name: "Continue to camera" }).click();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
    await expect(page.getByLabel("Prerecorded video")).toHaveCount(0);
    const scan = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(
      scan.violations.map((v) => ({
        id: v.id,
        nodes: v.nodes.map((n) => n.target),
      })),
    ).toEqual([]);
    if (width === 390) {
      await page
        .getByRole("button", { name: "Open workspace navigation" })
        .click();
      await expect(page.getByRole("dialog")).toBeVisible();
      await expect(
        page.getByRole("dialog").getByRole("link", { name: /demo/i }),
      ).toHaveCount(0);
      await page.keyboard.press("Escape");
      await expect(
        page.getByRole("button", { name: "Open workspace navigation" }),
      ).toBeFocused();
    }
  });

test("public pages, FAQs, metadata, results and saved displays contain no stale claims or simulation", async ({
  page,
}) => {
  const stale =
    /camera (?:is always|observations are) optional|optional (?:video|camera)|simulat|fixed camera|MAE\b|RMSE\b|R²|training history|model (?:success|failure)|discarded without analysis/i;
  for (const path of [
    "/",
    "/about",
    "/resources",
    "/privacy",
    "/workspace",
    "/workspace/guided",
    "/workspace/assessment",
    "/workspace/results",
    "/workspace/history",
    "/workspace/reports",
    "/workspace/settings",
  ]) {
    await page.goto(path);
    await expect(page.locator("main")).not.toContainText(stale);
    await expect(
      page.locator('a[href*="/demo"],a[href="/research"]'),
    ).toHaveCount(0);
    const meta = await page
      .locator('meta[name="description"]')
      .getAttribute("content");
    expect(meta).not.toMatch(stale);
  }
  for (const path of ["/workspace/demo", "/research"]) {
    expect((await page.goto(path))?.status()).toBe(404);
  }
});

test("legacy simulated records are excluded from history and trends", async ({
  page,
}) => {
  await page.addInitScript(() =>
    localStorage.setItem(
      "still:sessions",
      JSON.stringify([
        {
          id: "legacy-fixture",
          mode: "demo",
          date: "2026-11-01",
          screening: { score: 21, category: "Severe" },
          camera: null,
          note: "",
        },
      ]),
    ),
  );
  await page.goto("/workspace/history");
  await expect(
    page.getByRole("heading", { name: "Nothing saved yet." }),
  ).toBeVisible();
  await expect(page.getByText(/GAD-7 21/)).toHaveCount(0);
});

for (const reducedMotion of ["reduce", "no-preference"] as const)
  test(`server-rendered entrances hydrate cleanly with motion preference ${reducedMotion}`, async ({
    page,
  }) => {
    await page.emulateMedia({ reducedMotion });
    const errors: string[] = [];
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(message.text());
    });
    page.on("pageerror", (error) => errors.push(error.message));
    for (const route of ["/", "/workspace/guided", "/workspace/tools"]) {
      await page.goto(route);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      if (reducedMotion === "reduce") {
        const target = route === "/" ? ".hero-copy" : ".workspace-screen";
        await expect(page.locator(target)).toHaveCSS("animation-name", "none");
      }
    }
    expect(errors).toEqual([]);
  });
