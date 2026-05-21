import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";

import { fetchMyCourses } from "@/api/courses";
import Spinner from "@/components/ui/Spinner";
import ErrorBanner from "@/components/ui/ErrorBanner";
import { useAuthStore } from "@/store/authStore";

export default function Home() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["my-courses"],
    queryFn: fetchMyCourses,
  });

  if (isLoading) return <Spinner label="Loading your courses…" />;
  if (error)
    return (
      <ErrorBanner
        title="Could not load courses"
        message={(error as Error).message}
        action={{ label: "Retry", onClick: () => refetch() }}
      />
    );

  return (
    <div className="p-4 max-w-2xl mx-auto">
      <header className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Hi, {user?.full_name?.split(" ")[0]}</h1>
          <p className="text-sm text-hint">Pick a course to take a mock</p>
        </div>
        <button className="btn btn-secondary" onClick={() => navigate("/history")}>
          History
        </button>
      </header>

      {data && data.length === 0 ? (
        <div className="rounded-lg border border-dashed border-hint/40 p-6 text-center text-hint">
          You don't have any courses with mocks yet. Buy a course on the main website
          and come back here.
        </div>
      ) : (
        <ul className="space-y-3">
          {data?.map((c) => (
            <li key={c.course_id}>
              <Link
                to={`/courses/${c.course_id}/mocks`}
                className="block rounded-lg border border-hint/20 bg-secondaryBg p-4 transition hover:bg-secondaryBg/70"
              >
                <div className="flex items-center gap-3">
                  {c.thumbnail_url && (
                    // eslint-disable-next-line @next/next/no-img-element, jsx-a11y/alt-text
                    <img
                      src={c.thumbnail_url}
                      alt=""
                      className="h-14 w-14 rounded object-cover flex-shrink-0"
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold truncate">{c.title}</div>
                    {c.instructor_name && (
                      <div className="text-xs text-hint truncate">{c.instructor_name}</div>
                    )}
                  </div>
                  <div className="text-sm font-semibold text-accent flex-shrink-0">
                    {c.mocks_count} {c.mocks_count === 1 ? "mock" : "mocks"}
                  </div>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
