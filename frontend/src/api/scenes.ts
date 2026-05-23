import { requestJson } from "./client";
import type { SceneGraphResponse, SceneRead, SceneVersionRead } from "../types/api";

export function listScenes() {
  return requestJson<SceneRead[]>("/scenes");
}

export function getScene(sceneId: string) {
  return requestJson<SceneRead>(`/scenes/${sceneId}`);
}

export function listSceneVersions(sceneId: string) {
  return requestJson<SceneVersionRead[]>(`/scenes/${sceneId}/versions`);
}

export function getSceneGraph(sceneVersionId: string) {
  return requestJson<SceneGraphResponse>(`/scene-versions/${sceneVersionId}/graph`);
}
