import { api } from "@/api/client";
import type { MockKind, MockStatus, QuestionType } from "@/api/mocks";

export type AdminOption = {
  id: string;
  text: string;
  order: number;
  image_url: string | null;
  is_correct: boolean;
};

export type AdminQuestion = {
  id: string;
  type: QuestionType;
  prompt: string;
  explanation: string | null;
  image_url: string | null;
  points: number;
  order: number;
  passage_id: string | null;
  expected_answers: string[] | null;
  options: AdminOption[];
};

export type AdminPassage = {
  id: string;
  title: string | null;
  subtitle: string | null;
  body_html: string;
  order: number;
};

export type AdminModule = {
  id: string;
  title: string;
  description: string | null;
  time_limit_minutes: number;
  order: number;
  passages: AdminPassage[];
  questions: AdminQuestion[];
};

export type AdminMock = {
  id: string;
  course_id: string;
  title: string;
  description: string | null;
  instructions: string | null;
  kind: MockKind;
  total_minutes: number;
  pass_percent: number;
  status: MockStatus;
  modules: AdminModule[];
  created_at: string;
};

export type MockCreatePayload = {
  course_id: string;
  title: string;
  description?: string;
  instructions?: string;
  kind: MockKind;
  total_minutes: number;
  pass_percent: number;
};

export function fetchAdminMocks(courseId?: string) {
  const qs = courseId ? `?course_id=${courseId}` : "";
  return api<AdminMock[]>(`/admin/mocks${qs}`);
}

export function fetchAdminMock(mockId: string) {
  return api<AdminMock>(`/admin/mocks/${mockId}`);
}

export function createMock(body: MockCreatePayload) {
  return api<AdminMock>("/admin/mocks", { method: "POST", body });
}

export function patchMock(
  mockId: string,
  body: Partial<MockCreatePayload> & { status?: MockStatus },
) {
  return api<AdminMock>(`/admin/mocks/${mockId}`, { method: "PATCH", body });
}

export function deleteMock(mockId: string) {
  return api<void>(`/admin/mocks/${mockId}`, { method: "DELETE" });
}

export function createModule(
  mockId: string,
  body: { title: string; time_limit_minutes: number; description?: string },
) {
  return api<AdminModule>(`/admin/mocks/${mockId}/modules`, { method: "POST", body });
}

export function patchModule(
  moduleId: string,
  body: { title?: string; time_limit_minutes?: number; description?: string; order?: number },
) {
  return api<AdminModule>(`/admin/modules/${moduleId}`, { method: "PATCH", body });
}

export function deleteModule(moduleId: string) {
  return api<void>(`/admin/modules/${moduleId}`, { method: "DELETE" });
}

export function createPassage(
  moduleId: string,
  body: { title?: string | null; subtitle?: string | null; body_html: string },
) {
  return api<AdminPassage>(`/admin/modules/${moduleId}/passages`, { method: "POST", body });
}

export function patchPassage(
  passageId: string,
  body: { title?: string | null; subtitle?: string | null; body_html?: string },
) {
  return api<AdminPassage>(`/admin/passages/${passageId}`, { method: "PATCH", body });
}

export function deletePassage(passageId: string) {
  return api<void>(`/admin/passages/${passageId}`, { method: "DELETE" });
}

export type QuestionWritePayload = {
  type: QuestionType;
  prompt: string;
  explanation?: string;
  image_url?: string;
  points?: number;
  passage_id?: string | null;
  options?: { text: string; is_correct: boolean }[];
  expected_answers?: string[];
};

export function createQuestion(moduleId: string, body: QuestionWritePayload) {
  return api<AdminQuestion>(`/admin/modules/${moduleId}/questions`, {
    method: "POST",
    body,
  });
}

export function patchQuestion(questionId: string, body: Partial<QuestionWritePayload>) {
  return api<AdminQuestion>(`/admin/questions/${questionId}`, {
    method: "PATCH",
    body,
  });
}

export function deleteQuestion(questionId: string) {
  return api<void>(`/admin/questions/${questionId}`, { method: "DELETE" });
}

export async function uploadQuestionImage(questionId: string, file: File): Promise<string> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await api<{ message: string }>(`/admin/questions/${questionId}/image`, {
    method: "POST",
    body: fd,
  });
  return res.message;
}
