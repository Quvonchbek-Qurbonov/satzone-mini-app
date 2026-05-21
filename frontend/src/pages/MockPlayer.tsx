import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import {
  fetchAttempt,
  patchAnswer,
  submitAttempt,
  type Attempt,
  type AnswerWrite,
} from "@/api/attempts";
import type { Module, Question } from "@/api/mocks";
import PassagePane from "@/components/player/PassagePane";
import QuestionPane from "@/components/player/QuestionPane";
import QuestionNav from "@/components/player/QuestionNav";
import ModuleTimer from "@/components/player/ModuleTimer";
import Spinner from "@/components/ui/Spinner";
import ErrorBanner from "@/components/ui/ErrorBanner";
import { useTimer } from "@/hooks/useTimer";
import { useTelegram } from "@/hooks/useTelegram";

type DraftAnswer = {
  selected_option_ids: string[];
  text: string;
  flagged: boolean;
};

function emptyDraft(): DraftAnswer {
  return { selected_option_ids: [], text: "", flagged: false };
}

function draftFromResponse(resp: Attempt["answers"][number] | undefined): DraftAnswer {
  if (!resp) return emptyDraft();
  return {
    selected_option_ids: resp.response?.selected_option_ids ?? [],
    text: resp.response?.text ?? "",
    flagged: resp.flagged,
  };
}

export default function MockPlayer() {
  const { attemptId } = useParams<{ attemptId: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { tg } = useTelegram();

  const { data: attempt, isLoading, error } = useQuery({
    queryKey: ["attempt", attemptId],
    queryFn: () => fetchAttempt(attemptId!),
    enabled: Boolean(attemptId),
    refetchOnMount: "always",
  });

  // Linearized question list across modules
  const flatQuestions: { module: Module; question: Question }[] = useMemo(() => {
    if (!attempt) return [];
    return attempt.modules.flatMap((m) =>
      m.questions.map((q) => ({ module: m, question: q })),
    );
  }, [attempt]);

  const [drafts, setDrafts] = useState<Record<string, DraftAnswer>>({});
  const [currentIdx, setCurrentIdx] = useState(0);
  const draftFlushTimers = useRef<Record<string, number>>({});

  // Hydrate drafts from server on first load.
  useEffect(() => {
    if (!attempt) return;
    const map: Record<string, DraftAnswer> = {};
    for (const ans of attempt.answers) {
      map[ans.question_id] = draftFromResponse(ans);
    }
    setDrafts(map);
  }, [attempt?.id]);

  // Disable Telegram vertical-swipe-to-close while playing.
  useEffect(() => {
    tg?.disableVerticalSwipes?.();
    return () => {
      tg?.enableVerticalSwipes?.();
    };
  }, [tg]);

  const secondsRemaining = useTimer(attempt?.deadline_at);

  const submit = useMutation({
    mutationFn: () => submitAttempt(attemptId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["attempt", attemptId] });
      navigate(`/attempts/${attemptId}/results`, { replace: true });
    },
  });

  // Auto-submit when timer hits zero.
  useEffect(() => {
    if (!attempt || attempt.submitted_at) return;
    if (secondsRemaining === 0 && !submit.isPending) {
      submit.mutate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [secondsRemaining]);

  const setDraft = (questionId: string, update: (d: DraftAnswer) => DraftAnswer) => {
    setDrafts((prev) => {
      const next = { ...prev, [questionId]: update(prev[questionId] ?? emptyDraft()) };
      scheduleFlush(questionId, next[questionId]);
      return next;
    });
  };

  const scheduleFlush = (questionId: string, draft: DraftAnswer) => {
    if (draftFlushTimers.current[questionId]) {
      window.clearTimeout(draftFlushTimers.current[questionId]);
    }
    draftFlushTimers.current[questionId] = window.setTimeout(() => {
      const payload: AnswerWrite = {
        question_id: questionId,
        flagged: draft.flagged,
      };
      if (draft.selected_option_ids.length > 0) {
        payload.selected_option_ids = draft.selected_option_ids;
      }
      if (draft.text.trim()) {
        payload.text = draft.text;
      }
      patchAnswer(attemptId!, payload).catch(() => {
        /* swallowed — the next change will retry */
      });
    }, 500);
  };

  if (isLoading || !attempt) return <Spinner label="Loading mock…" />;
  if (error) return <ErrorBanner title="Could not load attempt" message={(error as Error).message} />;
  if (attempt.submitted_at) {
    // already submitted; jump to results
    navigate(`/attempts/${attemptId}/results`, { replace: true });
    return null;
  }
  if (flatQuestions.length === 0) {
    return <ErrorBanner title="This mock has no questions" />;
  }

  const current = flatQuestions[currentIdx];
  const currentQ = current.question;
  const passage = currentQ.passage_id
    ? current.module.passages.find((p) => p.id === currentQ.passage_id) ?? null
    : null;
  const draft = drafts[currentQ.id] ?? emptyDraft();

  const answered = new Set<number>();
  const flagged = new Set<number>();
  flatQuestions.forEach((fq, idx) => {
    const d = drafts[fq.question.id];
    if (!d) return;
    if (d.selected_option_ids.length > 0 || d.text.trim()) answered.add(idx);
    if (d.flagged) flagged.add(idx);
  });

  const onPrev = () => setCurrentIdx((i) => Math.max(0, i - 1));
  const onNext = () => setCurrentIdx((i) => Math.min(flatQuestions.length - 1, i + 1));

  const onSubmitClicked = () => {
    if (tg?.showPopup) {
      tg.showPopup(
        {
          title: "Submit mock?",
          message: `You answered ${answered.size} of ${flatQuestions.length}. This cannot be undone.`,
          buttons: [
            { id: "submit", type: "destructive", text: "Submit" },
            { id: "cancel", type: "cancel" },
          ],
        },
        (id) => {
          if (id === "submit") submit.mutate();
        },
      );
    } else if (window.confirm("Submit the mock now?")) {
      submit.mutate();
    }
  };

  const isMath = attempt.mock_kind === "sat_math";

  return (
    <div className="player-shell">
      <header className="flex items-center justify-between px-3 py-2 border-b border-hint/20">
        <div className="text-sm font-semibold truncate">{attempt.mock_title}</div>
        <ModuleTimer seconds={secondsRemaining} />
      </header>

      <div className="player-main">
        {!isMath && <PassagePane passage={passage} />}
        {!isMath && <div className="player-divider" />}
        <QuestionPane
          question={currentQ}
          questionNumber={currentIdx + 1}
          selectedIds={draft.selected_option_ids}
          textAnswer={draft.text}
          flagged={draft.flagged}
          onChangeSelection={(ids) =>
            setDraft(currentQ.id, (d) => ({ ...d, selected_option_ids: ids }))
          }
          onChangeText={(v) => setDraft(currentQ.id, (d) => ({ ...d, text: v }))}
          onToggleFlag={() => setDraft(currentQ.id, (d) => ({ ...d, flagged: !d.flagged }))}
        />
      </div>

      <QuestionNav
        total={flatQuestions.length}
        currentIndex={currentIdx}
        answered={answered}
        flagged={flagged}
        onJump={setCurrentIdx}
      />

      <footer className="flex items-center justify-between gap-2 px-3 py-2 border-t border-hint/20 bg-secondaryBg">
        <button className="btn btn-secondary" onClick={onPrev} disabled={currentIdx === 0}>
          Back
        </button>
        {currentIdx < flatQuestions.length - 1 ? (
          <button className="btn btn-primary flex-1" onClick={onNext}>
            Next
          </button>
        ) : (
          <button
            className="btn btn-danger flex-1"
            onClick={onSubmitClicked}
            disabled={submit.isPending}
          >
            {submit.isPending ? "Submitting…" : "Submit mock"}
          </button>
        )}
      </footer>
    </div>
  );
}
