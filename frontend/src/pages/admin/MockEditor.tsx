import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";

import {
  createModule,
  createPassage,
  createQuestion,
  deleteModule,
  deletePassage,
  deleteQuestion,
  fetchAdminMock,
  patchMock,
  patchModule,
  patchPassage,
  patchQuestion,
  uploadQuestionImage,
  type AdminMock,
  type AdminModule,
  type AdminQuestion,
  type QuestionWritePayload,
} from "@/api/admin";
import Spinner from "@/components/ui/Spinner";
import ErrorBanner from "@/components/ui/ErrorBanner";
import type { QuestionType } from "@/api/mocks";

export default function MockEditor() {
  const { mockId } = useParams<{ mockId: string }>();
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-mock", mockId],
    queryFn: () => fetchAdminMock(mockId!),
    enabled: Boolean(mockId),
  });

  const refetch = () => qc.invalidateQueries({ queryKey: ["admin-mock", mockId] });

  if (isLoading) return <Spinner />;
  if (error || !data) return <ErrorBanner title="Cannot load mock" message={(error as Error)?.message} />;

  return (
    <div className="p-4 max-w-3xl mx-auto pb-24">
      <Link to="/admin" className="text-sm text-hint hover:text-text">
        ← All courses
      </Link>
      <MockMetaCard mock={data} onSaved={refetch} />
      <ModuleListCard mock={data} onChanged={refetch} />
    </div>
  );
}

function MockMetaCard({ mock, onSaved }: { mock: AdminMock; onSaved: () => void }) {
  const qc = useQueryClient();
  const [title, setTitle] = useState(mock.title);
  const [desc, setDesc] = useState(mock.description ?? "");
  const [totalMinutes, setTotalMinutes] = useState(mock.total_minutes);
  const [passPercent, setPassPercent] = useState(mock.pass_percent);

  const save = useMutation({
    mutationFn: () =>
      patchMock(mock.id, {
        title,
        description: desc,
        total_minutes: totalMinutes,
        pass_percent: passPercent,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-mock", mock.id] });
      onSaved();
    },
  });

  const publish = useMutation({
    mutationFn: () =>
      patchMock(mock.id, {
        status: mock.status === "published" ? "draft" : "published",
      }),
    onSuccess: onSaved,
  });

  return (
    <section className="mt-3 rounded-lg border border-hint/20 p-4 bg-secondaryBg/40">
      <div className="flex items-center justify-between mb-3 gap-2">
        <h1 className="text-lg font-bold flex-1 min-w-0 truncate">{mock.title}</h1>
        <span
          className={
            "text-xs px-2 py-1 rounded-full font-semibold " +
            (mock.status === "published" ? "bg-success text-white" : "bg-warning/30 text-warning")
          }
        >
          {mock.status}
        </span>
      </div>
      <label className="block text-xs text-hint mb-1">Title</label>
      <input
        className="w-full mb-2 rounded border border-hint/30 px-2 py-1 text-sm bg-bg"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <label className="block text-xs text-hint mb-1">Description</label>
      <textarea
        className="w-full mb-2 rounded border border-hint/30 px-2 py-1 text-sm bg-bg"
        rows={2}
        value={desc}
        onChange={(e) => setDesc(e.target.value)}
      />
      <div className="flex gap-2 mb-3">
        <div className="flex-1">
          <label className="block text-xs text-hint mb-1">Total minutes</label>
          <input
            className="w-full rounded border border-hint/30 px-2 py-1 text-sm bg-bg"
            type="number"
            value={totalMinutes}
            onChange={(e) => setTotalMinutes(Number(e.target.value))}
          />
        </div>
        <div className="flex-1">
          <label className="block text-xs text-hint mb-1">Pass %</label>
          <input
            className="w-full rounded border border-hint/30 px-2 py-1 text-sm bg-bg"
            type="number"
            value={passPercent}
            min={0}
            max={100}
            onChange={(e) => setPassPercent(Number(e.target.value))}
          />
        </div>
      </div>
      <div className="flex gap-2">
        <button className="btn btn-secondary flex-1" disabled={save.isPending} onClick={() => save.mutate()}>
          {save.isPending ? "Saving…" : "Save"}
        </button>
        <button
          className={mock.status === "published" ? "btn btn-danger flex-1" : "btn btn-primary flex-1"}
          disabled={publish.isPending}
          onClick={() => publish.mutate()}
        >
          {mock.status === "published" ? "Unpublish" : "Publish"}
        </button>
      </div>
    </section>
  );
}

function ModuleListCard({ mock, onChanged }: { mock: AdminMock; onChanged: () => void }) {
  const create = useMutation({
    mutationFn: () =>
      createModule(mock.id, {
        title: `Module ${mock.modules.length + 1}`,
        time_limit_minutes: Math.max(1, Math.floor(mock.total_minutes / 2)),
      }),
    onSuccess: onChanged,
  });

  return (
    <section className="mt-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">Modules</h2>
        <button className="btn btn-secondary" onClick={() => create.mutate()} disabled={create.isPending}>
          + Module
        </button>
      </div>
      {mock.modules.map((m, idx) => (
        <ModuleCard key={m.id} module={m} index={idx} onChanged={onChanged} />
      ))}
    </section>
  );
}

function ModuleCard({
  module,
  index,
  onChanged,
}: {
  module: AdminModule;
  index: number;
  onChanged: () => void;
}) {
  const [title, setTitle] = useState(module.title);
  const [timeMins, setTimeMins] = useState(module.time_limit_minutes);
  const save = useMutation({
    mutationFn: () => patchModule(module.id, { title, time_limit_minutes: timeMins }),
    onSuccess: onChanged,
  });
  const remove = useMutation({
    mutationFn: () => deleteModule(module.id),
    onSuccess: onChanged,
  });
  const newPassage = useMutation({
    mutationFn: () => createPassage(module.id, { body_html: "<p>New passage</p>" }),
    onSuccess: onChanged,
  });
  const newQuestion = useMutation({
    mutationFn: () =>
      createQuestion(module.id, {
        type: "single_choice",
        prompt: "New question",
        points: 1,
        options: [
          { text: "A", is_correct: true },
          { text: "B", is_correct: false },
          { text: "C", is_correct: false },
          { text: "D", is_correct: false },
        ],
      }),
    onSuccess: onChanged,
  });

  return (
    <article className="rounded-lg border border-hint/20 p-4 bg-bg">
      <div className="flex items-center gap-2 mb-3">
        <div className="text-xs text-hint">Module {index + 1}</div>
      </div>
      <div className="flex gap-2 mb-3">
        <input
          className="flex-1 rounded border border-hint/30 px-2 py-1 text-sm bg-bg"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <input
          className="w-20 rounded border border-hint/30 px-2 py-1 text-sm bg-bg"
          type="number"
          value={timeMins}
          onChange={(e) => setTimeMins(Number(e.target.value))}
          title="Minutes"
        />
        <button className="btn btn-secondary" onClick={() => save.mutate()} disabled={save.isPending}>
          Save
        </button>
        <button className="btn btn-danger" onClick={() => remove.mutate()} disabled={remove.isPending}>
          ✕
        </button>
      </div>

      <h3 className="text-sm font-semibold mt-3 mb-2">Passages</h3>
      <div className="space-y-2">
        {module.passages.map((p) => (
          <PassageRow key={p.id} passage={p} onChanged={onChanged} />
        ))}
        <button className="btn btn-secondary w-full" onClick={() => newPassage.mutate()} disabled={newPassage.isPending}>
          + Passage
        </button>
      </div>

      <h3 className="text-sm font-semibold mt-4 mb-2">Questions</h3>
      <div className="space-y-2">
        {module.questions.map((q, qi) => (
          <QuestionRow
            key={q.id}
            question={q}
            indexInModule={qi}
            module={module}
            onChanged={onChanged}
          />
        ))}
        <button className="btn btn-secondary w-full" onClick={() => newQuestion.mutate()} disabled={newQuestion.isPending}>
          + Question
        </button>
      </div>
    </article>
  );
}

function PassageRow({
  passage,
  onChanged,
}: {
  passage: AdminModule["passages"][number];
  onChanged: () => void;
}) {
  const [title, setTitle] = useState(passage.title ?? "");
  const [subtitle, setSubtitle] = useState(passage.subtitle ?? "");
  const [bodyHtml, setBodyHtml] = useState(passage.body_html);

  const save = useMutation({
    mutationFn: () =>
      patchPassage(passage.id, { title: title || null, subtitle: subtitle || null, body_html: bodyHtml }),
    onSuccess: onChanged,
  });
  const remove = useMutation({
    mutationFn: () => deletePassage(passage.id),
    onSuccess: onChanged,
  });

  return (
    <div className="rounded-md border border-hint/20 p-3 space-y-2">
      <input
        className="w-full rounded border border-hint/30 px-2 py-1 text-sm bg-bg"
        placeholder="Title (optional)"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <input
        className="w-full rounded border border-hint/30 px-2 py-1 text-sm bg-bg"
        placeholder="Subtitle (optional)"
        value={subtitle}
        onChange={(e) => setSubtitle(e.target.value)}
      />
      <textarea
        className="w-full rounded border border-hint/30 px-2 py-1 text-xs font-mono bg-bg"
        rows={6}
        value={bodyHtml}
        onChange={(e) => setBodyHtml(e.target.value)}
      />
      <div className="flex gap-2">
        <button className="btn btn-secondary flex-1" disabled={save.isPending} onClick={() => save.mutate()}>
          Save passage
        </button>
        <button className="btn btn-danger" disabled={remove.isPending} onClick={() => remove.mutate()}>
          ✕
        </button>
      </div>
    </div>
  );
}

function QuestionRow({
  question,
  indexInModule,
  module,
  onChanged,
}: {
  question: AdminQuestion;
  indexInModule: number;
  module: AdminModule;
  onChanged: () => void;
}) {
  const [prompt, setPrompt] = useState(question.prompt);
  const [explanation, setExplanation] = useState(question.explanation ?? "");
  const [type, setType] = useState<QuestionType>(question.type);
  const [passageId, setPassageId] = useState<string | "">(question.passage_id ?? "");
  const [options, setOptions] = useState(question.options.map((o) => ({ ...o })));
  const [expected, setExpected] = useState((question.expected_answers ?? []).join("\n"));
  const [points, setPoints] = useState(question.points);

  const save = useMutation({
    mutationFn: () => {
      const payload: Partial<QuestionWritePayload> = {
        prompt,
        explanation: explanation || undefined,
        points,
        passage_id: passageId || null,
      };
      if (type === "single_choice" || type === "multi_choice") {
        payload.options = options.map((o) => ({ text: o.text, is_correct: o.is_correct }));
      }
      if (type === "grid_in" || type === "short_answer") {
        payload.expected_answers = expected
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean);
      }
      return patchQuestion(question.id, payload);
    },
    onSuccess: onChanged,
  });
  const remove = useMutation({
    mutationFn: () => deleteQuestion(question.id),
    onSuccess: onChanged,
  });

  const onImageChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    await uploadQuestionImage(question.id, f);
    onChanged();
  };

  const updateOption = (i: number, patch: Partial<{ text: string; is_correct: boolean }>) => {
    setOptions((prev) => {
      const next = prev.map((o) => ({ ...o }));
      next[i] = { ...next[i], ...patch };
      if (patch.is_correct && type === "single_choice") {
        next.forEach((o, idx) => (o.is_correct = idx === i));
      }
      return next;
    });
  };

  const addOption = () =>
    setOptions((prev) => [
      ...prev,
      { id: crypto.randomUUID(), text: "", order: prev.length, image_url: null, is_correct: false },
    ]);

  return (
    <div className="rounded-md border border-hint/20 p-3 space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-xs font-bold text-hint">Q{indexInModule + 1}</span>
        <select
          className="rounded border border-hint/30 px-2 py-1 text-xs bg-bg"
          value={type}
          onChange={(e) => setType(e.target.value as QuestionType)}
        >
          <option value="single_choice">Single choice</option>
          <option value="multi_choice">Multi choice</option>
          <option value="grid_in">Grid-in</option>
          <option value="short_answer">Short answer</option>
        </select>
        <select
          className="rounded border border-hint/30 px-2 py-1 text-xs bg-bg flex-1"
          value={passageId}
          onChange={(e) => setPassageId(e.target.value)}
        >
          <option value="">No passage</option>
          {module.passages.map((p, i) => (
            <option key={p.id} value={p.id}>
              Passage {i + 1}
              {p.title ? ` · ${p.title}` : ""}
            </option>
          ))}
        </select>
        <input
          className="w-14 rounded border border-hint/30 px-2 py-1 text-xs bg-bg"
          type="number"
          value={points}
          onChange={(e) => setPoints(Number(e.target.value))}
          title="Points"
        />
      </div>
      <textarea
        className="w-full rounded border border-hint/30 px-2 py-1 text-sm bg-bg"
        rows={3}
        placeholder="Prompt (supports $math$)"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
      />
      <textarea
        className="w-full rounded border border-hint/30 px-2 py-1 text-xs bg-bg"
        rows={2}
        placeholder="Explanation (shown after submission)"
        value={explanation}
        onChange={(e) => setExplanation(e.target.value)}
      />
      <div>
        <label className="text-xs text-hint">Image</label>
        <input type="file" accept="image/*" onChange={onImageChange} className="text-xs block" />
        {question.image_url && (
          <img src={question.image_url} alt="" className="mt-1 max-h-24 rounded border border-hint/20" />
        )}
      </div>

      {(type === "single_choice" || type === "multi_choice") && (
        <div className="space-y-1">
          {options.map((o, i) => (
            <div key={o.id} className="flex gap-2 items-center">
              <input
                type={type === "single_choice" ? "radio" : "checkbox"}
                name={`correct-${question.id}`}
                checked={o.is_correct}
                onChange={() => updateOption(i, { is_correct: !o.is_correct })}
              />
              <input
                className="flex-1 rounded border border-hint/30 px-2 py-1 text-sm bg-bg"
                value={o.text}
                onChange={(e) => updateOption(i, { text: e.target.value })}
                placeholder={`Option ${String.fromCharCode(65 + i)}`}
              />
              <button
                className="text-hint hover:text-danger px-2"
                onClick={() => setOptions((prev) => prev.filter((_, j) => j !== i))}
                aria-label="Remove option"
              >
                ✕
              </button>
            </div>
          ))}
          <button className="btn btn-secondary text-xs" onClick={addOption}>
            + Option
          </button>
        </div>
      )}

      {(type === "grid_in" || type === "short_answer") && (
        <div>
          <label className="text-xs text-hint">
            Accepted answers (one per line, case-insensitive)
          </label>
          <textarea
            className="w-full rounded border border-hint/30 px-2 py-1 text-sm bg-bg"
            rows={3}
            value={expected}
            onChange={(e) => setExpected(e.target.value)}
            placeholder="e.g. 3/4&#10;0.75"
          />
        </div>
      )}

      <div className="flex gap-2">
        <button className="btn btn-primary flex-1" disabled={save.isPending} onClick={() => save.mutate()}>
          {save.isPending ? "Saving…" : "Save question"}
        </button>
        <button className="btn btn-danger" disabled={remove.isPending} onClick={() => remove.mutate()}>
          ✕
        </button>
      </div>
      {save.error && <div className="text-xs text-danger">{(save.error as Error).message}</div>}
    </div>
  );
}
