type Props = {
  value: string;
  onChange: (v: string) => void;
};

export default function GridInInput({ value, onChange }: Props) {
  return (
    <div>
      <label className="block text-sm text-hint mb-2">Your answer:</label>
      <input
        type="text"
        inputMode="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-hint/40 bg-bg px-3 py-2 text-base focus:outline-none focus:border-button"
        placeholder="Type your answer"
        autoComplete="off"
        spellCheck={false}
      />
      <div className="mt-2 text-xs text-hint">
        Type the exact answer (numbers, fractions like 3/4, decimals, words).
      </div>
    </div>
  );
}
