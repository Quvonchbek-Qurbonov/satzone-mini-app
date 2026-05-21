import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { fetchCourseMocks } from "@/api/mocks";
import Spinner from "@/components/ui/Spinner";
import ErrorBanner from "@/components/ui/ErrorBanner";

export default function CourseMocks() {
  const { courseId } = useParams<{ courseId: string }>();
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["course-mocks", courseId],
    queryFn: () => fetchCourseMocks(courseId!),
    enabled: Boolean(courseId),
  });

  if (isLoading) return <Spinner />;
  if (error)
    return (
      <ErrorBanner
        title="Could not load mocks"
        message={(error as Error).message}
        action={{ label: "Retry", onClick: () => refetch() }}
      />
    );

  return (
    <div className="p-4 max-w-2xl mx-auto">
      <h1 className="text-lg font-bold mb-3">Mocks</h1>
      <ul className="space-y-2">
        {data?.map((m) => (
          <li key={m.id}>
            <Link
              to={`/mocks/${m.id}`}
              className="block rounded-lg border border-hint/20 bg-secondaryBg p-4 hover:opacity-90"
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="font-semibold">{m.title}</div>
                  <div className="text-xs text-hint">
                    {m.kind === "sat_rw" ? "Reading & Writing" : m.kind === "sat_math" ? "Math" : "Mock"} ·{" "}
                    {m.total_minutes} min · {m.questions_count} questions
                  </div>
                </div>
                <span className="text-xs text-accent font-semibold">Start</span>
              </div>
            </Link>
          </li>
        ))}
      </ul>
      {data && data.length === 0 && (
        <div className="text-center text-hint mt-8">No mocks published yet for this course.</div>
      )}
    </div>
  );
}
