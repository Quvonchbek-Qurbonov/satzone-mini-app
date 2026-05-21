import { useQuery, useMutation } from "@tanstack/react-query";
import { useParams, useNavigate } from "react-router-dom";

import { fetchMock } from "@/api/mocks";
import { startAttempt } from "@/api/attempts";
import Spinner from "@/components/ui/Spinner";
import ErrorBanner from "@/components/ui/ErrorBanner";

export default function MockIntro() {
  const { mockId } = useParams<{ mockId: string }>();
  const navigate = useNavigate();
  const { data, isLoading, error } = useQuery({
    queryKey: ["mock", mockId],
    queryFn: () => fetchMock(mockId!),
    enabled: Boolean(mockId),
  });

  const start = useMutation({
    mutationFn: () => startAttempt(mockId!),
    onSuccess: (att) => navigate(`/attempts/${att.id}`),
  });

  if (isLoading) return <Spinner />;
  if (error || !data) return <ErrorBanner title="Could not load mock" message={(error as Error)?.message} />;

  return (
    <div className="p-4 max-w-2xl mx-auto">
      <h1 className="text-xl font-bold mb-2">{data.title}</h1>
      <div className="text-sm text-hint mb-4">
        {data.total_minutes} minutes · {data.modules.reduce((n, m) => n + m.questions.length, 0)} questions
      </div>
      {data.description && <p className="mb-4">{data.description}</p>}
      {data.instructions && (
        <div className="rounded-lg border border-hint/20 bg-secondaryBg p-4 mb-4 whitespace-pre-line text-sm">
          {data.instructions}
        </div>
      )}
      <div className="rounded-lg border border-warning/40 bg-warning/10 p-3 mb-6 text-sm">
        <strong>Note:</strong> Once you start, the timer runs server-side. You cannot pause.
      </div>
      <button
        className="btn btn-primary w-full"
        disabled={start.isPending}
        onClick={() => start.mutate()}
      >
        {start.isPending ? "Starting…" : "Start mock"}
      </button>
      {start.error && (
        <div className="mt-3 text-sm text-danger">{(start.error as Error).message}</div>
      )}
    </div>
  );
}
