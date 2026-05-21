import { api } from "@/api/client";
import type { Mock } from "@/api/mocks";

export type AnswerWrite = {
  question_id: string;
  selected_option_ids?: string[];
  text?: string;
  flagged?: boolean;
};

export type AnswerRead = {
  question_id: string;
  response: { selected_option_ids?: string[]; text?: string } | null;
  is_correct: boolean;
  awarded_points: number;
  flagged: boolean;
};

export type AttemptStart = {
  id: string;
  mock_id: string;
  started_at: string;
  deadline_at: string;
  status: "in_progress" | "submitted" | "expired";
};

export type Attempt = AttemptStart & {
  mock_title: string;
  mock_kind: Mock["kind"];
  pass_percent: number;
  submitted_at: string | null;
  time_spent_seconds: number;
  seconds_remaining: number;
  score_percent: number;
  raw_score: number;
  total_points: number;
  passed: boolean;
  modules: Mock["modules"];
  answers: AnswerRead[];
};

export type AttemptHistoryItem = {
  id: string;
  mock_id: string;
  mock_title: string;
  mock_kind: Mock["kind"];
  status: Attempt["status"];
  started_at: string;
  submitted_at: string | null;
  score_percent: number;
  passed: boolean;
};

export type AttemptSubmitResult = {
  id: string;
  mock_id: string;
  submitted_at: string;
  time_spent_seconds: number;
  score_percent: number;
  raw_score: number;
  total_points: number;
  passed: boolean;
};

export function startAttempt(mockId: string) {
  return api<AttemptStart>(`/mocks/${mockId}/attempts`, { method: "POST" });
}

export function fetchAttempt(attemptId: string) {
  return api<Attempt>(`/attempts/${attemptId}`);
}

export function patchAnswer(attemptId: string, payload: AnswerWrite) {
  return api<AnswerRead>(`/attempts/${attemptId}/answers`, {
    method: "PATCH",
    body: payload,
  });
}

export function submitAttempt(attemptId: string) {
  return api<AttemptSubmitResult>(`/attempts/${attemptId}/submit`, {
    method: "POST",
  });
}

export function fetchHistory() {
  return api<AttemptHistoryItem[]>("/me/attempts");
}
