"""Scene JSON Schema and validator for SnapReel.

Defines Pydantic models for scenes, template data payloads, and SceneScript.
Enforces validation rules defined in SCHEMA.md, FORMATS.md, TRANSITIONS.md, TEMPLATES_V2.md.
"""

from __future__ import annotations

import json
import re
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
    "title", "bullets", "bar_chart", "counter", "code_block", "kinetic",
    "lower_third", "quote", "icon_list", "split",
]
CodeLanguage = Literal["python", "js", "bash", "plain"]
TransitionType = Literal["fade", "slide_left", "slide_right", "zoom_in", "cross_dissolve", "none"]


class TitleData(BaseModel):
    heading: str = Field(..., max_length=80)
    subheading: Optional[str] = Field(None, max_length=120)


class BulletsData(BaseModel):
    heading: str = Field(..., max_length=80)
    items: list[Annotated[str, Field(max_length=120)]]

    @field_validator("items")
    @classmethod
    def validate_items_count(cls, v: list[str]) -> list[str]:
        if len(v) < 1:
            raise ValueError("bullets requires at least 1 item")
        if len(v) > 6:
            raise ValueError("bullets items must be at most 6 (max 6)")
        return v


class BarChartData(BaseModel):
    heading: str = Field(..., max_length=80)
    labels: list[str]
    values: list[Union[int, float]]
    unit: Optional[str] = Field(None, max_length=30)

    @model_validator(mode="before")
    @classmethod
    def wrap_single_values(cls, v: Any) -> Any:
        if isinstance(v, dict):
            v = dict(v)
            if "labels" in v and isinstance(v["labels"], str):
                v["labels"] = [v["labels"]]
            if "values" in v and isinstance(v["values"], (int, float)):
                v["values"] = [v["values"]]
        return v

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
            raise ValueError(f"labels and values must be same length ({len(self.labels)} vs {len(self.values)})")
        return self


class CounterData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    label: str = Field(..., max_length=80)
    from_value: Union[int, float] = Field(..., alias="from", serialization_alias="from")
    to: Union[int, float]
    unit: Optional[str] = Field(None, max_length=30)

    @model_validator(mode="before")
    @classmethod
    def handle_from_alias(cls, data: Any) -> Any:
        if isinstance(data, dict) and "from_" in data and "from" not in data and "from_value" not in data:
            data = dict(data)
            data["from"] = data.pop("from_")
        return data

    @property
    def from_(self) -> Union[int, float]:
        return self.from_value

    def __getitem__(self, key: str) -> Any:
        return self.from_value if key == "from" else getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except (KeyError, AttributeError):
            return default


class CodeBlockData(BaseModel):
    heading: Optional[str] = Field(None, max_length=80)
    language: CodeLanguage
    code: str = Field(..., max_length=600)


class KineticData(BaseModel):
    lines: list[Annotated[str, Field(max_length=80)]]
    style: Optional[Literal["pop_in", "slide_up", "typewriter", "word_highlight", "scale_fade"]] = "pop_in"
    align: Optional[Literal["center", "left"]] = "center"

    @field_validator("lines")
    @classmethod
    def validate_lines_count(cls, v: list[str]) -> list[str]:
        if len(v) < 1:
            raise ValueError("kinetic requires at least 1 line")
        if len(v) > 5:
            raise ValueError("kinetic lines must be at most 5 (max 5)")
        return v


class LowerThirdData(BaseModel):
    name: str = Field(..., max_length=40)
    role: Optional[str] = Field("", max_length=60)
    accent: Optional[str] = Field(None, max_length=20)

    @model_validator(mode="before")
    @classmethod
    def default_role_if_none(cls, v: Any) -> Any:
        if isinstance(v, dict):
            v = dict(v)
            if v.get("role") is None:
                v["role"] = ""
        return v


class QuoteData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    text: str = Field(..., max_length=200)
    attribution: Optional[str] = Field(None, alias="author", max_length=60)
    style: Optional[Literal["centered", "card"]] = "centered"

    @model_validator(mode="before")
    @classmethod
    def accept_author_alias(cls, v: Any) -> Any:
        """Accept 'author' as alias for 'attribution'."""
        if isinstance(v, dict):
            if "author" in v and "attribution" not in v:
                v = dict(v)
                v["attribution"] = v.pop("author")
        return v


_ICON_MAP = {
    # Common LLM-generated icon names -> nearest valid icon
    "gpu": "bolt", "ai": "star", "battery": "circle", "cpu": "bolt",
    "cloud": "circle", "chip": "bolt", "phone": "circle", "brain": "star",
    "speed": "arrow", "power": "bolt", "data": "circle", "wifi": "circle",
    "memory": "circle", "network": "circle", "model": "star", "npu": "bolt",
    "shield": "lock", "security": "lock", "privacy": "lock",
    "check_mark": "check", "checkmark": "check", "tick": "check",
    "right": "arrow", "next": "arrow", "forward": "arrow",
}
_VALID_ICONS = {"circle", "star", "check", "arrow", "bolt", "heart", "lock"}


class IconListItem(BaseModel):
    icon: str  # validated/coerced below
    text: str = Field(..., max_length=80)

    @model_validator(mode="before")
    @classmethod
    def coerce_icon_and_label(cls, v: Any) -> Any:
        """Accept 'label' as alias for 'text', and map unknown icons to valid ones."""
        if isinstance(v, dict):
            v = dict(v)
            if "label" in v and "text" not in v:
                v["text"] = v.pop("label")
            raw_icon = str(v.get("icon", "")).lower().strip()
            if raw_icon not in _VALID_ICONS:
                v["icon"] = _ICON_MAP.get(raw_icon, "circle")
        return v

    @field_validator("icon")
    @classmethod
    def validate_icon(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in _VALID_ICONS:
            return _ICON_MAP.get(v, "circle")
        return v


class IconListData(BaseModel):
    heading: Optional[str] = Field(None, max_length=80)
    items: list[IconListItem]

    @field_validator("items")
    @classmethod
    def validate_items_count(cls, v: list[IconListItem]) -> list[IconListItem]:
        if len(v) < 1:
            raise ValueError("icon_list requires at least 1 item")
        if len(v) > 5:
            raise ValueError("icon_list items must be at most 5 (max 5)")
        return v


class SplitData(BaseModel):
    heading: Optional[str] = Field(None, max_length=80)
    body: Optional[str] = Field(None, max_length=200)
    visual: Optional[Literal["bar", "counter", "none"]] = "none"
    visual_data: Optional[dict[str, Any]] = None
    # Aliases for LLM-generated field names
    left: Optional[str] = Field(None, max_length=200)
    right: Optional[str] = Field(None, max_length=200)

    @model_validator(mode="before")
    @classmethod
    def accept_left_right_as_body(cls, v: Any) -> Any:
        """Accept left/right as body content; make heading optional."""
        if isinstance(v, dict):
            v = dict(v)
            # If heading is None or missing, provide a default
            if not v.get("heading"):
                v["heading"] = "Comparison"
            # If body is missing but left/right present, combine them
            if not v.get("body") and (v.get("left") or v.get("right")):
                left = v.get("left", "")
                right = v.get("right", "")
                v["body"] = f"{left} vs {right}" if left and right else (left or right)
        return v


TEMPLATE_DATA_MODELS: dict[str, type[BaseModel]] = {
    "title": TitleData,
    "bullets": BulletsData,
    "bar_chart": BarChartData,
    "counter": CounterData,
    "code_block": CodeBlockData,
    "kinetic": KineticData,
    "lower_third": LowerThirdData,
    "quote": QuoteData,
    "icon_list": IconListData,
    "split": SplitData,
}

TemplateData = Union[
    TitleData, BulletsData, BarChartData, CounterData, CodeBlockData,
    KineticData, LowerThirdData, QuoteData, IconListData, SplitData,
]


_VALID_TEMPLATES = {
    "title", "bullets", "bar_chart", "counter", "code_block", "kinetic",
    "lower_third", "quote", "icon_list", "split",
}

# Map common LLM truncations/typos to correct template names
_TEMPLATE_CORRECTIONS: dict[str, str] = {
    "icon_": "icon_list", "icon_ist": "icon_list", "icon_lis": "icon_list",
    "icon_l": "icon_list", "iconlist": "icon_list", "icons": "icon_list",
    "lower_": "lower_third", "lower_t": "lower_third", "lowerthird": "lower_third",
    "bar_": "bar_chart", "barchart": "bar_chart", "bar": "bar_chart",
    "code_": "code_block", "codeblock": "code_block", "code": "code_block",
}


def _fix_template_name(name: str) -> str:
    """Auto-correct truncated or misspelled template names."""
    # Strip trailing dots, ellipsis, spaces, and other non-alphanumeric junk
    import re as _re
    name = _re.sub(r'[^a-z_]+$', '', name.lower().strip())
    if name in _VALID_TEMPLATES:
        return name
    if name.startswith("icon"):
        return "icon_list"
    if name.startswith("bar"):
        return "bar_chart"
    if name.startswith("lower"):
        return "lower_third"
    if name.startswith("code"):
        return "code_block"
    # Direct correction lookup
    corrected = _TEMPLATE_CORRECTIONS.get(name)
    if corrected:
        return corrected
    # Prefix match: find the only valid template that starts with this string
    matches = [t for t in _VALID_TEMPLATES if t.startswith(name)]
    if len(matches) == 1:
        return matches[0]
    return name  # let Pydantic reject it if truly invalid


class Scene(BaseModel):
    id: str
    template: TemplateType
    duration: float = Field(..., ge=2.0, le=300.0)
    narration: str = Field(..., max_length=1200)
    data: Any
    transition: Optional[str] = "fade"

    @model_validator(mode="before")
    @classmethod
    def fix_template_name(cls, v: Any) -> Any:
        """Auto-correct truncated template names from LLM output and ensure narration is string."""
        if isinstance(v, dict):
            v = dict(v)
            if "template" in v:
                v["template"] = _fix_template_name(str(v["template"]).strip())
            if v.get("narration") is None:
                v["narration"] = ""
        return v

    @field_validator("transition")
    @classmethod
    def validate_transition(cls, v: Optional[str]) -> str:
        allowed = {"fade", "slide_left", "slide_right", "zoom_in", "cross_dissolve", "none"}
        if not v or v.lower() not in allowed:
            return "fade"
        return v.lower()

    @model_validator(mode="after")
    def validate_data_for_template(self) -> "Scene":
        model_cls = TEMPLATE_DATA_MODELS.get(self.template)
        if model_cls is not None:
            if isinstance(self.data, dict):
                self.data = model_cls.model_validate(self.data)
            elif isinstance(self.data, BaseModel):
                if not isinstance(self.data, model_cls):
                    self.data = model_cls.model_validate(self.data.model_dump(by_alias=True))
            elif isinstance(self.data, str):
                self.data = KineticData(lines=[self.data[:80]])
            else:
                self.data = model_cls.model_validate(self.data)
        return self


class SceneScript(BaseModel):
    title: str = Field(..., max_length=80)
    target_duration: int = 60
    aspect_ratio: str = "16:9"
    total_duration: float
    scenes: list[Scene] = Field(..., min_length=1, max_length=30)

    @field_validator("aspect_ratio")
    @classmethod
    def valid_ratio(cls, v: str) -> str:
        allowed = {"16:9", "9:16", "1:1", "4:3"}
        if v not in allowed:
            raise ValueError(f"aspect_ratio must be one of {allowed}")
        return v

    @model_validator(mode="after")
    def validate_total_duration(self) -> "SceneScript":
        scene_sum = sum(s.duration for s in self.scenes)
        if abs(self.total_duration - scene_sum) > 0.1 + 1e-6:
            raise ValueError(
                f"total_duration mismatch: specified {self.total_duration}s, "
                f"but sum of scene durations is {scene_sum:.2f}s (tolerance is +-0.1s)"
            )
        return self


def _extract_json_content(text: str) -> str:
    """Extract JSON object from LLM responses that may include thinking process, preambles, or markdown."""
    text = text.strip()
    if not text:
        return text

    # 1. Strip thinking tags <think>...</think> if present
    text = re.sub(r"(?is)<think>.*?</think>", "", text).strip()

    # 2. Look for markdown code fence containing JSON with "scenes" or "title"
    fences = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    for fence in reversed(fences):
        f = fence.strip()
        if "{" in f and "}" in f and ("scenes" in f or "title" in f):
            first = f.find("{")
            last = f.rfind("}")
            if first != -1 and last > first:
                return f[first:last + 1]

    # 3. Look for the outermost JSON object if there is conversational preamble (e.g. "Here's a thinking process...")
    first_brace = text.find("{")
    if first_brace != -1:
        last_brace = text.rfind("}")
        if last_brace > first_brace:
            return text[first_brace:last_brace + 1]
        else:
            # Truncated JSON starting at first_brace
            return text[first_brace:]

    return text


def _repair_json(text: str) -> str:
    """Attempt to auto-repair common LLM JSON formatting errors.

    Handles:
    - Thinking processes, chain-of-thought, or conversational preambles
    - Markdown code fences (even if preceded by conversational text)
    - Trailing commas before } or ] (e.g. ``{"a": 1,}``)
    - Missing comma between adjacent closing/opening braces (e.g. ``} {``)
    - Smart/curly quotes replaced with straight quotes
    - Truncated JSON: attempt to close unclosed braces/brackets
    - Lone backslash before a normal character (invalid escape)
    """
    # 0. Extract JSON if wrapped in thinking tokens or conversational text
    text = _extract_json_content(text)

    # 1. Strip markdown fences if still present
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # 2. Normalise smart/curly quotes -> straight quotes
    for bad, good in (("\u2018", "'"), ("\u2019", "'"), ("\u201c", '"'), ("\u201d", '"')):
        text = text.replace(bad, good)

    # 3. Remove trailing commas before } or ]
    text = re.sub(r",\s*([}\]])", r"\1", text)

    # 4. Insert missing commas between adjacent objects/arrays: }{ or }[ or ]{
    #    e.g. }\n    { -> },\n    {
    text = re.sub(r"([}\]])\s*\n(\s*)([{\[\"])", r"\1,\n\2\3", text)
    #    Insert missing comma between adjacent properties:
    #    e.g. "val"\n    "key": -> "val",\n    "key":
    text = re.sub(r'("|\d|true|false|null|[}\]])\s*\n(\s*"[a-zA-Z0-9_]+"\s*:)', r"\1,\n\2", text)

    # 5. Fix invalid escape sequences (lone backslash before non-special char)
    #    e.g. \n is fine, \' is not valid JSON — replace \' with '
    text = re.sub(r"\\([^\"\\bfnrtu/])", r"\1", text)

    # 6. If JSON is truncated (unbalanced braces), try to close it
    try:
        json.loads(text)
        return text  # already valid
    except json.JSONDecodeError:
        pass

    # Count unmatched open braces/brackets
    stack: list[str] = []
    in_str = False
    escape_next = False
    for ch in text:
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_str:
            escape_next = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]" and stack:
            stack.pop()

    if stack:
        text = text.rstrip().rstrip(",") + "".join(reversed(stack))

    return text


def validate_script(raw_json: Union[str, dict[str, Any]]) -> SceneScript:
    """Validate a raw JSON string (or dictionary) against SceneScript schema.

    Attempts automatic repair of common LLM JSON formatting errors before
    raising a ValidationError.
    """
    if isinstance(raw_json, dict):
        return SceneScript.model_validate(raw_json)

    if not isinstance(raw_json, str):
        raise ValidationError.from_exception_data(
            title="SceneScript",
            line_errors=[{"type": "model_type", "loc": (), "input": raw_json, "ctx": {"expected": "str or dict"}}],
        )

    # Try raw first, then repaired
    for candidate in (raw_json.strip(), _repair_json(raw_json.strip())):
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return SceneScript.model_validate(data)
        except (json.JSONDecodeError, Exception):
            pass

    # Both failed — raise a clear error with the original text
    try:
        json.loads(_repair_json(raw_json.strip()))
    except json.JSONDecodeError as exc:
        raise ValidationError.from_exception_data(
            title="SceneScript",
            line_errors=[{"type": "value_error", "loc": (), "input": raw_json, "ctx": {"error": f"Invalid JSON: {exc}"}}],
        ) from exc

    # JSON parsed but Pydantic validation failed — let Pydantic raise directly
    data = json.loads(_repair_json(raw_json.strip()))
    return SceneScript.model_validate(data)


__all__ = [
    "TemplateType", "CodeLanguage", "TransitionType",
    "TitleData", "BulletsData", "BarChartData", "CounterData", "CodeBlockData",
    "KineticData", "LowerThirdData", "QuoteData", "IconListItem", "IconListData", "SplitData",
    "Scene", "SceneScript", "validate_script", "ValidationError",
]
