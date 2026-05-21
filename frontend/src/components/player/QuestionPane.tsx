import { useEffect, useRef } from "react";

import ChoiceList from "./ChoiceList";
import GridInInput from "./GridInInput";
import type { Question } from "@/api/mocks";
import { renderMath } from "@/lib/math";

type Props = {
  question: Question;
  questionNumber: number;
  selectedIds: string[];
  textAnswer: string;
  flagged: boolean;
  onChangeSelection: (ids: string[]) => void;
  onChangeText: (v: string) => void;
  onToggleFlag: () => void;
};

export default function QuestionPane({
  question,
  questionNumber,
  selectedIds,
  textAnswer,
  flagged,
  onChangeSelection,
  onChangeText,
  onToggleFlag,
}: Props) {
  const promptRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (promptRef.current) {
      promptRef.current.innerHTML = renderMath(question.prompt);
    }
  }, [question.id, question.prompt]);

  const isChoice =
    question.type === "single_choice" || question.type === "multi_choice";

  return (
    <section className="player-pane player-pane-right">
      <div className="flex items-center gap-3 mb-3">
        <span className="inline-flex items-center justify-center min-w-[28px] h-7 px-2 rounded bg-text text-bg text-xs font-bold">
          {questionNumber}
        </span>
        <button
          className={
            "text-sm font-semibold " + (flagged ? "text-accent" : "text-hint hover:text-accent")
          }
          onClick={onToggleFlag}
          aria-pressed={flagged}
        >
          {flagged ? "★ Flagged" : "☆ Flag for review"}
        </button>
      </div>
      <div ref={promptRef} className="text-base leading-relaxed mb-4" />
      {question.image_url && (
        <img
          src={question.image_url}
          alt=""
          className="mb-4 max-h-72 w-auto rounded border border-hint/20"
        />
      )}
      {isChoice && (
        <ChoiceList
          options={question.options}
          selectedIds={selectedIds}
          multi={question.type === "multi_choice"}
          onChange={onChangeSelection}
        />
      )}
      {!isChoice && (
        <GridInInput value={textAnswer} onChange={onChangeText} />
      )}
    </section>
  );
}
