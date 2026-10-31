"""The flat JSON-schema argument validator shared by the assistant tools and the modules.

A schema is ``{"type": "object", "properties": {...}, "required": [...]}`` whose properties are
scalars (``string``, ``integer``, ``number``, ``boolean``) or an ``array`` of strings. Nothing is
evaluated and no ``$ref`` is followed: a property is checked against its own keywords only.
"""

import copy
import math
import unicodedata

# control, format, surrogate, private-use and unassigned characters, line and paragraph separators
_CONTROL = frozenset({"Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp"})
_TYPES = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, int | float) and not isinstance(v, bool) and math.isfinite(v),
    "boolean": lambda v: isinstance(v, bool),
    "array": lambda v: isinstance(v, list) and all(isinstance(x, str) for x in v),
}
_KEYWORDS = frozenset(
    {
        "type",
        "description",
        "default",
        "enum",
        "minimum",
        "maximum",
        "maxLength",
        "maxItems",
        "items",
    }
)
MAX_ITEMS = 1000  # an array property never takes more than this many items


def clean_text(s, max_len: int = 80) -> str:
    """``s`` made safe to show to a model: control characters become spaces, whitespace runs
    collapse, the result is stripped and cut to ``max_len`` characters (ending in ``…``)."""
    text = "".join(" " if unicodedata.category(ch) in _CONTROL else ch for ch in str(s))
    text = " ".join(text.split())
    if len(text) > max_len:
        text = text[: max_len - 1].rstrip() + "…"
    return text


def validate_args(schema: dict, args) -> dict:
    """``args`` with defaults filled in; ``ValueError`` naming the first offending argument."""
    if not isinstance(args, dict):
        raise ValueError("arguments must be an object")
    props = schema["properties"]
    for name in args:
        if name not in props:
            raise ValueError(f"unknown argument '{clean_text(name, 40)}'")
    out = {}
    for name, spec in props.items():
        if name not in args:
            if name in schema.get("required", []):
                raise ValueError(f"missing argument '{name}'")
            if "default" in spec:
                out[name] = copy.deepcopy(spec["default"])
            continue
        value = args[name]
        if not _TYPES[spec["type"]](value):
            raise ValueError(f"argument '{name}' must be of type {spec['type']}")
        if "enum" in spec and value not in spec["enum"]:
            raise ValueError(f"argument '{name}' must be one of {spec['enum']}")
        if "minimum" in spec and value < spec["minimum"]:
            raise ValueError(f"argument '{name}' must be at least {spec['minimum']}")
        if "maximum" in spec and value > spec["maximum"]:
            raise ValueError(f"argument '{name}' must be at most {spec['maximum']}")
        if "maxLength" in spec and len(value) > spec["maxLength"]:
            raise ValueError(f"argument '{name}' must be at most {spec['maxLength']} characters")
        limit = spec.get("maxItems", MAX_ITEMS)
        if spec["type"] == "array" and len(value) > limit:
            raise ValueError(f"argument '{name}' must have at most {limit} items")
        out[name] = value
    return out


def check_schema(schema) -> dict:
    """``schema`` if it is a valid flat schema, else ``ValueError``; for schemas that come from
    outside (an uploaded module's metadata) before anything relies on their shape."""
    if not isinstance(schema, dict) or not isinstance(schema.get("properties"), dict):
        raise ValueError("params must be an object with 'properties'")
    required = schema.get("required", [])
    if not isinstance(required, list) or not all(isinstance(r, str) for r in required):
        raise ValueError("params 'required' must be a list of names")
    for name, spec in schema["properties"].items():
        if not isinstance(name, str) or not isinstance(spec, dict):
            raise ValueError("every parameter must be an object")
        if spec.get("type") not in _TYPES:
            raise ValueError(f"parameter '{clean_text(name, 40)}' has an unsupported type")
        if not _KEYWORDS.issuperset(spec):
            raise ValueError(f"parameter '{clean_text(name, 40)}' uses an unsupported keyword")
        if "enum" in spec and not isinstance(spec["enum"], list):
            raise ValueError(f"parameter '{clean_text(name, 40)}' has an invalid enum")
        if "default" in spec:
            try:
                validate_args({"properties": {name: spec}}, {name: spec["default"]})
            except (ValueError, TypeError) as e:
                raise ValueError(f"parameter '{clean_text(name, 40)}' has a bad default") from e
        for key in ("minimum", "maximum", "maxLength", "maxItems"):
            if key in spec and not _TYPES["number"](spec[key]):
                raise ValueError(f"parameter '{clean_text(name, 40)}' has an invalid {key}")
    unknown = [r for r in required if r not in schema["properties"]]
    if unknown:
        raise ValueError(f"'required' names unknown parameters: {unknown}")
    return schema
