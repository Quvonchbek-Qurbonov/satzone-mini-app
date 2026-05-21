import { api } from "@/api/client";

export type CourseSummary = {
  course_id: string;
  title: string;
  slug: string | null;
  thumbnail_url: string | null;
  instructor_name: string | null;
  mocks_count: number;
  enrolled: boolean;
};

export function fetchMyCourses() {
  return api<CourseSummary[]>("/me/courses");
}

export function fetchAdminCourses() {
  return api<CourseSummary[]>("/admin/courses");
}
