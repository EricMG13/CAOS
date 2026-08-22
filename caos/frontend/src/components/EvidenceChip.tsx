type Props = {
  evidenceId: string;
  linkedId: string;
  onOpen: (evidenceId: string) => void;
  onPreview: (evidenceId: string) => void;
  onPreviewEnd: () => void;
  warning?: boolean;
};

export default function EvidenceChip({ evidenceId, linkedId, onOpen, onPreview, onPreviewEnd, warning = false }: Props) {
  const linked = linkedId === evidenceId;
  return <button
    type="button"
    className={`evidence-chip${warning ? " warning" : ""}${linked ? " is-linked" : ""}`}
    data-evidence-id={evidenceId}
    aria-label={`Open evidence ${evidenceId}${warning ? ", QA concern" : ""}`}
    onBlur={onPreviewEnd}
    onClick={() => onOpen(evidenceId)}
    onFocus={() => onPreview(evidenceId)}
    onMouseEnter={() => onPreview(evidenceId)}
    onMouseLeave={onPreviewEnd}
  >
    {warning && <span aria-hidden="true">▲</span>}
    {evidenceId}
  </button>;
}
