import { letterFor, classNames } from "@/lib/format";
import type { Option } from "@/api/mocks";

type Props = {
  options: Option[];
  selectedIds: string[];
  multi: boolean;
  onChange: (ids: string[]) => void;
};

export default function ChoiceList({ options, selectedIds, multi, onChange }: Props) {
  const toggle = (id: string) => {
    if (multi) {
      onChange(
        selectedIds.includes(id)
          ? selectedIds.filter((x) => x !== id)
          : [...selectedIds, id],
      );
    } else {
      onChange([id]);
    }
  };

  return (
    <div role="radiogroup">
      {options.map((opt, idx) => {
        const isSelected = selectedIds.includes(opt.id);
        return (
          <div
            key={opt.id}
            role={multi ? "checkbox" : "radio"}
            aria-checked={isSelected}
            tabIndex={0}
            className={classNames("choice-row", isSelected && "selected")}
            onClick={() => toggle(opt.id)}
            onKeyDown={(e) => {
              if (e.key === " " || e.key === "Enter") {
                e.preventDefault();
                toggle(opt.id);
              }
            }}
          >
            <span className="choice-letter">{letterFor(idx)}</span>
            <span className="flex-1">{opt.text}</span>
            {opt.image_url && (
              <img src={opt.image_url} alt="" className="ml-2 h-16 w-16 object-contain" />
            )}
          </div>
        );
      })}
    </div>
  );
}
