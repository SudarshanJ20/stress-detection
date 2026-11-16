import { Navigation, Footer } from "@/components/navigation";
import Link from "next/link";
export const metadata = { title: "Privacy" };
export default function Page() {
  return (
    <>
      <Navigation />
      <main id="main" className="content-page prose">
        <p className="eyebrow">PRIVACY, IN PLAIN LANGUAGE</p>
        <h1>
          Your space.
          <br />
          <em>Your choice.</em>
        </h1>
        <p className="lead">
          No account, analytics or external AI service. Here is exactly what
          this local app stores.
        </p>
        <h2>Temporary by default</h2>
        <p>
          Answers, questionnaire results, notes and completed observations stay
          in browser memory until you close or reload this app. GAD-7 scoring
          runs in the browser; your answers are not sent to the Python service.
          Navigating between pages preserves your current session in memory.
        </p>
        <h2>Recording and local processing</h2>
        <p>
          Enable camera requests video permission; the microphone stays off. A
          35-second recording first stays in browser memory. Nothing is
          transferred until you check consent and choose “Analyze on this
          computer.” The video goes only to the local Python backend on this
          computer. A prerecorded file is processed only after the same explicit
          consent, and its source stays labeled.
        </p>
        <p>
          Tracks stop after capture or when you leave. Browser recordings and
          replay URLs are released after transfer, cancellation or failure.
          Leaving requests cancellation of an unfinished local job. If the
          connection fails, deletion may require a retry in Settings; temporary
          jobs expire within 30 minutes.
        </p>
        <h2>Local processing</h2>
        <p>
          If you explicitly choose local analysis in Camera session, the Python
          service temporarily stores your uploaded video and measurement files
          on this computer. Intermediates and the uploaded recording are deleted
          after processing unless you explicitly choose to keep the recording.
          Job results are held in server memory for up to 30 minutes. Unfinished
          jobs expire after 30 minutes; startup removes stale temporary jobs
          after an interrupted server. Retained recordings survive restarts
          until explicitly deleted.
        </p>
        <h2>Optional browser saving</h2>
        <p>
          “Save this session in this browser” stores the score, observations,
          date and optional session note in localStorage. Raw item answers are
          not included. Saving a private note is also an explicit action. Theme
          and reduced-motion preferences are the only automatically persisted
          preferences when you change them. Browser storage is not encrypted;
          anyone with access to this browser profile may read it.
        </p>
        <h2>Deletion and exports</h2>
        <p>
          History Delete removes that browser record and its retained server
          recording when reachable. Settings can erase all Still browser
          sessions/notes and all local-server jobs/recordings. If the server is
          unavailable, the app reports that deletion is incomplete. A downloaded
          JSON report or a browser-printed PDF is outside the app’s control;
          remove those files yourself. We cannot remotely erase them.
        </p>
        <h2>Separate interface demo</h2>
        <p>
          The optional Interface demo remains clearly labeled “Demo mode —
          simulated result.” Its fixed sample is never calculated from video or
          questionnaire answers. It does not upload recordings or save demo
          outcomes to genuine history or trends. Its reports retain the
          simulation label.
        </p>
        <h2>No cloud processing</h2>
        <p>
          Run the frontend and backend on loopback as documented. Photos, fonts
          and icons are bundled locally. Resource links open external websites
          only when you choose them. No third-party scripts, trackers or remote
          model services are used. Do not expose this local presentation service
          to a public network.
        </p>
        <Link className="button" href="/workspace/settings">
          Manage local data
        </Link>
      </main>
      <Footer />
    </>
  );
}
