import { useEffect, useRef } from "react";
import type { Passage } from "@/api/mocks";

type Props = {
  passage: Passage | null;
};

export default function PassagePane({ passage }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Scroll to top on passage change.
    ref.current?.scrollTo({ top: 0, behavior: "smooth" });
  }, [passage?.id]);

  if (!passage) {
    return (
      <div className="player-pane player-pane-left text-hint text-sm italic">
        No passage for this question.
      </div>
    );
  }

  return (
    <section ref={ref} className="player-pane player-pane-left">
      {passage.title && <div className="passage-title">{passage.title}</div>}
      {passage.subtitle && <div className="passage-sub">{passage.subtitle}</div>}
      <div className="passage-body" dangerouslySetInnerHTML={{ __html: passage.body_html }} />
    </section>
  );
}
