import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { fetchAttempt } from "@/api/attempts";
import Spinner from "@/components/ui/Spinner";
import ErrorBanner from "@/components/ui/ErrorBanner";

export default function MockResults() {
  const { attemptId } = useParams<{ attemptId: string }>();
  const { data, isLoading, error } = useQuery({
    queryKey: ["attempt", attemptId],
    queryFn: () => fetchAttempt(attemptId!),
    enabled: Boolean(attemptId),
  });

  if (isLoading) return <Spinner />;
  if (error || !data)
    return <ErrorBanner title="Could not load results" message={(error as Error)?.message} />;

  const totalQuestions = data.modules.reduce((n, m) => n + m.questions.length, 0);
  const correctCount = data.answers.filter((a) => a.is_correct).length;
  const badgeClass = data.passed ? "bg-success" : "bg-danger";

  return (
    <div className="p-4 max-w-2xl mx-auto">
      <h1 className="text-xl font-bold mb-1">{data.mock_title}</h1>
      <p className="text-sm text-hint mb-4">Results</p>

      <div className="rounded-lg bg-gradient-to-br from-accent to-accent/80 text-white p-6 mb-5 text-center">
        <div className="text-xs uppercase tracking-widest opacity-90">Score</div>
        <div className="text-5xl font-extrabold mt-1">{data.score_percent}%</div>
        <div className="text-sm opacity-90 mt-1">
          {data.raw_score} / {data.total_points} points · {correctCount}/{totalQuestions} correct
        </div>
        <span
          className={`inline-block mt-3 px-3 py-1 rounded-full text-xs font-semibold ${badgeClass}`}
        >
          {data.passed ? "Passed" : "Did not pass"}
        </span>
      </div>

      <div className="rounded-lg border border-hint/20 p-4 mb-4 text-sm">
        <div className="flex justify-between mb-1">
          <span className="text-hint">Time spent</span>
          <span className="font-semibold">
            {Math.floor(data.time_spent_seconds / 60)} min {data.time_spent_seconds % 60} s
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-hint">Pass threshold</span>
          <span className="font-semibold">{data.pass_percent}%</span>
        </div>
      </div>

      <div className="space-y-2">
        <h2 className="text-sm font-semibold text-hint uppercase tracking-wider mt-4">By question</h2>
        {data.modules.flatMap((m) =>
          m.questions.map((q, i) => {
            const ans = data.answers.find((a) => a.question_id === q.id);
            const ok = ans?.is_correct;
            return (
              <div
                key={q.id}
                className={
                  "rounded-md border p-3 text-sm flex items-center justify-between " +
                  (ok ? "border-success/40 bg-success/10" : "border-danger/40 bg-danger/10")
                }
              >
                <div className="flex-1 min-w-0 truncate">
                  Q{i + 1}: {q.prompt.slice(0, 80)}
                </div>
                <span className={"font-bold ml-3 " + (ok ? "text-success" : "text-danger")}>
                  {ok ? "✓" : "✗"}
                </span>
              </div>
            );
          }),
        )}
      </div>

      <Link to="/home" className="btn btn-primary w-full mt-6">
        Back to home
      </Link>
    </div>
  );
}
