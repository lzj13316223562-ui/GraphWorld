import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Shell } from "../components/layout/Shell";
import { SceneListPage } from "../features/scene-browser/SceneListPage";
import { SceneDetailPage } from "../features/scene-browser/SceneDetailPage";
import { RunConfigPage } from "../features/run-config/RunConfigPage";
import { RunDetailPage } from "../features/run-monitor/RunDetailPage";
import { ReplayPage } from "../features/replay/ReplayPage";

export function App() {
  return (
    <BrowserRouter>
      <Shell>
        <Routes>
          <Route path="/" element={<Navigate to="/scenes" replace />} />
          <Route path="/scenes" element={<SceneListPage />} />
          <Route path="/scenes/:sceneId" element={<SceneDetailPage />} />
          <Route path="/runs/new" element={<RunConfigPage />} />
          <Route path="/runs/:runId" element={<RunDetailPage />} />
          <Route path="/runs/:runId/replay" element={<ReplayPage />} />
          <Route path="*" element={<Navigate to="/scenes" replace />} />
        </Routes>
      </Shell>
    </BrowserRouter>
  );
}
