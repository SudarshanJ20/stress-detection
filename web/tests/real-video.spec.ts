import { test, expect, Page } from "@playwright/test";
import fs from "node:fs/promises";
import { execFileSync } from "node:child_process";
import AxeBuilder from "@axe-core/playwright";
const headers = { Origin: "http://127.0.0.1:3000", "X-Still-Local": "1" };
const runtime = "../data/processed/still-local";
async function selectVideo(
  page: Page,
  file: string | { name: string; mimeType: string; buffer: Buffer },
) {
  await page.getByText("Use a clearly labeled prerecorded input").click();
  await page.getByLabel("Prerecorded video").setInputFiles(file);
  await expect(
    page.getByRole("button", { name: "Analyze on this computer" }),
  ).toBeDisabled();
}
async function consent(page: Page) {
  await page.getByRole("checkbox", { name: /I consent to processing/ }).check();
}
async function downloadReport(page: Page) {
  const event = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download JSON report" }).click();
  return JSON.parse(await fs.readFile((await (await event).path())!, "utf8"));
}

test("real measurements preserve sources, units, reports and explicitly retained recording deletion", async ({
  page,
}) => {
  test.setTimeout(90000);
  const path = "../data/processed/still-validation/development-prerecorded.mp4";
  test.skip(
    !(await fs
      .stat(path)
      .then(() => true)
      .catch(() => false)),
    "Optional consented development recording unavailable.",
  );
  await page.goto("/workspace/assessment");
  for (let i = 0; i < 7; i++) {
    await page.getByRole("radio", { name: /More than half the days/ }).check();
    await page
      .getByRole("button", {
        name: i === 6 ? "Review answers" : "Next question",
      })
      .click();
  }
  await page
    .getByRole("link", { name: /Calculate my screening result/ })
    .click();
  await page.getByRole("link", { name: "Video session", exact: true }).click();
  let created = 0;
  page.on("request", (r) => {
    if (r.url().endsWith("/api/local/jobs") && r.method() === "POST") created++;
  });
  await selectVideo(page, path);
  expect(created).toBe(0);
  await expect(
    page.getByRole("checkbox", { name: /Keep the recording/ }),
  ).not.toBeChecked();
  await consent(page);
  await page.getByRole("checkbox", { name: /Keep the recording/ }).check();
  const start = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/local/jobs") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Analyze on this computer" })
    .dblclick();
  const response = await start;
  const id = (await response.json()).id;
  expect(response.request().postDataJSON().consent_local_processing).toBe(true);
  await expect(
    page.getByRole("heading", { name: "A clearer perspective." }),
  ).toBeVisible({ timeout: 60000 });
  expect(created).toBe(1);
  await expect(page.getByTestId("screening-score")).toHaveText("14");
  await expect(
    page.getByRole("heading", { name: "Video analysis" }),
  ).toBeVisible();
  await expect(page.getByText("62%", { exact: true })).toHaveCount(0);
  const json = await downloadReport(page);
  expect(json.mode).not.toContain("simulated");
  expect(json.illustrative_example).toBeUndefined();
  expect(json.recording_retained_locally).toBe(true);
  expect(json.questionnaire.score).toBe(14);
  expect(json.webcam.source).toBe("prerecorded");
  expect(json.webcam.scheduled_windows).toBe(1);
  expect(json.webcam.timing.decode_complete).toBe(true);
  expect(json.webcam.timing.missing_pts).toBe(0);
  expect(
    json.webcam.timing.pts_span_seconds +
      json.webcam.timing.last_frame_duration_seconds,
  ).toBeCloseTo(json.webcam.duration_seconds, 6);
  await expect(page.getByTestId("tracking-coverage")).toHaveText(
    `${(json.webcam.quality.tracked_coverage * 100).toFixed(1)}% of decoded frames`,
  );
  for (const key of ["beh_mouth_mean", "beh_eye_mean", "beh_motion_median"]) {
    const f = json.webcam.facial[key];
    await expect(page.getByTestId(key)).toHaveText(
      f.value === null ? "Unavailable" : f.value.toFixed(4),
    );
    expect(f.source).toBe("tracked facial landmarks");
    expect(f.unit).toBe(
      key.includes("motion") ? "face sizes per second" : "dimensionless ratio",
    );
  }
  expect(JSON.stringify(json.webcam)).not.toMatch(
    /pulse|bpm|diffuse_spectrum/i,
  );
  await expect(page.locator("main")).not.toContainText(/pulse|\bBPM\b/i);
  await expect
    .poll(() =>
      fs
        .stat(`${runtime}/jobs/${id}`)
        .then(() => true)
        .catch(() => false),
    )
    .toBe(false);
  expect(
    await fs
      .stat(`${runtime}/recordings/${id}.webm`)
      .then(() => true)
      .catch(() => false),
  ).toBe(true);
  expect(
    await page.evaluate(() => localStorage.getItem("still:sessions")),
  ).toBeNull();
  for (const width of [390, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
    await page.screenshot({
      path: `/tmp/still-real-results-${width}.png`,
      fullPage: true,
      animations: "disabled",
    });
  }
  await page.emulateMedia({ media: "print" });
  await expect(
    page.getByRole("heading", { name: "Video analysis" }),
  ).toBeVisible();
  await expect(page.getByTestId("screening-score")).toHaveText("14");
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
  await page
    .getByRole("button", { name: "Save this session in this browser" })
    .click();
  await page
    .getByRole("link", { name: "Session history", exact: true })
    .click();
  await page.getByRole("button", { name: "Delete this saved session" }).click();
  await expect
    .poll(() =>
      fs
        .stat(`${runtime}/recordings/${id}.webm`)
        .then(() => true)
        .catch(() => false),
    )
    .toBe(false);
});

test("invalid encoding reports failure and discards browser data and server files even with retention checked", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const w = window as unknown as { created: number; revoked: number };
    w.created = 0;
    w.revoked = 0;
    const make = URL.createObjectURL.bind(URL),
      revoke = URL.revokeObjectURL.bind(URL);
    URL.createObjectURL = (blob) => {
      w.created++;
      return make(blob);
    };
    URL.revokeObjectURL = (url) => {
      w.revoked++;
      revoke(url);
    };
  });
  await page.goto("/workspace/camera");
  await selectVideo(page, {
    name: "invalid-test.mp4",
    mimeType: "video/mp4",
    buffer: Buffer.from("INVALID ENCODING TEST FIXTURE"),
  });
  await consent(page);
  await page.getByRole("checkbox", { name: /Keep the recording/ }).check();
  const start = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/local/jobs") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Analyze on this computer" }).click();
  const id = (await (await start).json()).id;
  await expect(page.locator('.error[role="alert"]')).toContainText(
    "Analysis could not finish",
    { timeout: 20000 },
  );
  expect(
    await fs
      .stat(`${runtime}/jobs/${id}`)
      .then(() => true)
      .catch(() => false),
  ).toBe(false);
  expect(
    await fs
      .stat(`${runtime}/recordings/${id}.webm`)
      .then(() => true)
      .catch(() => false),
  ).toBe(false);
  await expect
    .poll(() =>
      page.evaluate(() => {
        const w = window as unknown as { created: number; revoked: number };
        return w.created === w.revoked;
      }),
    )
    .toBe(true);
  await expect(
    page.getByRole("button", { name: "Retry video", exact: true }),
  ).toBeVisible();
});

test("short decoded recording uses no 30-second windows and does not invent measurements", async ({
  page,
}) => {
  const folder = await fs.mkdtemp(
    "../data/processed/still-validation/short-synthetic-",
  );
  const path = `${folder}/input.mp4`;
  execFileSync("../.venv/bin/python", [
    "-c",
    `import av, numpy as np\nfrom fractions import Fraction\nfrom pathlib import Path\np=Path('${path}'); p.parent.mkdir(parents=True,exist_ok=True)\nwith av.open(str(p),'w') as out:\n s=out.add_stream('libx264',rate=24);s.width=160;s.height=120;s.pix_fmt='yuv420p'\n for i in range(5):\n  f=av.VideoFrame.from_ndarray(np.zeros((120,160,3),dtype=np.uint8),format='rgb24');f.pts=i;f.time_base=Fraction(1,24)\n  for packet in s.encode(f):out.mux(packet)\n for packet in s.encode():out.mux(packet)\n`,
  ]);
  try {
    await page.goto("/workspace/camera");
    await selectVideo(page, path);
    await consent(page);
    await page
      .getByRole("button", { name: "Analyze on this computer" })
      .click();
    await expect(
      page.getByRole("heading", { name: "A clearer perspective." }),
    ).toBeVisible({ timeout: 20000 });
    const json = await downloadReport(page);
    expect(json.webcam.duration_seconds).toBeLessThan(1);
    expect(json.webcam.scheduled_windows).toBe(0);
    expect(json.webcam).not.toHaveProperty("pulse");
    for (const f of Object.values(json.webcam.facial) as {
      value: number | null;
      reasons: string[];
    }[]) {
      expect(f.value).toBeNull();
      expect(f.reasons).toContain("no_complete_window");
    }
    await expect(
      page.getByText(/decoded video contains no complete 30-second interval/),
    ).toBeVisible();
  } finally {
    await fs.rm(folder, { recursive: true, force: true });
  }
});

for (const width of [390, 768, 1440])
  test(`consent review is accessible and responsive at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 960 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/workspace/camera");
    await selectVideo(page, {
      name: "synthetic-test.webm",
      mimeType: "video/webm",
      buffer: Buffer.from("PREVIEW TEST FIXTURE ONLY"),
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
    const scan = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(
      scan.violations.map((v) => ({
        id: v.id,
        nodes: v.nodes.map((n) => n.target),
      })),
    ).toEqual([]);
    await page.getByRole("checkbox", { name: /I consent/ }).focus();
    await page.keyboard.press("Space");
    await expect(
      page.getByRole("checkbox", { name: /I consent/ }),
    ).toBeChecked();
    await page
      .getByRole("button", { name: "Retry video", exact: true })
      .click();
    await expect(
      page.getByRole("button", { name: "Enable camera" }),
    ).toBeVisible();
  });

test("cancelling a native job deletes its uploaded video and never retains an unfinished recording", async ({
  page,
}) => {
  const path = "../data/processed/still-validation/development-prerecorded.mp4";
  test.skip(
    !(await fs
      .stat(path)
      .then(() => true)
      .catch(() => false)),
    "Optional consented development recording unavailable.",
  );
  await page.goto("/workspace/camera");
  await selectVideo(page, path);
  await consent(page);
  await page.getByRole("checkbox", { name: /Keep the recording/ }).check();
  const start = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/local/jobs") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Analyze on this computer" }).click();
  const id = (await (await start).json()).id;
  await page.getByRole("button", { name: "Cancel local analysis" }).click();
  await expect(
    page.getByRole("button", { name: "Enable camera" }),
  ).toBeVisible();
  expect((await page.request.get("/api/local/jobs/" + id)).status()).toBe(404);
  await expect
    .poll(() =>
      fs
        .stat(`${runtime}/jobs/${id}`)
        .then(() => true)
        .catch(() => false),
    )
    .toBe(false);
  expect(
    await fs
      .stat(`${runtime}/recordings/${id}.webm`)
      .then(() => true)
      .catch(() => false),
  ).toBe(false);
});

test("Cancel takes precedence over a completed response waiting for cleanup", async ({
  page,
}) => {
  // Test-only response for a cancellation race, not validation of measured values.
  let releaseFirst: (() => void) | undefined;
  let deletes = 0,
    finishedCleanup = false;
  await page.route("**/api/local/jobs", (route) =>
    route.fulfill({
      json: {
        id: route.request().postDataJSON().request_id,
        stage: "awaiting_upload",
      },
    }),
  );
  await page.route("**/api/local/jobs/*/video", (route) =>
    route.fulfill({ json: { stage: "queued" } }),
  );
  await page.route("**/api/local/jobs/*", async (route) => {
    if (route.request().method() === "DELETE") {
      deletes++;
      if (deletes === 1)
        await new Promise<void>((resolve) => {
          releaseFirst = resolve;
        });
      await route.fulfill({ json: { deleted: true } });
      if (deletes >= 2) finishedCleanup = true;
    } else
      await route.fulfill({
        json: {
          stage: "completed",
          recording_saved: false,
          result: {
            source: "prerecorded",
            duration_seconds: 35,
            scheduled_windows: 1,
            facial: {},
            pulse: [],
            quality: {
              tracked_coverage: 0,
              processed_frames: 0,
              missing_face_frames: 0,
              multiple_face_frames: 0,
            },
            versions: {},
            availability: "complete_intervals",
          },
        },
      });
  });
  await page.goto("/workspace/camera");
  await selectVideo(page, {
    name: "race-fixture.webm",
    mimeType: "video/webm",
    buffer: Buffer.from("CANCELLATION TEST ONLY"),
  });
  await consent(page);
  await page.getByRole("button", { name: "Analyze on this computer" }).click();
  await expect.poll(() => Boolean(releaseFirst)).toBe(true);
  await page.getByRole("button", { name: "Cancel local analysis" }).click();
  await expect(
    page.getByRole("button", { name: "Enable camera" }),
  ).toBeVisible();
  releaseFirst?.();
  await expect.poll(() => finishedCleanup).toBe(true);
  await expect(
    page.getByRole("heading", { name: "A clearer perspective." }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Enable camera" }),
  ).toBeVisible();
});
