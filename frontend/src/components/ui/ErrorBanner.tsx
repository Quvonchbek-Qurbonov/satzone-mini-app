type Props = {
  title: string;
  message?: string;
  action?: { label: string; onClick: () => void };
};

export default function ErrorBanner({ title, message, action }: Props) {
  return (
    <div className="m-4 rounded-lg border border-danger/30 bg-danger/10 p-4 text-sm">
      <div className="font-semibold text-danger">{title}</div>
      {message && <div className="mt-1 text-text">{message}</div>}
      {action && (
        <button className="btn btn-secondary mt-3" onClick={action.onClick}>
          {action.label}
        </button>
      )}
    </div>
  );
}
