import { test, expect, Page } from "@playwright/test";
import fs from "node:fs/promises";
import AxeBuilder from "@axe-core/playwright";
import {
  DEMO_EXAMPLE,
  DEMO_LABEL,
  genuineSessions,
  report,
  scoreGad,
  Session,
} from "../lib/session";

async function questionnaire(page: Page, value = "Several days") {
  await page.goto("/workspace/demo");
  await expect(
    page.getByRole("button", { name: "Next question" }),
  ).toBeDisabled();
  for (let i = 0; i < 7; i++) {
    await page.getByRole("radio", { name: new RegExp(value) }).check();
    await page
      .getByRole("button", {
        name: i === 6 ? "Review answers" : "Next question",
      })
      .click();
    await expect(
      page.locator(".demo-banner").getByText(DEMO_LABEL, { exact: true }),
    ).toBeVisible();
  }
}
async function setup(page: Page) {
  await questionnaire(page);
  await page.getByRole("button", { name: "Continue to camera" }).click();
  await expect(
    page.getByRole("button", { name: "Enable camera" }),
  ).toBeVisible();
}
async function fakeCamera(page: Page) {
  await page.addInitScript(() => {
    const w = window as unknown as {
      streams: MediaStream[];
      cameraCalls: number;
      constraints: MediaStreamConstraints[];
      starts: number;
      durations: number[];
    };
    w.streams = [];
    w.cameraCalls = 0;
    w.constraints = [];
    w.starts = 0;
    w.durations = [];
    const start = MediaRecorder.prototype.start;
    const stop = MediaRecorder.prototype.stop;
    const began = new WeakMap<MediaRecorder, number>();
    MediaRecorder.prototype.start = function (
      ...args: Parameters<MediaRecorder["start"]>
    ) {
      w.starts++;
      began.set(this, performance.now());
      return start.apply(this, args);
    };
    MediaRecorder.prototype.stop = function () {
      if (began.has(this))
        w.durations.push(performance.now() - began.get(this)!);
      return stop.call(this);
    };
    Object.defineProperty(navigator.mediaDevices, "getUserMedia", {
      configurable: true,
      value: async (constraints: MediaStreamConstraints) => {
        w.cameraCalls++;
        w.constraints.push(constraints);
        const canvas = document.createElement("canvas");
        canvas.width = 480;
        canvas.height = 360;
        const context = canvas.getContext("2d")!;
        const paint = () => {
          context.fillStyle = "#d5dbd1";
          context.fillRect(0, 0, 480, 360);
          context.fillStyle = "#203d33";
          context.font = "16px sans-serif";
          context.fillText("SYNTHETIC QA CAMERA — NOT LIVE", 15, 180);
          context.fillText(String(performance.now()), 15, 210);
        };
        paint();
        const interval = setInterval(paint, 40);
        const stream = canvas.captureStream(25);
        w.streams.push(stream);
        const track = stream.getTracks()[0];
        const nativeStop = track.stop.bind(track);
        track.stop = () => {
          clearInterval(interval);
          nativeStop();
        };
        return stream;
      },
    });
  });
}
async function tracksEnded(page: Page) {
  return page.evaluate(() =>
    (window as unknown as { streams: MediaStream[] }).streams.every((s) =>
      s.getTracks().every((t) => t.readyState === "ended"),
    ),
  );
}

test("fixed example is independent of all questionnaire scores and excluded from genuine data", () => {
  const sessions: Session[] = [];
  for (let total = 0; total <= 21; total++) {
    let rest = total;
    const answers = Array.from({ length: 7 }, () => {
      const n = Math.min(3, rest);
      rest -= n;
      return n;
    });
    const demo: Session = {
      id: String(total),
      date: "2026-11-15",
      mode: "demo",
      screening: scoreGad(answers),
      camera: null,
      note: "",
    };
    const exported = report(demo);
    expect(exported.illustrative_example).toEqual(DEMO_EXAMPLE);
    expect(exported.mode).toBe(DEMO_LABEL);
    expect(exported.questionnaire?.score).toBe(total);
    expect(exported.webcam.availability).toBe("unavailable");
    sessions.push(demo);
  }
  expect(genuineSessions(sessions)).toEqual([]);
  const real: Session = { ...sessions[0], mode: "genuine", id: "real" };
  expect(genuineSessions([...sessions, real])).toEqual([real]);
  expect(report(real).illustrative_example).toBeNull();
});

test("review/edit, back/next, in-app resume, independent questionnaire and refresh warning", async ({
  page,
}) => {
  await questionnaire(page);
  await page.getByRole("button", { name: /1. Feeling nervous/ }).click();
  await page.getByRole("radio", { name: /Nearly every day/ }).check();
  await page.getByRole("button", { name: "Next question" }).click();
  await page.getByRole("button", { name: "Back", exact: true }).click();
  await expect(
    page.getByRole("radio", { name: /Nearly every day/ }),
  ).toBeChecked();
  await page.getByRole("link", { name: "Your overview" }).click();
  await page
    .getByRole("link", { name: "Guided demonstration", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: /1. Feeling nervous/ }),
  ).toContainText("Nearly every day");
  await page.getByRole("button", { name: "Continue to camera" }).click();
  await page.getByRole("button", { name: "Back to review" }).click();
  await expect(
    page.getByRole("button", { name: /1. Feeling nervous/ }),
  ).toContainText("Nearly every day");
  await page.getByRole("button", { name: "Continue to camera" }).click();
  await page
    .getByRole("button", { name: "Continue with questionnaire only" })
    .click();
  await expect(page.getByTestId("screening-score")).toHaveText("9");
  await expect(
    page.locator(".demo-banner").getByText(DEMO_LABEL, { exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "Save this session in this browser" })
    .click();
  const saved = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("still:sessions")!),
  );
  expect(saved).toHaveLength(1);
  expect(saved[0].mode).toBe("genuine");
  expect(saved[0].demoCapture).toBeUndefined();
  const dialog = page.waitForEvent("dialog");
  const navigation = page.reload();
  const prompt = await dialog;
  expect(prompt.type()).toBe("beforeunload");
  await prompt.accept();
  await navigation;
});

for (const [cause, message] of [
  ["NotAllowedError", "permission was denied"],
  ["NotFoundError", "No camera was found"],
  ["NotReadableError", "camera is busy"],
]) {
  test(`demo camera handles ${cause} with genuine fallback`, async ({
    page,
  }) => {
    await page.addInitScript((name) => {
      Object.defineProperty(navigator.mediaDevices, "getUserMedia", {
        value: async () => {
          throw new DOMException("Test camera error", name);
        },
      });
    }, cause);
    await setup(page);
    await page.getByRole("button", { name: "Enable camera" }).click();
    await expect(page.locator('.error[role="alert"]')).toContainText(message);
    await page
      .getByRole("button", { name: "Continue with questionnaire only" })
      .click();
    await expect(page.getByTestId("screening-score")).toHaveText("7");
  });
}

test("unsupported browser and recorder error are recoverable", async ({
  page,
}) => {
  await setup(page);
  await page.evaluate(() => {
    Object.defineProperty(window, "MediaRecorder", {
      configurable: true,
      value: undefined,
    });
  });
  await page.getByRole("button", { name: "Enable camera" }).click();
  await expect(page.locator('.error[role="alert"]')).toContainText(
    "unavailable in this browser",
  );
  await expect(
    page.getByRole("button", { name: "Continue with questionnaire only" }),
  ).toBeVisible();
});

test("35-second capture, countdown, duplicate guards, demo reveal, report/print attribution and privacy", async ({
  page,
}) => {
  test.setTimeout(80000);
  await fakeCamera(page);
  const uploads: string[] = [];
  page.on("request", (request) => {
    if (request.method() !== "GET" && request.url().includes("/api/local"))
      uploads.push(request.url());
  });
  await setup(page);
  expect(
    await page.evaluate(
      () => (window as unknown as { cameraCalls: number }).cameraCalls,
    ),
  ).toBe(0);
  await page.getByRole("button", { name: "Enable camera" }).dblclick();
  await expect(page.getByText("Camera ready", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Preview ready. Face detection is not active in this demo."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Start recording" }).dblclick();
  await expect(page.getByText("Preparation · not recording yet")).toBeVisible();
  expect(
    await page.evaluate(() => (window as unknown as { starts: number }).starts),
  ).toBe(0);
  await expect(
    page.getByRole("button", { name: "Stop recording", exact: true }),
  ).toBeVisible({ timeout: 6000 });
  await expect(
    page.getByText("Preparing the predefined interface example.", {
      exact: false,
    }),
  ).toBeVisible({ timeout: 40000 });
  await expect(
    page.locator(".demo-banner").getByText(DEMO_LABEL, { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Moderate — example" }),
  ).toBeVisible({ timeout: 5000 });
  await expect(page.getByTestId("demo-screening-score")).toHaveText("7");
  await expect(page.getByText(DEMO_EXAMPLE.explanation)).toBeVisible();
  for (const width of [390, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
    await page.screenshot({
      path: `/tmp/still-demo-results-${width}.png`,
      fullPage: true,
      animations: "disabled",
    });
  }

  await expect.poll(() => tracksEnded(page)).toBe(true);
  const capture = await page.evaluate(() => {
    const w = window as unknown as {
      starts: number;
      durations: number[];
      cameraCalls: number;
      constraints: MediaStreamConstraints[];
    };
    return {
      starts: w.starts,
      durations: w.durations,
      calls: w.cameraCalls,
      constraints: w.constraints,
    };
  });
  expect(capture.starts).toBe(1);
  expect(capture.calls).toBe(1);
  expect(capture.durations[0]).toBeGreaterThanOrEqual(35000);
  expect(capture.durations[0]).toBeLessThan(35500);
  expect(capture.constraints[0].audio).toBe(false);
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download demo report" }).click();
  const json = JSON.parse(
    await fs.readFile((await (await download).path())!, "utf8"),
  );
  expect(json.mode).toBe(DEMO_LABEL);
  expect(json.illustrative_example).toEqual(DEMO_EXAMPLE);
  expect(json.questionnaire.score).toBe(7);
  expect(json.webcam.availability).toBe("unavailable");
  expect(json.demo_capture.duration_seconds).toBeGreaterThanOrEqual(35);
  expect(json.answers).toBeUndefined();
  expect(
    await page.evaluate(() => localStorage.getItem("still:sessions")),
  ).toBeNull();
  await page.emulateMedia({ media: "print" });
  await expect(
    page.locator(".demo-banner").getByText(DEMO_LABEL, { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Moderate — example" }),
  ).toBeVisible();
  await expect(page.getByTestId("demo-screening-score")).toBeVisible();
  await page.emulateMedia({ media: "screen" });
  const audit = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(
    audit.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
  await page.getByRole("button", { name: "Retry video" }).click();
  await expect(
    page.getByRole("button", { name: "Enable camera" }),
  ).toBeVisible();
  expect(uploads).toEqual([]);
});

test("early stop, countdown cancel, retry, recorder failure, navigation cleanup and cancel", async ({
  page,
}) => {
  await fakeCamera(page);
  await setup(page);
  await page.getByRole("button", { name: "Enable camera" }).click();
  await page.getByRole("button", { name: "Start recording" }).click();
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
  await expect(
    page.getByRole("heading", { name: "Moderate — example" }),
  ).toHaveCount(0);
  await expect.poll(() => tracksEnded(page)).toBe(true);
  await page.getByRole("button", { name: "Retry camera" }).click();
  await page.evaluate(() => {
    Object.defineProperty(window, "MediaRecorder", {
      configurable: true,
      value: class {
        static isTypeSupported() {
          return true;
        }
        constructor() {
          throw new Error("Test-only recorder unavailable");
        }
      },
    });
  });
  await page.getByRole("button", { name: "Start recording" }).click();
  await expect(page.locator('.error[role="alert"]')).toContainText(
    "Test-only recorder unavailable",
  );
  await expect.poll(() => tracksEnded(page)).toBe(true);
  await page.getByRole("button", { name: "Retry camera" }).click();
  await expect(page.getByText("Camera ready", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Your overview" }).click();
  await expect.poll(() => tracksEnded(page)).toBe(true);
  await page
    .getByRole("link", { name: "Guided demonstration", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Enable camera" }),
  ).toBeVisible();
  page.once("dialog", (d) => d.accept());
  await page.getByRole("button", { name: "Cancel demo" }).click();
  await expect(page).toHaveURL(/\/workspace$/);
  await page
    .getByRole("link", { name: "Guided demonstration", exact: true })
    .click();
  await expect(page.getByText("0/7 answered")).toBeVisible();
});

test("demo records cannot load into genuine history or trend; research route removed", async ({
  page,
}) => {
  await page.addInitScript(() =>
    localStorage.setItem(
      "still:sessions",
      JSON.stringify([
        {
          id: "test-demo",
          date: "2026-11-01",
          mode: "demo",
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
  const response = await page.goto("/research");
  expect(response?.status()).toBe(404);
  await expect(page.locator('a[href="/research"]')).toHaveCount(0);
});

for (const width of [390, 768, 1440])
  test(`demo layouts, keyboard and reduced motion at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await setup(page);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
    await expect(
      page.getByRole("heading", { name: "Ready when you are." }),
    ).toBeFocused();
    await page.getByRole("button", { name: "Enable camera" }).focus();
    await expect(
      page.getByRole("button", { name: "Enable camera" }),
    ).toBeFocused();
    const scan = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(
      scan.violations.map((v) => ({
        id: v.id,
        nodes: v.nodes.map((n) => n.target),
      })),
    ).toEqual([]);
  });

test("late permission resolution after leaving stops tracks and creates no capture", async ({
  page,
}) => {
  await fakeCamera(page);
  await setup(page);
  await page.evaluate(() => {
    const native = navigator.mediaDevices.getUserMedia.bind(
      navigator.mediaDevices,
    );
    Object.defineProperty(navigator.mediaDevices, "getUserMedia", {
      value: async (constraints: MediaStreamConstraints) => {
        await new Promise<void>((resolve) => {
          (window as unknown as { resolveCamera: () => void }).resolveCamera =
            resolve;
        });
        return native(constraints);
      },
    });
  });
  await page.getByRole("button", { name: "Enable camera" }).click();
  await expect(
    page.getByRole("button", { name: "Requesting permission…" }),
  ).toBeVisible();
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
  expect(
    await page.evaluate(() => (window as unknown as { starts: number }).starts),
  ).toBe(0);
});

test("background interruption is incomplete and cancellation can be declined", async ({
  page,
}) => {
  await fakeCamera(page);
  await setup(page);
  page.once("dialog", (dialog) => dialog.dismiss());
  await page.getByRole("button", { name: "Cancel demo" }).click();
  await expect(
    page.getByRole("button", { name: "Enable camera" }),
  ).toBeVisible();
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
  await expect(
    page.getByRole("button", { name: "Retry camera" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Moderate — example" }),
  ).toHaveCount(0);
});

test("mobile workspace drawer traps focus, shows demo label and closes with Escape", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/workspace/demo");
  await page.getByRole("button", { name: "Open workspace navigation" }).click();
  const drawer = page.getByRole("dialog");
  await expect(drawer).toBeVisible();
  await expect(drawer.getByText(DEMO_LABEL)).toBeVisible();
  await expect(drawer.getByRole("link", { name: "Still home" })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(drawer).not.toBeVisible();
  await expect(
    page.getByRole("button", { name: "Open workspace navigation" }),
  ).toBeFocused();
});
