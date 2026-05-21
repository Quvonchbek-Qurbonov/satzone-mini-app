import { classNames } from "@/lib/format";

type Props = {
  total: number;
  currentIndex: number;
  answered: Set<number>;
  flagged: Set<number>;
  onJump: (idx: number) => void;
};

export default function QuestionNav({ total, currentIndex, answered, flagged, onJump }: Props) {
  return (
    <div className="flex gap-1 overflow-x-auto px-2 py-2 bg-secondaryBg border-t border-hint/20">
      {Array.from({ length: total }).map((_, idx) => (
        <button
          key={idx}
          className={classNames(
            "q-pill relative",
            answered.has(idx) && "answered",
            currentIndex === idx && "current",
            flagged.has(idx) && "flagged",
          )}
          onClick={() => onJump(idx)}
          aria-label={`Go to question ${idx + 1}`}
        >
          {idx + 1}
        </button>
      ))}
    </div>
  );
}
