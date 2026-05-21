import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { fetchAdminCourses } from "@/api/courses";
import { createMock } from "@/api/admin";
import { fetchAdminMocks } from "@/api/admin";
import Spinner from "@/components/ui/Spinner";
import ErrorBanner from "@/components/ui/ErrorBanner";

export default function AdminHome() {
  const qc = useQueryClient();
  const [expanded, setExpanded] = useState<string | null>(null);
  const { data: courses, isLoading, error } = useQuery({
    queryKey: ["admin-courses"],
    queryFn: fetchAdminCourses,
  });

  if (isLoading) return <Spinner />;
  if (error) return <ErrorBanner title="Cannot load courses" message={(error as Error).message} />;

  return (
    <div className="p-4 max-w-2xl mx-auto">
      <header className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-bold">Admin · Mocks</h1>
      </header>
      <ul className="space-y-3">
        {courses?.map((c) => (
          <li key={c.course_id} className="rounded-lg border border-hint/20">
            <button
              className="w-full p-4 text-left flex items-center justify-between gap-3"
              onClick={() => setExpanded((cur) => (cur === c.course_id ? null : c.course_id))}
            >
              <div className="min-w-0">
                <div className="font-semibold truncate">{c.title}</div>
                <div className="text-xs text-hint truncate">{c.instructor_name ?? ""}</div>
              </div>
              <div className="text-xs text-accent flex-shrink-0">
                {c.mocks_count} {c.mocks_count === 1 ? "mock" : "mocks"} ›
              </div>
            </button>
            {expanded === c.course_id && (
              <CourseMockList
                courseId={c.course_id}
                courseTitle={c.title}
                onCreated={() => {
                  qc.invalidateQueries({ queryKey: ["admin-courses"] });
                  qc.invalidateQueries({ queryKey: ["admin-mocks", c.course_id] });
                }}
              />
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function CourseMockList({
  courseId,
  courseTitle,
  onCreated,
}: {
  courseId: string;
  courseTitle: string;
  onCreated: () => void;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["admin-mocks", courseId],
    queryFn: () => fetchAdminMocks(courseId),
  });
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState<"sat_rw" | "sat_math" | "generic">("sat_rw");
  const [totalMinutes, setTotalMinutes] = useState(64);

  const create = useMutation({
    mutationFn: () =>
      createMock({
        course_id: courseId,
        title: title.trim() || `${courseTitle} mock`,
        kind,
        total_minutes: totalMinutes,
        pass_percent: 60,
      }),
    onSuccess: () => {
      setTitle("");
      onCreated();
    },
  });

  return (
    <div className="border-t border-hint/10 p-4 space-y-3 bg-secondaryBg/40">
      <div className="space-y-2">
        {isLoading ? (
          <Spinner />
        ) : (
          data?.map((m) => (
            <Link
              key={m.id}
              to={`/admin/mocks/${m.id}`}
              className="block rounded-md border border-hint/20 p-3 bg-bg hover:opacity-90"
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="font-semibold text-sm">{m.title}</div>
                  <div className="text-xs text-hint">
                    {m.kind} · {m.total_minutes} min ·{" "}
                    <span className={m.status === "published" ? "text-success" : "text-warning"}>
                      {m.status}
                    </span>
                  </div>
                </div>
                <span className="text-xs text-accent">Edit</span>
              </div>
            </Link>
          ))
        )}
      </div>

      <div className="rounded-md border border-dashed border-hint/40 p-3 bg-bg">
        <div className="text-sm font-semibold mb-2">Create new mock</div>
        <input
          className="w-full mb-2 rounded border border-hint/30 px-2 py-1 text-sm bg-bg"
          placeholder="Mock title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <div className="flex gap-2 mb-2">
          <select
            className="flex-1 rounded border border-hint/30 px-2 py-1 text-sm bg-bg"
            value={kind}
            onChange={(e) => setKind(e.target.value as typeof kind)}
          >
            <option value="sat_rw">SAT Reading & Writing</option>
            <option value="sat_math">SAT Math</option>
            <option value="generic">Generic</option>
          </select>
          <input
            className="w-24 rounded border border-hint/30 px-2 py-1 text-sm bg-bg"
            type="number"
            value={totalMinutes}
            min={1}
            max={600}
            onChange={(e) => setTotalMinutes(Number(e.target.value))}
          />
        </div>
        <button
          className="btn btn-primary w-full"
          onClick={() => create.mutate()}
          disabled={create.isPending}
        >
          {create.isPending ? "Creating…" : "Create"}
        </button>
        {create.error && (
          <div className="text-xs text-danger mt-2">{(create.error as Error).message}</div>
        )}
      </div>
    </div>
  );
}
