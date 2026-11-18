import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs/promises";

const hiddenPulse =
  /pulse|\bbpm\b|diffuse_spectrum|distinct peak|readings available|search-band edge/i;

async function exportJson(page: Page, button: string) {
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: button }).click(),
  ]);
  const json = await fs.readFile((await download.path())!, "utf8");
  expect(json).not.toMatch(hiddenPulse);
  return JSON.parse(json);
}

test("older saved sessions hide pulse on screen, in print, and in both exports", async ({
  page,
}) => {
  await page.addInitScript(() => {
    localStorage.setItem(
      "still:sessions",
      JSON.stringify([
        {
          id: "legacy-video",
          date: "2026-11-16",
          assessment_type: "combined",
          screening: {
            score: 7,
            category: "Mild",
            source: "GAD-7 questionnaire",
            timeframe: "Last two weeks",
          },
          camera: {
            source: "webcam",
            duration_seconds: 35,
            scheduled_windows: 1,
            availability: "complete_intervals",
            facial: {
              beh_mouth_mean: {
                value: 0.1234,
                supported_windows: 1,
                scheduled_windows: 1,
              },
            },
            quality: {
              tracked_coverage: 1,
              processed_frames: 1050,
              missing_face_frames: 0,
              multiple_face_frames: 0,
              track_event_counts: {},
              region_coverage: { forehead: 1 },
            },
            pulse: [
              {
                estimated_bpm: 154,
                status: "accepted",
                method: "green",
                region: "cheek_image_right",
                window_index: 0,
                near_band_edge: true,
              },
              {
                estimated_bpm: null,
                status: "rejected",
                rejection_reason: "diffuse_spectrum",
                method: "pos",
                region: "forehead",
                window_index: 0,
              },
            ],
            versions: {
              policy_stamp: { pulse: "green-pos-baseline-v1" },
              pulse_settings: { min_bpm: 42 },
            },
            interpretation: "Pulse estimates pass fixed quality screens.",
          },
          note: "",
        },
      ]),
    );
  });

  for (const path of [
    "/",
    "/about",
    "/privacy",
    "/resources",
    "/workspace",
    "/workspace/guided",
    "/workspace/camera",
    "/workspace/assessment",
    "/workspace/history",
  ]) {
    await page.goto(path);
    await expect(page.locator("body")).not.toContainText(hiddenPulse);
  }

  await page.getByRole("link", { name: "Open session" }).click();
  await expect(page.getByTestId("screening-score")).toHaveText("7");
  await expect(page.getByTestId("beh_mouth_mean")).toHaveText("0.1234");
  await expect(page.locator("body")).not.toContainText(hiddenPulse);
  await page.getByRole("link", { name: "Reports", exact: true }).click();
  await page.emulateMedia({ media: "print" });
  await expect(page.getByTestId("screening-score")).toBeVisible();
  await expect(page.getByTestId("beh_mouth_mean")).toBeVisible();
  await expect(page.locator("body")).not.toContainText(hiddenPulse);
  await page.emulateMedia({ media: "screen" });

  const report = await exportJson(page, "Download JSON report");
  expect(report.questionnaire.score).toBe(7);
  expect(report.webcam.facial.beh_mouth_mean.value).toBe(0.1234);
  await page.goto("/workspace/settings");
  await expect(page.locator("body")).not.toContainText(hiddenPulse);
  const saved = await exportJson(page, "Export my saved data");
  expect(saved.sessions[0].screening.score).toBe(7);
  expect(saved.sessions[0].camera.facial.beh_mouth_mean.value).toBe(0.1234);
  expect(
    await page.evaluate(
      () =>
        JSON.parse(localStorage.getItem("still:sessions")!)[0].camera.pulse[0]
          .estimated_bpm,
    ),
  ).toBe(154);
});
