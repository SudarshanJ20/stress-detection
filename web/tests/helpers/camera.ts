import { Page } from "@playwright/test";
export async function fakeCamera(page: Page) {
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
export async function tracksEnded(page: Page) {
  return page.evaluate(() =>
    (window as unknown as { streams: MediaStream[] }).streams.every((s) =>
      s.getTracks().every((t) => t.readyState === "ended"),
    ),
  );
}
