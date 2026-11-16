"use client";
import { useRouter } from "next/navigation";
import { useStill } from "./state";
import { Heading } from "./screen-frames";
import VideoAnalysis from "./video-analysis";
export default function CameraSession() {
  const { current, setCurrent } = useStill();
  const router = useRouter();
  return (
    <>
      <Heading
        label="Video observations — webcam"
        title="A moment to observe."
        sub="Record 35 seconds, review your video and choose local processing."
      />
      <VideoAnalysis
        onComplete={(camera, recordingId) => {
          setCurrent({ ...current, mode: "genuine", camera, recordingId });
          router.push("/workspace/results");
        }}
        onBack={() => router.push("/workspace/assessment")}
        onCancel={() => router.push("/workspace")}
        onQuestionnaire={() => {
          setCurrent({ ...current, camera: null, recordingId: undefined });
          router.push("/workspace/results");
        }}
      />
    </>
  );
}
