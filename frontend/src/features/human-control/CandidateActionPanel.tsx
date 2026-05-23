import { MousePointerClick } from "lucide-react";
import type { CandidateAction } from "../../types/api";

interface CandidateActionPanelProps {
  actions: CandidateAction[];
  disabled?: boolean;
  onSelect: (actionId: string) => void;
}

export function CandidateActionPanel({ actions, disabled = false, onSelect }: CandidateActionPanelProps) {
  if (!actions.length) {
    return <div className="empty-panel">No candidate actions.</div>;
  }

  return (
    <div className="action-list">
      {actions.map((action) => (
        <button
          key={action.action_id}
          type="button"
          className="action-row"
          disabled={disabled || !action.legal}
          title={action.preview || action.reason}
          onClick={() => onSelect(action.action_id)}
        >
          <MousePointerClick size={16} aria-hidden />
          <span className="action-main">
            <strong>{action.action_type}</strong>
            <span>{action.target_id || action.object_id || action.reason}</span>
          </span>
        </button>
      ))}
    </div>
  );
}
