import { useMutation, useQuery } from "@tanstack/react-query";
import { Play } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../../app/auth";
import { listScenes, listSceneVersions } from "../../api/scenes";
import { createRun } from "../../api/runs";
import type { ControlMode, VisibilityMode } from "../../types/api";

export function RunConfigPage() {
  const navigate = useNavigate();
  const auth = useAuth();
  const [searchParams] = useSearchParams();
  const sceneVersionParam = searchParams.get("sceneVersionId") ?? "";
  const inferredSceneId = sceneVersionParam.split("__v")[0] || "";
  const scenes = useQuery({ queryKey: ["scenes"], queryFn: listScenes });
  const [sceneId, setSceneId] = useState(inferredSceneId);
  const activeSceneId = sceneId || scenes.data?.[0]?.id || "";
  const versions = useQuery({
    queryKey: ["scene-versions", activeSceneId],
    queryFn: () => listSceneVersions(activeSceneId),
    enabled: Boolean(activeSceneId),
  });
  const [sceneVersionId, setSceneVersionId] = useState(sceneVersionParam);
  const [controlMode, setControlMode] = useState<ControlMode>("human");
  const [visibilityMode, setVisibilityMode] = useState<VisibilityMode>("fog_of_war");
  const [maxSteps, setMaxSteps] = useState(20);
  const [agentModel, setAgentModel] = useState("");
  const [useLlm, setUseLlm] = useState(false);
  const isUserMode = !auth.isAdmin;
  const activeVersionId = sceneVersionId || versions.data?.[0]?.id || "";
  const selectedSummary = useMemo(
    () => versions.data?.find((version) => version.id === activeVersionId)?.graph_summary ?? {},
    [versions.data, activeVersionId],
  );

  const mutation = useMutation({
    mutationFn: createRun,
    onSuccess: (state) => navigate(`/runs/${state.run.id}`),
  });

  useEffect(() => {
    if (!isUserMode) {
      return;
    }
    setVisibilityMode("fog_of_war");
    if (controlMode === "agent") {
      setControlMode("human");
    }
    setUseLlm(false);
  }, [controlMode, isUserMode]);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!activeVersionId) {
      return;
    }
    const safeControlMode = isUserMode && controlMode === "agent" ? "human" : controlMode;
    const safeVisibilityMode = isUserMode ? "fog_of_war" : visibilityMode;
    mutation.mutate({
      scene_version_id: activeVersionId,
      control_mode: safeControlMode,
      visibility_mode: safeVisibilityMode,
      task_id: "maintain_order",
      agent_model: safeControlMode === "agent" ? agentModel || null : null,
      max_steps: maxSteps,
      config: { use_llm: safeControlMode === "agent" && useLlm },
    });
  }

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Run Configuration</p>
          <h1>New Run</h1>
        </div>
      </header>

      <form className="form-grid" onSubmit={submit}>
        <div className="mode-banner">
          <strong>{auth.isAdmin ? "Admin workspace" : "User workspace"}</strong>
          <span>{auth.isAdmin ? "All control and visibility modes are available." : "Runs are limited to fog_of_war and non-agent control."}</span>
        </div>
        <label>
          <span>Scene</span>
          <select
            value={activeSceneId}
            onChange={(event) => {
              setSceneId(event.target.value);
              setSceneVersionId("");
            }}
          >
            {scenes.data?.map((scene) => (
              <option key={scene.id} value={scene.id}>
                {scene.name || scene.id}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Scene Version</span>
          <select value={activeVersionId} onChange={(event) => setSceneVersionId(event.target.value)}>
            {versions.data?.map((version) => (
              <option key={version.id} value={version.id}>
                v{version.version} · {version.id}
              </option>
            ))}
          </select>
        </label>
        <fieldset className="form-section">
          <legend>Control Mode</legend>
          <div className="option-group">
            {(["human", "agent", "npc_only"] as ControlMode[]).map((mode) => {
              const disabled = isUserMode && mode === "agent";
              return (
                <button
                  key={mode}
                  className={controlMode === mode ? "option-button selected" : "option-button"}
                  type="button"
                  disabled={disabled}
                  title={disabled ? "Agent control is only available in admin mode." : mode}
                  onClick={() => setControlMode(mode)}
                >
                  <span>{mode}</span>
                </button>
              );
            })}
          </div>
        </fieldset>
        <fieldset className="form-section">
          <legend>Visibility Mode</legend>
          <div className="option-group">
            {(["fog_of_war", "room", "full"] as VisibilityMode[]).map((mode) => {
              const disabled = isUserMode && mode !== "fog_of_war";
              return (
                <button
                  key={mode}
                  className={visibilityMode === mode ? "option-button selected" : "option-button"}
                  type="button"
                  disabled={disabled}
                  title={disabled ? "User mode can only use fog_of_war." : mode}
                  onClick={() => setVisibilityMode(mode)}
                >
                  <span>{mode}</span>
                </button>
              );
            })}
          </div>
        </fieldset>
        <label>
          <span>Max Steps</span>
          <input type="number" min={1} max={1600} value={maxSteps} onChange={(event) => setMaxSteps(Number(event.target.value))} />
        </label>
        <label>
          <span>Agent Model</span>
          <input
            value={agentModel}
            disabled={isUserMode || controlMode !== "agent"}
            onChange={(event) => setAgentModel(event.target.value)}
            placeholder="fallback"
          />
        </label>
        <label className="check-row">
          <input
            type="checkbox"
            checked={useLlm}
            disabled={isUserMode || controlMode !== "agent"}
            onChange={(event) => setUseLlm(event.target.checked)}
          />
          <span>Use LLM</span>
        </label>
        <div className="summary-strip">
          <span>{String(selectedSummary.node_count ?? 0)} nodes</span>
          <span>{String(selectedSummary.edge_count ?? 0)} edges</span>
          <span>{String(selectedSummary.room_count ?? 0)} rooms</span>
        </div>
        {mutation.error && <div className="error-panel">{mutation.error.message}</div>}
        <button className="button primary submit-button" type="submit" disabled={!activeVersionId || mutation.isPending}>
          <Play size={16} aria-hidden />
          Start Run
        </button>
      </form>
    </section>
  );
}
