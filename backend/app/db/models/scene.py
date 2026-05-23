from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.models.base import Base, TimestampMixin
from backend.app.db.models.types import JSONBType


class Scene(TimestampMixin, Base):
    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    versions: Mapped[list["SceneVersion"]] = relationship(back_populates="scene", cascade="all, delete-orphan")


class SceneVersion(TimestampMixin, Base):
    __tablename__ = "scene_versions"
    __table_args__ = (UniqueConstraint("scene_id", "version", name="uq_scene_versions_scene_version"),)

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    scene_id: Mapped[str] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"), index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_json: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)
    graph_summary: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)

    scene: Mapped[Scene] = relationship(back_populates="versions")
    nodes: Mapped[list["SceneNode"]] = relationship(back_populates="scene_version", cascade="all, delete-orphan")
    edges: Mapped[list["SceneEdge"]] = relationship(back_populates="scene_version", cascade="all, delete-orphan")


class SceneNode(TimestampMixin, Base):
    __tablename__ = "scene_nodes"
    __table_args__ = (UniqueConstraint("scene_version_id", "node_key", name="uq_scene_nodes_version_key"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scene_version_id: Mapped[str] = mapped_column(ForeignKey("scene_versions.id", ondelete="CASCADE"), index=True)
    node_key: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    node_type: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    semantic_type: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    properties: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)

    scene_version: Mapped[SceneVersion] = relationship(back_populates="nodes")


class SceneEdge(TimestampMixin, Base):
    __tablename__ = "scene_edges"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scene_version_id: Mapped[str] = mapped_column(ForeignKey("scene_versions.id", ondelete="CASCADE"), index=True)
    source_key: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    target_key: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    relation: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    properties: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)

    scene_version: Mapped[SceneVersion] = relationship(back_populates="edges")
