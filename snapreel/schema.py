"""Scene JSON Schema and validator for SnapReel.

Defines Pydantic models for scenes, template data payloads, and SceneScript.
Enforces validation rules defined in SCHEMA.md.
"""

from __future__ import annotations

import json
from typing import Annotated, Any, Literal, Optional, Union
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)


TemplateType = Literal[
    "title",
    "bullets",
    "bar_chart",
    "counter",
    "code_block",
    "kinetic",
]

CodeLanguage = Literal["python", "js", "bash", "plain"]


class TitleData(BaseModel):
    """Data payload for 'title' template."""

    heading: str = Field(..., max_length=60)
    subheading: Optional[str] = Field(None, max_length=100)


class BulletsData(BaseModel):
    """Data payload for 'bullets' template."""

    heading: str = Field(..., max_length=60)
    items: list[Annotated[str, Field(max_length=80)]]

    @field_validator("items")
    @classmethod
    def validate_items_count(cls, v: list[str]) -> list[str]:
        if len(v) < 1:
            raise ValueError("bullets requires at least 1 item")
        if len(v) > 6:
            raise ValueError("bullets items must be at most 6 (max 6)")
        return v


class BarChartData(BaseModel):
    """Data payload for 'bar_chart' template."""

    heading: str = Field(..., max_length=60)
    labels: list[str]
    values: list[Union[int, float]]
    unit: Optional[str] = Field(None, max_length=10)

    @field_validator("labels", "values")
    @classmethod
    def validate_lengths(cls, v: list, info) -> list:
        if len(v) < 2:
            raise ValueError(f"{info.field_name} requires at least 2 items (min 2)")
        if len(v) > 8:
            raise ValueError(f"{info.field_name} must have at most 8 items (max 8)")
        return v

    @model_validator(mode="after")
    def validate_same_length(self) -> "BarChartData":
        if len(self.labels) != len(self.values):
            raise ValueError(
                f"labels and values must be same length (labels={len(self.labels)}, values={len(self.values)})"
            )
        return self


class CounterData(BaseModel):
    """Data payload for 'counter' template."""

    model_config = ConfigDict(populate_by_name=True)

    label: str = Field(..., max_length=60)
    from_value: Union[int, float] = Field(..., alias="from", serialization_alias="from")
    to: Union[int, float]
    unit: Optional[str] = Field(None, max_length=10)

    @model_validator(mode="before")
    @classmethod
    def handle_from_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "from_" in data and "from" not in data and "from_value" not in data:
                data = dict(data)
                data["from"] = data.pop("from_")
        return data

    @property
    def from_(self) -> Union[int, float]:
        return self.from_value

    def __getitem__(self, key: str) -> Any:
        if key == "from":
            return self.from_value
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except (KeyError, AttributeError):
            return default


class CodeBlockData(BaseModel):
    """Data payload for 'code_block' template."""

    heading: Optional[str] = Field(None, max_length=60)
    language: CodeLanguage
    code: str = Field(..., max_length=600)


class KineticData(BaseModel):
    """Data payload for 'kinetic' template."""

    lines: list[Annotated[str, Field(max_length=60)]]

    @field_validator("lines")
    @classmethod
    def validate_lines_count(cls, v: list[str]) -> list[str]:
        if len(v) < 1:
            raise ValueError("kinetic requires at least 1 line")
        if len(v) > 5:
            raise ValueError("kinetic lines must be at most 5 (max 5)")
        return v


TEMPLATE_DATA_MODELS: dict[str, type[BaseModel]] = {
    "title": TitleData,
    "bullets": BulletsData,
    "bar_chart": BarChartData,
    "counter": CounterData,
    "code_block": CodeBlockData,
    "kinetic": KineticData,
}

TemplateData = Union[
    TitleData,
    BulletsData,
    BarChartData,
    CounterData,
    CodeBlockData,
    KineticData,
]


class Scene(BaseModel):
    """Single scene definition in a video script."""

    id: str
    template: TemplateType
    duration: float = Field(..., ge=2.0, le=15.0)
    narration: str = Field(..., max_length=200)
    data: Any

    @model_validator(mode="after")
    def validate_data_for_template(self) -> "Scene":
        model_cls = TEMPLATE_DATA_MODELS.get(self.template)
        if model_cls is not None:
            if isinstance(self.data, dict):
                self.data = model_cls.model_validate(self.data)
            elif isinstance(self.data, BaseModel):
                if not isinstance(self.data, model_cls):
                    self.data = model_cls.model_validate(self.data.model_dump(by_alias=True))
            else:
                self.data = model_cls.model_validate(self.data)
        return self


class SceneScript(BaseModel):
    """Complete video script containing title, total duration, and scenes."""

    title: str = Field(..., max_length=80)
    total_duration: float
    scenes: list[Scene] = Field(..., min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_total_duration(self) -> "SceneScript":
        scene_sum = sum(s.duration for s in self.scenes)
        # Tolerance of +-0.1 second as per SCHEMA.md rule 5
        if abs(self.total_duration - scene_sum) > 0.1 + 1e-6:
            raise ValueError(
                f"total_duration mismatch: specified {self.total_duration}s, "
                f"but sum of scene durations is {scene_sum:.2f}s (tolerance is +-0.1s)"
            )
        return self


def validate_script(raw_json: Union[str, dict[str, Any]]) -> SceneScript:
    """Validate a raw JSON string (or dictionary) against the SceneScript schema.

    Args:
        raw_json: Raw JSON string or dictionary representation of the scene script.

    Returns:
        Validated SceneScript instance.

    Raises:
        ValidationError: If JSON is malformed or schema constraints are violated.
    """
    if isinstance(raw_json, dict):
        return SceneScript.model_validate(raw_json)

    if not isinstance(raw_json, str):
        raise ValidationError.from_exception_data(
            title="SceneScript",
            line_errors=[
                {
                    "type": "model_type",
                    "loc": (),
                    "input": raw_json,
                    "ctx": {"expected": "str or dict"},
                }
            ],
        )

    cleaned = raw_json.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValidationError.from_exception_data(
            title="SceneScript",
            line_errors=[
                {
                    "type": "value_error",
                    "loc": (),
                    "input": raw_json,
                    "ctx": {"error": f"Invalid JSON: {exc}"},
                }
            ],
        ) from exc

    if not isinstance(data, dict):
        raise ValidationError.from_exception_data(
            title="SceneScript",
            line_errors=[
                {
                    "type": "model_type",
                    "loc": (),
                    "input": data,
                    "ctx": {"expected": "dict (JSON object)"},
                }
            ],
        )

    return SceneScript.model_validate(data)


__all__ = [
    "TemplateType",
    "CodeLanguage",
    "TitleData",
    "BulletsData",
    "BarChartData",
    "CounterData",
    "CodeBlockData",
    "KineticData",
    "Scene",
    "SceneScript",
    "validate_script",
    "ValidationError",
]
