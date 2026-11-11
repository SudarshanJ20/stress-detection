"use client";
import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
  useCallback,
} from "react";
import { MotionConfig } from "motion/react";
import { Session } from "@/lib/session";
type State = {
  answers: (number | null)[];
  setAnswers: (v: (number | null)[]) => void;
  current: Session;
  setCurrent: (s: Session) => void;
  history: Session[];
  save: () => void;
  remove: (id: string) => void;
  clear: () => void;
  newSession: () => void;
  open: (s: Session) => void;
  theme: string;
  setTheme: (s: string) => void;
  reduced: boolean;
  setReduced: (s: boolean) => void;
  storageError: string;
};
const Context = createContext<State | null>(null);
const empty = (): Session => ({
  id: crypto.randomUUID(),
  date: new Date().toISOString(),
  screening: null,
  camera: null,
  note: "",
});
export function StateProvider({ children }: { children: ReactNode }) {
  const [answers, setAnswers] = useState<(number | null)[]>(
    Array(7).fill(null),
  );
  const [current, setCurrent] = useState<Session>({
    id: "",
    date: "",
    screening: null,
    camera: null,
    note: "",
  });
  const [history, setHistory] = useState<Session[]>([]);
  const [theme, themeState] = useState("light");
  const [reduced, reducedState] = useState(false);
  const [storageError, error] = useState("");
  useEffect(() => {
    setCurrent(empty());
    try {
      const v = JSON.parse(localStorage.getItem("still:sessions") || "[]");
      if (Array.isArray(v))
        setHistory(
          v.filter(
            (s) =>
              typeof s.id === "string" &&
              typeof s.date === "string" &&
              "screening" in s &&
              "camera" in s,
          ),
        );
      const p = JSON.parse(localStorage.getItem("still:preferences") || "{}");
      themeState(p.theme === "dark" ? "dark" : "light");
      reducedState(Boolean(p.reduced));
    } catch {
      error("Browser storage could not be read. This session stays temporary.");
    }
  }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.dataset.reduced = String(reduced);
  }, [theme, reduced]);
  const persist = useCallback((h: Session[]) => {
    try {
      localStorage.setItem("still:sessions", JSON.stringify(h));
      setHistory(h);
      error("");
    } catch {
      error("Saving failed. Browser storage may be disabled or full.");
    }
  }, []);
  const preferences = (t: string, r: boolean) => {
    themeState(t);
    reducedState(r);
    try {
      localStorage.setItem(
        "still:preferences",
        JSON.stringify({ theme: t, reduced: r }),
      );
    } catch {
      error("Preferences could not be saved.");
    }
  };
  const clear = () => {
    localStorage.removeItem("still:sessions");
    localStorage.removeItem("still:notes");
    localStorage.removeItem("still:preferences");
    themeState("light");
    reducedState(false);
    setHistory([]);
    setAnswers(Array(7).fill(null));
    setCurrent(empty());
  };
  return (
    <Context.Provider
      value={{
        answers,
        setAnswers,
        current,
        setCurrent,
        history,
        save: () =>
          persist([current, ...history.filter((s) => s.id !== current.id)]),
        remove: (id) => persist(history.filter((s) => s.id !== id)),
        clear,
        newSession: () => {
          setCurrent(empty());
          setAnswers(Array(7).fill(null));
        },
        open: setCurrent,
        theme,
        setTheme: (t) => preferences(t, reduced),
        reduced,
        setReduced: (r) => preferences(theme, r),
        storageError,
      }}
    >
      <MotionConfig reducedMotion={reduced ? "always" : "user"}>
        {children}
      </MotionConfig>
    </Context.Provider>
  );
}
export const useStill = () => {
  const s = useContext(Context);
  if (!s) throw Error("Still provider missing");
  return s;
};
