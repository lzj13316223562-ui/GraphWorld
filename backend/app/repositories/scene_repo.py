from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from backend.app.db.models import Scene, SceneEdge, SceneNode, SceneVersion
from backend.app.runtime.scene_importer import ImportedScene


class SceneRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_scenes(self) -> list[Scene]:
        statement: Select[tuple[Scene]] = select(Scene).order_by(Scene.created_at.desc(), Scene.id.asc())
        return list(self.db.scalars(statement).all())

    def get_scene(self, scene_id: str) -> Scene | None:
        return self.db.get(Scene, scene_id)

    def list_versions(self, scene_id: str) -> list[SceneVersion]:
        statement = (
            select(SceneVersion)
            .where(SceneVersion.scene_id == scene_id)
            .order_by(SceneVersion.version.desc(), SceneVersion.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def get_version(self, scene_version_id: str) -> SceneVersion | None:
        return self.db.get(SceneVersion, scene_version_id)

    def next_version_number(self, scene_id: str) -> int:
        statement = select(func.max(SceneVersion.version)).where(SceneVersion.scene_id == scene_id)
        current = self.db.scalar(statement)
        return int(current or 0) + 1

    def save_imported_scene(self, imported: ImportedScene) -> SceneVersion:
        scene = self.db.get(Scene, imported.scene_id)
        if scene is None:
            scene = Scene(
                id=imported.scene_id,
                name=imported.name,
                domain=imported.domain,
                description=imported.description,
            )
            self.db.add(scene)
        else:
            scene.name = imported.name
            scene.domain = imported.domain
            if imported.description:
                scene.description = imported.description

        scene_version = SceneVersion(
            id=imported.scene_version_id,
            scene_id=imported.scene_id,
            version=imported.version,
            source_json=imported.source_json,
            graph_summary=imported.graph_summary,
        )
        self.db.add(scene_version)
        self.db.flush()

        self.db.add_all(
            SceneNode(
                scene_version_id=imported.scene_version_id,
                node_key=node.node_key,
                node_type=node.node_type,
                semantic_type=node.semantic_type,
                properties=node.properties,
            )
            for node in imported.nodes
        )
        self.db.add_all(
            SceneEdge(
                scene_version_id=imported.scene_version_id,
                source_key=edge.source_key,
                target_key=edge.target_key,
                relation=edge.relation,
                properties=edge.properties,
            )
            for edge in imported.edges
        )
        self.db.commit()
        self.db.refresh(scene_version)
        return scene_version

    def version_nodes(self, scene_version_id: str) -> list[SceneNode]:
        statement = select(SceneNode).where(SceneNode.scene_version_id == scene_version_id).order_by(SceneNode.node_key.asc())
        return list(self.db.scalars(statement).all())

    def version_edges(self, scene_version_id: str) -> list[SceneEdge]:
        statement = (
            select(SceneEdge)
            .where(SceneEdge.scene_version_id == scene_version_id)
            .order_by(SceneEdge.source_key.asc(), SceneEdge.target_key.asc(), SceneEdge.relation.asc())
        )
        return list(self.db.scalars(statement).all())
