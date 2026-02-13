from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal, Mapping
from .utils import get_theme_path


# ---------- small utilities ----------

def _as_mapping(obj: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(obj, Mapping):
        raise TypeError(f"{path} must be an object/dict, got {type(obj).__name__}")
    return obj


def _get(obj: Mapping[str, Any], key: str, path: str, *, default: Any = None, required: bool = True) -> Any:
    if key in obj:
        return obj[key]
    if required:
        raise KeyError(f"Missing required field: {path}.{key}")
    return default


def _as_str(v: Any, path: str) -> str:
    if not isinstance(v, str):
        raise TypeError(f"{path} must be str, got {type(v).__name__}")
    return v


def _as_float(v: Any, path: str) -> float:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    raise TypeError(f"{path} must be number, got {type(v).__name__}")


def _as_int(v: Any, path: str) -> int:
    if isinstance(v, int) and not isinstance(v, bool):
        return v
    raise TypeError(f"{path} must be int, got {type(v).__name__}")


def _as_bool(v: Any, path: str) -> bool:
    if isinstance(v, bool):
        return v
    raise TypeError(f"{path} must be bool, got {type(v).__name__}")


def _as_color_hex(v: Any, path: str) -> str:
    s = _as_str(v, path)
    if len(s) == 7 and s.startswith("#"):
        # minimal check: '#RRGGBB'
        hex_part = s[1:]
        if all(c in "0123456789abcdefABCDEF" for c in hex_part):
            return s.upper()
    raise ValueError(f"{path} must be color hex '#RRGGBB', got {s!r}")


# ---------- schema dataclasses ----------

Alignment = Literal["LEFT", "CENTER", "RIGHT", "JUSTIFY"]
Orientation = Literal["portrait", "landscape"]
PageSize = Literal["A4", "A3", "A5", "Letter", "Legal"]  # extend as needed


@dataclass(frozen=True)
class Meta:
    name: str
    version: str
    author: str

    @staticmethod
    def from_dict(d: Mapping[str, Any], path: str = "meta") -> "Meta":
        d = _as_mapping(d, path)
        return Meta(
            name=_as_str(_get(d, "name", path), f"{path}.name"),
            version=_as_str(_get(d, "version", path), f"{path}.version"),
            author=_as_str(_get(d, "author", path), f"{path}.author"),
        )


@dataclass(frozen=True)
class Page:
    size: PageSize
    orientation: Orientation
    margin_top: int
    margin_bottom: int
    margin_left: int
    margin_right: int
    background_color: str

    @staticmethod
    def from_dict(d: Mapping[str, Any], path: str = "page") -> "Page":
        d = _as_mapping(d, path)
        size = _as_str(_get(d, "size", path), f"{path}.size")
        orientation = _as_str(_get(d, "orientation", path), f"{path}.orientation")

        # enforce known literals (fail fast, don't silently accept garbage)
        if size not in ("A4", "A3", "A5", "Letter", "Legal"):
            raise ValueError(f"{path}.size unsupported: {size!r}")
        if orientation not in ("portrait", "landscape"):
            raise ValueError(f"{path}.orientation unsupported: {orientation!r}")

        return Page(
            size=size,  # type: ignore[assignment]
            orientation=orientation,  # type: ignore[assignment]
            margin_top=_as_int(_get(d, "margin_top", path), f"{path}.margin_top"),
            margin_bottom=_as_int(_get(d, "margin_bottom", path), f"{path}.margin_bottom"),
            margin_left=_as_int(_get(d, "margin_left", path), f"{path}.margin_left"),
            margin_right=_as_int(_get(d, "margin_right", path), f"{path}.margin_right"),
            background_color=_as_color_hex(_get(d, "background_color", path), f"{path}.background_color"),
        )


@dataclass(frozen=True)
class Fonts:
    regular: str
    bold:str
    heading: str
    code: str

    @staticmethod
    def from_dict(d: Mapping[str, Any], path: str = "fonts") -> "Fonts":
        d = _as_mapping(d, path)
        return Fonts(
            regular=_as_str(_get(d, "regular", path), f"{path}.regular"),
            bold=_as_str(_get(d, "bold", path), f"{path}.bold"),
            heading=_as_str(_get(d, "heading", path), f"{path}.heading"),
            code=_as_str(_get(d, "code", path), f"{path}.code"),
        )


@dataclass(frozen=True)
class Colors:
    text_primary: str
    text_secondary: str
    link: str
    border: str

    @staticmethod
    def from_dict(d: Mapping[str, Any], path: str = "colors") -> "Colors":
        d = _as_mapping(d, path)
        return Colors(
            text_primary=_as_color_hex(_get(d, "text_primary", path), f"{path}.text_primary"),
            text_secondary=_as_color_hex(_get(d, "text_secondary", path), f"{path}.text_secondary"),
            link=_as_color_hex(_get(d, "link", path), f"{path}.link"),
            border=_as_color_hex(_get(d, "border", path), f"{path}.border"),
        )


@dataclass(frozen=True)
class BodyStyle:
    font_size: float
    leading: float
    alignment: Alignment
    space_after: float

    @staticmethod
    def from_dict(d: Mapping[str, Any], path: str = "styles.body") -> "BodyStyle":
        d = _as_mapping(d, path)
        alignment = _as_str(_get(d, "alignment", path), f"{path}.alignment")
        if alignment not in ("LEFT", "CENTER", "RIGHT", "JUSTIFY"):
            raise ValueError(f"{path}.alignment unsupported: {alignment!r}")
        return BodyStyle(
            font_size=_as_float(_get(d, "font_size", path), f"{path}.font_size"),
            leading=_as_float(_get(d, "leading", path), f"{path}.leading"),
            alignment=alignment,  # type: ignore[assignment]
            space_after=_as_float(_get(d, "space_after", path), f"{path}.space_after"),
        )


@dataclass(frozen=True)
class HeadingStyle:
    font_size: float
    leading: float
    color: str
    space_before: float
    space_after: float
    align: Alignment

    @staticmethod
    def from_dict(d: Mapping[str, Any], path: str) -> "HeadingStyle":
        d = _as_mapping(d, path)
        align = _as_str(_get(d, "align", path), f"{path}.align")
        if align not in ("LEFT", "CENTER", "RIGHT", "JUSTIFY"):
            raise ValueError(f"{path}.align unsupported: {align!r}")
        return HeadingStyle(
            font_size=_as_float(_get(d, "font_size", path), f"{path}.font_size"),
            leading=_as_float(_get(d, "leading", path), f"{path}.leading"),
            color=_as_color_hex(_get(d, "color", path), f"{path}.color"),
            space_before=_as_float(_get(d, "space_before", path), f"{path}.space_before"),
            space_after=_as_float(_get(d, "space_after", path), f"{path}.space_after"),
            align=align,  # type: ignore[assignment]
        )


@dataclass(frozen=True)
class Headings:
    h1: HeadingStyle
    h2: HeadingStyle
    h3: HeadingStyle
    h4: HeadingStyle

    @staticmethod
    def from_dict(d: Mapping[str, Any], path: str = "styles.headings") -> "Headings":
        d = _as_mapping(d, path)
        return Headings(
            h1=HeadingStyle.from_dict(_get(d, "h1", path), f"{path}.h1"),
            h2=HeadingStyle.from_dict(_get(d, "h2", path), f"{path}.h2"),
            h3=HeadingStyle.from_dict(_get(d, "h3", path), f"{path}.h3"),
            h4=HeadingStyle.from_dict(_get(d, "h4", path), f"{path}.h4"),
        )

@dataclass(frozen=True)
class CodeStyle:
    style_name: str
    font_size: float
    background_color: str
    border_color: str
    show_line_numbers: bool
    highlight_colors: Mapping[str, str]

    @staticmethod
    def from_dict(d: Mapping[str, Any], path: str = "styles.code") -> "CodeStyle":
        d = _as_mapping(d, path)

        # 解析 highlight_colors，默认为空字典以防万一
        raw_colors = _get(d, "highlight_colors", path, default={})
        if not isinstance(raw_colors, Mapping):
            raise TypeError(f"{path}.highlight_colors must be a dict")

        # 确保所有值都是 Hex 颜色
        validated_colors = {}
        for k, v in raw_colors.items():
            validated_colors[k] = _as_color_hex(v, f"{path}.highlight_colors.{k}")

        return CodeStyle(
            style_name=_as_str(_get(d, "style_name", path), f"{path}.style_name"),
            font_size=_as_float(_get(d, "font_size", path), f"{path}.font_size"),
            background_color=_as_color_hex(_get(d, "background_color", path), f"{path}.background_color"),
            border_color=_as_color_hex(_get(d, "border_color", path), f"{path}.border_color"),
            show_line_numbers=_as_bool(_get(d, "show_line_numbers", path), f"{path}.show_line_numbers"),
            highlight_colors=validated_colors  # [NEW]
        )

@dataclass(frozen=True)
class TableStyle:
    header_bg: str
    header_text: str
    row_bg_even: str
    row_bg_odd: str
    grid_color: str

    @staticmethod
    def from_dict(d: Mapping[str, Any], path: str = "styles.table") -> "TableStyle":
        d = _as_mapping(d, path)
        return TableStyle(
            header_bg=_as_color_hex(_get(d, "header_bg", path), f"{path}.header_bg"),
            header_text=_as_color_hex(_get(d, "header_text", path), f"{path}.header_text"),
            row_bg_even=_as_color_hex(_get(d, "row_bg_even", path), f"{path}.row_bg_even"),
            row_bg_odd=_as_color_hex(_get(d, "row_bg_odd", path), f"{path}.row_bg_odd"),
            grid_color=_as_color_hex(_get(d, "grid_color", path), f"{path}.grid_color"),
        )

@dataclass(frozen=True)
class QuoteStyle:
    border_color: str
    border_width: float
    left_indent: float   # 竖线和文字之间的距离
    text_color: str      # 引用文字颜色 (可选)

    @staticmethod
    def from_dict(d: Mapping[str, Any], path: str = "styles.quote") -> "QuoteStyle":
        d = _as_mapping(d, path)
        return QuoteStyle(
            border_color=_as_color_hex(_get(d, "border_color", path), f"{path}.border_color"),
            border_width=_as_float(_get(d, "border_width", path), f"{path}.border_width"),
            left_indent=_as_float(_get(d, "left_indent", path), f"{path}.left_indent"),
            text_color=_as_color_hex(_get(d, "text_color", path, default="#666666"), f"{path}.text_color"),
        )

@dataclass(frozen=True)
class Styles:
    body: BodyStyle
    headings: Headings
    code: CodeStyle
    table: TableStyle
    quote: QuoteStyle

    @staticmethod
    def from_dict(d: Mapping[str, Any], path: str = "styles") -> "Styles":
        d = _as_mapping(d, path)
        return Styles(
            body=BodyStyle.from_dict(_get(d, "body", path), f"{path}.body"),
            headings=Headings.from_dict(_get(d, "headings", path), f"{path}.headings"),
            code=CodeStyle.from_dict(_get(d, "code", path), f"{path}.code"),
            table=TableStyle.from_dict(_get(d, "table", path), f"{path}.table"),
            quote=QuoteStyle.from_dict(_get(d, "quote", path), f"{path}.quote"),
        )


@dataclass(frozen=True)
class StyleConfig:
    meta: Meta
    page: Page
    fonts: Fonts
    colors: Colors
    styles: Styles

    @staticmethod
    def from_dict(d: Mapping[str, Any], path: str = "$") -> "StyleConfig":
        d = _as_mapping(d, path)
        return StyleConfig(
            meta=Meta.from_dict(_get(d, "meta", path), "meta"),
            page=Page.from_dict(_get(d, "page", path), "page"),
            fonts=Fonts.from_dict(_get(d, "fonts", path), "fonts"),
            colors=Colors.from_dict(_get(d, "colors", path), "colors"),
            styles=Styles.from_dict(_get(d, "styles", path), "styles"),
        )

    @staticmethod
    def from_json_obj(obj: Any) -> "StyleConfig":
        return StyleConfig.from_dict(_as_mapping(obj, "$"), "$")

    @staticmethod
    def get_pre_build_style(style_name: str):
        with get_theme_path(f"{style_name}.json") as theme_path:
            with open(theme_path, "r", encoding='utf-8') as f:
                text = f.read()
        return StyleConfig.from_json_obj(json.loads(text))


# ---------- usage example ----------
if __name__ == '__main__':
    print(StyleConfig.get_pre_build_style("academic"))
