"""Load the BI-RADS descriptor lexicon from its Markdown definition file.

Each descriptor line in the file has the form:
    - Label — `variable` (one | multi | multiple): value_a, value_b, ...
grouped under one `## Modality` heading per modality.
"""

import re
from dataclasses import dataclass
from pathlib import Path

LEXICON_FILE = Path(__file__).parent / "lexicon" / "Descriptors_V.1.0.2.md"

_HEADING = re.compile(r"^##\s+(?P<name>.+?)\s*$")
_DESCRIPTOR = re.compile(
    r"^-\s+(?P<label>.+?)\s+—\s+`(?P<variable>\w+)`\s+\((?P<cardinality>one|multi|multiple)\):\s+(?P<values>.+?)\s*$"
)
_RANGE = re.compile(r"(?P<prefix>[a-z_]+?)(?P<start>\d+)\.\.(?P=prefix)(?P<end>\d+)")


@dataclass(frozen=True)
class Descriptor:
    variable: str
    label: str
    multiple: bool
    values: tuple[str, ...]  # empty for numeric descriptors
    numeric: bool = False
    integer: bool = False

    def empty(self):
        return [] if self.multiple else None


@dataclass(frozen=True)
class Modality:
    key: str
    name: str
    descriptors: tuple[Descriptor, ...]

    def empty(self):
        return {d.variable: d.empty() for d in self.descriptors}


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _parse_values(raw):
    values = []
    for value in (v.strip() for v in raw.split(",")):
        match = _RANGE.fullmatch(value)
        if match:
            start, end = int(match["start"]), int(match["end"])
            values += [f"{match['prefix']}{i}" for i in range(start, end + 1)]
        elif value:
            values.append(value)
    return tuple(values)


def load_lexicon(path=LEXICON_FILE):
    """Return {modality_key: Modality} in file order."""
    modalities, current, descriptors = {}, None, []

    def flush():
        if current:
            modalities[_slug(current)] = Modality(_slug(current), current, tuple(descriptors))

    for line in Path(path).read_text(encoding="utf-8").splitlines():
        heading = _HEADING.match(line)
        if heading:
            flush()
            # "Contrast-Enhanced Mammography — recombined images" -> "Contrast-Enhanced Mammography"
            current, descriptors = heading["name"].split(" — ")[0].strip(), []
            continue
        match = _DESCRIPTOR.match(line)
        if not (current and match):
            continue
        raw = match["values"]
        if raw.startswith("number"):
            descriptor = Descriptor(
                match["variable"], match["label"], False, (), numeric=True, integer="whole" in raw
            )
        else:
            descriptor = Descriptor(
                match["variable"], match["label"], match["cardinality"] != "one", _parse_values(raw)
            )
        descriptors.append(descriptor)
    flush()
    return modalities


def lexicon_version(path=LEXICON_FILE):
    match = re.search(r"V\.?\d+(?:\.\d+)*", Path(path).stem)
    return match[0] if match else Path(path).stem
