import { useMutation, useQuery } from "@tanstack/react-query";
import { Play } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { listScenes, listSceneVersions } from "../../api/scenes";
import { createRun } from "../../api/runs";
import type { ControlMode, VisibilityMode } from "../../types/api";

export function RunConfigPage() {
  const navigate = useNavigate();
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
  const activeVersionId = sceneVersionId || versions.data?.[0]?.id || "";
  const selectedSummary = useMemo(
    () => versions.data?.find((version) => version.id === activeVersionId)?.graph_summary ?? {},
    [versions.data, activeVersionId],
  );

  const mutation = useMutation({
    mutationFn: createRun,
    onSuccess: (state) => navigate(`/runs/${state.run.id}`),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!activeVersionId) {
      return;
    }
    mutation.mutate({
      scene_version_id: activeVersionId,
      control_mode: controlMode,
      visibility_mode: visibilityMode,
      task_id: "maintain_order",
      agent_model: agentModel || null,
      max_steps: maxSteps,
      config: { use_llm: useLlm },
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
        <label>
          <span>Control Mode</span>
          <select value={controlMode} onChange={(event) => setControlMode(event.target.value as ControlMode)}>
            <option value="human">human</option>
            <option value="agent">agent</option>
            <option value="npc_only">npc_only</option>
          </select>
        </label>
        <label>
          <span>Visibility Mode</span>
          <select value={visibilityMode} onChange={(event) => setVisibilityMode(event.target.value as VisibilityMode)}>
            <option value="fog_of_war">fog_of_war</option>
            <option value="room">room</option>
            <option value="full">full</option>
          </select>
        </label>
        <label>
          <span>Max Steps</span>
          <input type="number" min={1} max={1600} value={maxSteps} onChange={(event) => setMaxSteps(Number(event.target.value))} />
        </label>
        <label>
          <span>Agent Model</span>
          <input value={agentModel} onChange={(event) => setAgentModel(event.target.value)} placeholder="fallback" />
        </label>
        <label className="check-row">
          <input type="checkbox" checked={useLlm} onChange={(event) => setUseLlm(event.target.checked)} />
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
