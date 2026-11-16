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
        label="Video analysis"
        title="A moment to observe."
        sub="Record 35 seconds, review your video and choose local processing."
      />
      <VideoAnalysis
        onComplete={(camera, recordingId) => {
          setCurrent({
            ...current,
            mode: "genuine",
            assessment_type: current.screening ? "combined" : "video_only",
            camera,
            recordingId,
          });
          router.push("/workspace/results");
        }}
        onBack={() => router.push("/workspace/assessment")}
        onCancel={() => router.push("/workspace")}
        onQuestionnaire={() => {
          setCurrent({
            ...current,
            assessment_type: "questionnaire_only",
            camera: null,
            recordingId: undefined,
          });
          router.push("/workspace/results");
        }}
      />
    </>
  );
}
