import { api } from "@/api/client";

export type MockKind = "sat_rw" | "sat_math" | "generic";
export type MockStatus = "draft" | "published" | "archived";
export type QuestionType = "single_choice" | "multi_choice" | "grid_in" | "short_answer";

export type Passage = {
  id: string;
  title: string | null;
  subtitle: string | null;
  body_html: string;
  order: number;
};

export type Option = {
  id: string;
  text: string;
  order: number;
  image_url: string | null;
  is_correct?: boolean;
};

export type Question = {
  id: string;
  type: QuestionType;
  prompt: string;
  image_url: string | null;
  points: number;
  order: number;
  passage_id: string | null;
  options: Option[];
  explanation?: string;
  expected_answers?: string[] | null;
};

export type Module = {
  id: string;
  title: string;
  description: string | null;
  time_limit_minutes: number;
  order: number;
  passages: Passage[];
  questions: Question[];
};

export type MockSummary = {
  id: string;
  course_id: string;
  title: string;
  description: string | null;
  kind: MockKind;
  total_minutes: number;
  pass_percent: number;
  status: MockStatus;
  modules_count: number;
  questions_count: number;
  created_at: string;
};

export type Mock = {
  id: string;
  course_id: string;
  title: string;
  description: string | null;
  instructions: string | null;
  kind: MockKind;
  total_minutes: number;
  pass_percent: number;
  status?: MockStatus;
  modules: Module[];
};

export function fetchCourseMocks(courseId: string) {
  return api<MockSummary[]>(`/courses/${courseId}/mocks`);
}

export function fetchMock(mockId: string) {
  return api<Mock>(`/mocks/${mockId}`);
}
