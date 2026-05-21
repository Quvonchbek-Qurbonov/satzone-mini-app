import { useEffect, useState } from "react";

/** Drive a UI countdown from a server-supplied deadline (ISO string). */
export function useTimer(deadlineISO: string | null | undefined): number {
  const [secondsRemaining, setSecondsRemaining] = useState<number>(() =>
    deadlineISO ? Math.max(0, Math.floor((new Date(deadlineISO).getTime() - Date.now()) / 1000)) : 0,
  );

  useEffect(() => {
    if (!deadlineISO) return;
    const tick = () => {
      const left = Math.max(0, Math.floor((new Date(deadlineISO).getTime() - Date.now()) / 1000));
      setSecondsRemaining(left);
    };
    tick();
    const id = window.setInterval(tick, 250);
    return () => window.clearInterval(id);
  }, [deadlineISO]);

  return secondsRemaining;
}

export function formatTimer(secs: number): string {
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}
