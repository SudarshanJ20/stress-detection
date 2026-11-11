import { test, expect } from "@playwright/test";
import fs from "node:fs/promises";
import { scoreGad, report, gad } from "../lib/session";
import AxeBuilder from "@axe-core/playwright";

// All answers in these tests are explicit test inputs, not participant observations.
test("all score boundaries, incomplete values, and report source consistency", () => {
  for (let total = 0; total <= 21; total++) {
    let remaining = total;
    const answers = Array.from({ length: 7 }, () => {
      const v = Math.min(3, remaining);
      remaining -= v;
      return v;
    });
    const value = scoreGad(answers);
    expect(value.score).toBe(total);
    expect(value.category).toBe(
      total < 5
        ? "Minimal"
        : total < 10
          ? "Mild"
          : total < 15
            ? "Moderate"
            : "Severe",
    );
    expect(
      report({
        id: "test",
        date: "test",
        screening: value,
        camera: null,
        note: "",
      }).questionnaire,
    ).toEqual(value);
  }
  for (const a of [
    [],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, null],
    [0, 0, 0, 0, 0, 0, 4],
    [0, 0, 0, 0, 0, 0, 1.5],
  ])
    expect(() => scoreGad(a)).toThrow();
  expect(gad.questions).toHaveLength(7);
  expect(gad.timeframe).toContain("last 2 weeks");
});

test("guided questionnaire, report export, opt-in save, reopen, filtering and deletion", async ({
  page,
}) => {
  await page.goto("/workspace/assessment");
  await expect(
    page.getByRole("button", { name: "Next question" }),
  ).toBeDisabled();
  expect(
    await page.evaluate(() => localStorage.getItem("still:sessions")),
  ).toBeNull();
  for (let i = 0; i < 7; i++) {
    await page.getByRole("radio", { name: /More than half the days/ }).check();
    await page
      .getByRole("button", {
        name: i === 6 ? "Review answers" : /Next question/,
      })
      .click();
  }
  await page.getByRole("combobox").selectOption("Somewhat difficult");
  await page
    .getByRole("link", { name: /Calculate my screening result/ })
    .click();
  await expect(page.getByTestId("screening-score")).toHaveText("14");
  await expect(
    page.getByRole("heading", { name: /Moderate reported symptoms/ }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => localStorage.getItem("still:sessions")),
  ).toBeNull();
  const event = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download JSON report" }).click();
  const downloaded = await event;
  const json = JSON.parse(
    await fs.readFile((await downloaded.path())!, "utf8"),
  );
  expect(json.questionnaire.score).toBe(14);
  expect(json.questionnaire.category).toBe("Moderate");
  expect(json.questionnaire_difficulty).toBe("Somewhat difficult");
  expect(json.webcam.availability).toBe("not_added");
  expect(json.answers).toBeUndefined();
  await page
    .getByRole("button", { name: "Save this session in this browser" })
    .click();
  await expect(
    page.getByText(
      "Saved locally in this browser. Raw questionnaire answers are not saved.",
    ),
  ).toBeVisible();
  await page.reload();
  await page.goto("/workspace/history");
  await expect(
    page.getByText("GAD-7 14/21 · Moderate", { exact: false }),
  ).toBeVisible();
  await page.getByLabel("From").fill("2099-01-01");
  await expect(
    page.getByRole("heading", { name: "No sessions in this date range." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Clear dates" }).click();
  await page.getByRole("link", { name: "Open session" }).click();
  await expect(page.getByTestId("screening-score")).toHaveText("14");
  await page.goto("/workspace/history");
  await page.getByRole("button", { name: "Delete this saved session" }).click();
  await expect(
    page.getByRole("heading", { name: "Nothing saved yet." }),
  ).toBeVisible();
});

test("camera denied only after explicit Start, backend unavailable, and clean empty results", async ({
  page,
}) => {
  await page.addInitScript(() => {
    (window as unknown as { cameraCalls: number }).cameraCalls = 0;
    Object.defineProperty(navigator.mediaDevices, "getUserMedia", {
      value: async () => {
        (window as unknown as { cameraCalls: number }).cameraCalls++;
        throw new DOMException("denied", "NotAllowedError");
      },
    });
  });
  await page.goto("/workspace/camera");
  expect(
    await page.evaluate(
      () => (window as unknown as { cameraCalls: number }).cameraCalls,
    ),
  ).toBe(0);
  await page.getByRole("button", { name: "Start camera" }).click();
  await expect(page.locator('.error[role="alert"]')).toContainText(
    "permission was denied",
  );
  expect(
    await page.evaluate(
      () => (window as unknown as { cameraCalls: number }).cameraCalls,
    ),
  ).toBe(1);
  await page.route("**/api/local/health", (r) => r.abort());
  await page.reload();
  await expect(page.getByRole("status")).toContainText(
    "Local Python service unavailable",
  );
  await page.getByRole("button", { name: /Continue without camera/ }).click();
  await expect(
    page.getByRole("heading", { name: "No result to show yet." }),
  ).toBeVisible();
});

test("real prerecorded development input goes through local Python, report values match, deletion succeeds", async ({
  page,
}) => {
  test.setTimeout(120000);
  const input =
    "../data/processed/still-validation/development-prerecorded.mp4";
  test.skip(
    !(await fs
      .stat(input)
      .then(() => true)
      .catch(() => false)),
    "Optional private development clip is not present. See demo documentation.",
  );
  await page.goto("/workspace/camera");
  await expect(page.getByRole("button", { name: "Check again" })).toHaveCount(
    0,
  );
  await page.getByText("Use a clearly labeled prerecorded input").click();
  await page.getByLabel("Prerecorded video").setInputFiles(input);
  await expect(
    page.getByText("Prerecorded input — not a live measurement"),
  ).toBeVisible();
  await page.getByRole("button", { name: "Analyze on this computer" }).click();
  await expect(
    page.getByRole("heading", { name: "A clearer perspective." }),
  ).toBeVisible({ timeout: 100000 });
  await expect(
    page.getByText("Prerecorded input · not live", { exact: false }),
  ).toBeVisible();
  const event = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download JSON report" }).click();
  const json = JSON.parse(
    await fs.readFile((await (await event).path())!, "utf8"),
  );
  expect(json.questionnaire).toBeNull();
  expect(json.webcam.source).toBe("prerecorded");
  expect(json.webcam.scheduled_windows).toBe(1);
  expect(json.webcam.pulse).toHaveLength(6);
  for (const row of json.webcam.pulse) {
    if (row.status === "accepted") {
      expect(row.estimated_bpm).not.toBeNull();
      await expect(
        page
          .getByText(`${row.estimated_bpm.toFixed(1)} BPM`, { exact: true })
          .first(),
      ).toBeVisible();
    } else expect(row.estimated_bpm).toBeNull();
  }
});

test("interrupted upload/analysis is cancelled; unsupported fixture is visibly prerecorded", async ({
  page,
}) => {
  let removed = false;
  await page.route("**/api/local/jobs", async (route) => {
    if (route.request().method() === "POST")
      await route.fulfill({
        json: { id: "test-job", stage: "awaiting_upload" },
      });
    else await route.continue();
  });
  await page.route("**/api/local/jobs/test-job/video", (route) =>
    route.fulfill({ json: { stage: "queued" } }),
  );
  await page.route("**/api/local/jobs/test-job", (route) => {
    if (route.request().method() === "DELETE") {
      removed = true;
      return route.fulfill({ json: { deleted: true } });
    }
    return route.fulfill({
      json: { id: "test-job", stage: "queued", result: null },
    });
  });
  await page.goto("/workspace/camera");
  await page.getByText("Use a clearly labeled prerecorded input").click();
  await page.getByLabel("Prerecorded video").setInputFiles({
    name: "synthetic-test.webm",
    mimeType: "video/webm",
    buffer: Buffer.from("synthetic test only"),
  });
  await page.getByRole("button", { name: "Analyze on this computer" }).click();
  await expect(page.getByText("Queued for local analysis")).toBeVisible();
  await page.getByRole("link", { name: "Questionnaire", exact: true }).click();
  await expect.poll(() => removed).toBe(true);
});

test("notes, breathing controls, grounding, theme and reduced motion work", async ({
  page,
}) => {
  await page.goto("/workspace/tools");
  const box = page.getByRole("textbox");
  await box.fill("Synthetic QA note");
  expect(
    await page.evaluate(() => localStorage.getItem("still:notes")),
  ).toBeNull();
  await page.getByRole("button", { name: "Save note in this browser" }).click();
  await page.reload();
  await expect(box).toHaveValue("Synthetic QA note");
  await page.getByRole("button", { name: "Delete note" }).click();
  await expect(box).toHaveValue("");
  await page.getByRole("button", { name: "Start", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Pause", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Pause", exact: true }).click();
  await page.getByRole("button", { name: "Reset", exact: true }).click();
  await page.getByRole("checkbox").first().check();
  await page.getByRole("button", { name: "Reset checklist" }).click();
  await expect(page.getByRole("checkbox").first()).not.toBeChecked();
  await page.goto("/workspace/settings");
  await page.getByLabel("Appearance").selectOption("dark");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page
    .getByRole("checkbox", { name: /Reduce decorative motion/ })
    .check();
  await expect(page.locator("html")).toHaveAttribute("data-reduced", "true");
});

for (const width of [390, 768, 1440])
  test(`responsive public/app layouts and accessibility at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 960 });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    for (const route of [
      "/",
      "/about",
      "/privacy",
      "/resources",
      "/research",
      "/workspace",
      "/workspace/assessment",
      "/workspace/camera",
      "/workspace/history",
      "/workspace/settings",
    ]) {
      await page.goto(route);
      await page.waitForTimeout(250);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth + 1,
        ),
        route,
      ).toBe(true);
    }
    await page.goto("/");
    await page.waitForTimeout(1600);
    const audit = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(
      audit.violations.map((v) => ({
        id: v.id,
        nodes: v.nodes.map((n) => n.target),
      })),
    ).toEqual([]);
    if (width === 390) {
      await page.getByRole("button", { name: "Open navigation" }).click();
      await expect(page.getByRole("dialog")).toBeVisible();
      await page.keyboard.press("Escape");
      await expect(page.getByRole("dialog")).not.toBeVisible();
    }
    expect(errors).toEqual([]);
  });

test("synthetic camera exercises real MediaRecorder, auto-stop, track cleanup and unsupported Python output", async ({
  page,
}) => {
  test.setTimeout(120000);
  // Test-only generated video, visibly labeled in every frame. This is not hardware validation.
  await page.addInitScript(() => {
    Object.defineProperty(navigator.mediaDevices, "getUserMedia", {
      value: async () => {
        const canvas = document.createElement("canvas");
        canvas.width = 480;
        canvas.height = 360;
        const context = canvas.getContext("2d")!;
        let tick = 0;
        const paint = () => {
          context.fillStyle = "#d5dbd1";
          context.fillRect(0, 0, 480, 360);
          context.fillStyle = "#243c32";
          context.font = "17px sans-serif";
          context.fillText("SYNTHETIC QA CAMERA — NOT LIVE", 18, 170);
          context.fillText(String(tick++), 20, 210);
        };
        paint();
        const timer = setInterval(paint, 42);
        const stream = canvas.captureStream(24);
        (window as unknown as { testStream: MediaStream }).testStream = stream;
        stream.getTracks().forEach((track) => {
          const stop = track.stop.bind(track);
          track.stop = () => {
            clearInterval(timer);
            stop();
          };
        });
        return stream;
      },
    });
  });
  await page.goto("/workspace/camera");
  await page.getByRole("button", { name: "Start camera" }).click();
  await expect(
    page.getByRole("button", { name: "Stop camera", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Analyze on this computer" }),
  ).toBeVisible({ timeout: 45000 });
  expect(
    await page.evaluate(() =>
      (window as unknown as { testStream: MediaStream }).testStream
        .getTracks()
        .every((t) => t.readyState === "ended"),
    ),
  ).toBe(true);
  const jobResponse = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/local/jobs") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Analyze on this computer" }).click();
  const id = (await (await jobResponse).json()).id;
  await expect(
    page.getByRole("heading", { name: "A clearer perspective." }),
  ).toBeVisible({ timeout: 60000 });
  await expect(page.getByText("0.0% of decoded frames")).toBeVisible();
  const event = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download JSON report" }).click();
  const json = JSON.parse(
    await fs.readFile((await (await event).path())!, "utf8"),
  );
  expect(json.webcam.scheduled_windows).toBe(1);
  expect(json.webcam.pulse).toHaveLength(6);
  expect(
    json.webcam.pulse.every(
      (r: { estimated_bpm: number | null }) => r.estimated_bpm === null,
    ),
  ).toBe(true);
  const deleted = await page.request.delete("/api/local/jobs/" + id, {
    headers: { Origin: "http://127.0.0.1:3000", "X-Still-Local": "1" },
  });
  expect(deleted.ok()).toBe(true);
});
