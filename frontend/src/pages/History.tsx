import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { fetchHistory } from "@/api/attempts";
import Spinner from "@/components/ui/Spinner";
import ErrorBanner from "@/components/ui/ErrorBanner";
import { formatDate } from "@/lib/format";

export default function History() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["history"],
    queryFn: fetchHistory,
  });
  if (isLoading) return <Spinner />;
  if (error) return <ErrorBanner title="Could not load history" message={(error as Error).message} />;

  return (
    <div className="p-4 max-w-2xl mx-auto">
      <h1 className="text-xl font-bold mb-3">History</h1>
      {data && data.length === 0 ? (
        <div className="text-hint text-center mt-8">No attempts yet.</div>
      ) : (
        <ul className="space-y-2">
          {data?.map((a) => (
            <li key={a.id}>
              <Link
                to={a.submitted_at ? `/attempts/${a.id}/results` : `/attempts/${a.id}`}
                className="block rounded-lg border border-hint/20 bg-secondaryBg p-3 hover:opacity-90"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="font-semibold truncate">{a.mock_title}</div>
                    <div className="text-xs text-hint">{formatDate(a.started_at)}</div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className="text-lg font-bold">
                      {a.submitted_at ? `${a.score_percent}%` : "In progress"}
                    </div>
                    {a.submitted_at && (
                      <div
                        className={
                          "text-xs " + (a.passed ? "text-success" : "text-danger")
                        }
                      >
                        {a.passed ? "Passed" : "Failed"}
                      </div>
                    )}
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
