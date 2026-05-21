import { formatTimer } from "@/hooks/useTimer";
import { classNames } from "@/lib/format";

type Props = {
  seconds: number;
};

export default function ModuleTimer({ seconds }: Props) {
  const low = seconds <= 60;
  return (
    <div
      className={classNames(
        "px-3 py-1 rounded font-mono text-base font-bold tabular-nums",
        low ? "bg-danger text-white" : "bg-secondaryBg text-text",
      )}
    >
      {formatTimer(seconds)}
    </div>
  );
}
