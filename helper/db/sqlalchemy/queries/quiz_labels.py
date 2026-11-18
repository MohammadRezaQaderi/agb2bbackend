from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from helper.db.sqlalchemy.models import QuizLabel


def _normalize_quiz_kind(quiz_kind: str) -> str:
    normalized = str(quiz_kind or "").strip().upper()
    if not normalized:
        raise ValueError("quiz_kind is required")
    return normalized


def _serialize_json_object(value: Mapping[str, Any], field_name: str) -> str:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return json.dumps(
        dict(value),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )


def _deserialize_json_object(value: str | None) -> dict[str, Any] | None:
    if value is None:
        return None
    decoded = json.loads(value)
    if not isinstance(decoded, dict):
        raise ValueError("stored quiz label JSON must contain an object")
    return decoded


def _quiz_label_payload(record: QuizLabel) -> dict[str, Any]:
    return {
        "id": record.id,
        "user_id": record.user_id,
        "quiz_kind": record.quiz_kind,
        "labels": _deserialize_json_object(record.labels_json),
        "metadata": _deserialize_json_object(record.metadata_json),
        "definition_version": record.definition_version,
        "scoring_version": record.scoring_version,
        "created_time": record.created_time,
        "edited_time": record.edited_time,
    }


def upsert_quiz_labels(
    session: Session,
    *,
    user_id: int | str,
    quiz_kind: str,
    labels: Mapping[str, Any],
    definition_version: str,
    scoring_version: str,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_kind = _normalize_quiz_kind(quiz_kind)
    normalized_definition_version = str(definition_version or "").strip()
    normalized_scoring_version = str(scoring_version or "").strip()
    if not normalized_definition_version:
        raise ValueError("definition_version is required")
    if not normalized_scoring_version:
        raise ValueError("scoring_version is required")

    labels_json = _serialize_json_object(labels, "labels")
    metadata_json = (
        _serialize_json_object(metadata, "metadata")
        if metadata is not None
        else None
    )
    normalized_user_id = int(user_id)
    record = session.execute(
        select(QuizLabel).where(
            QuizLabel.user_id == normalized_user_id,
            QuizLabel.quiz_kind == normalized_kind,
        )
    ).scalar_one_or_none()

    if record is None:
        record = QuizLabel(
            user_id=normalized_user_id,
            quiz_kind=normalized_kind,
            labels_json=labels_json,
            metadata_json=metadata_json,
            definition_version=normalized_definition_version,
            scoring_version=normalized_scoring_version,
        )
        session.add(record)
    else:
        record.labels_json = labels_json
        record.metadata_json = metadata_json
        record.definition_version = normalized_definition_version
        record.scoring_version = normalized_scoring_version
        record.edited_time = datetime.now()

    session.flush()
    return _quiz_label_payload(record)


def get_quiz_labels(
    session: Session,
    *,
    user_id: int | str,
    quiz_kind: str,
) -> dict[str, Any] | None:
    record = session.execute(
        select(QuizLabel).where(
            QuizLabel.user_id == int(user_id),
            QuizLabel.quiz_kind == _normalize_quiz_kind(quiz_kind),
        )
    ).scalar_one_or_none()
    return _quiz_label_payload(record) if record else None


def list_quiz_labels_for_user(
    session: Session,
    *,
    user_id: int | str,
) -> list[dict[str, Any]]:
    records = session.execute(
        select(QuizLabel)
        .where(QuizLabel.user_id == int(user_id))
        .order_by(QuizLabel.quiz_kind.asc())
    ).scalars().all()
    return [_quiz_label_payload(record) for record in records]
