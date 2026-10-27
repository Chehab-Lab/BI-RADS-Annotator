"""Load the BI-RADS descriptor lexicon from its Markdown definition file.

Per modality (`## Modality`) the file has three sections:
    ### Exam_level        descriptors that describe the whole exam
    ### Finding_type      descriptors of one finding; a top-level Bool item followed by
                          indented lines is a group (e.g. Mass -> Shape, Margin, Density)
    #### Characteristics  location of the finding
Descriptor lines look like:
    - Label — `variable` (one | multi | multiple | Bool): value_a, value_b, ...
"""

import re
from dataclasses import dataclass
from pathlib import Path

LEXICON_FILE = Path(__file__).parent / "lexicon" / "Descriptors_V.1.2.md"

_MODALITY = re.compile(r"^##\s+(?P<name>[^#].*?)\s*$")
_SECTION = re.compile(r"^\s*#{3,4}\s*(?P<name>\w+)")
_ITEM = re.compile(
    r"^(?P<indent>\s*)(?:-\s+)?(?P<label>.+?)\s*—\s*(?:`(?P<variable>\w+)`\s*)?"
    r"\((?P<kind>one|multi|multiple|Bool)\)(?::\s*(?P<values>.*?))?\s*$"
)
_HEADER = re.compile(r"^-\s+(?P<label>[^—`]+?):\s*$")  # "- Masses:" (group without variable)
_RANGE = re.compile(r"(?P<prefix>[a-z_]+?)(?P<start>\d+)\.\.(?P=prefix)(?P<end>\d+)")
_SECTIONS = {"exam_level": "exam", "finding_type": "finding", "characteristics": "characteristics"}


@dataclass(frozen=True)
class Descriptor:
    variable: str
    label: str
    kind: str  # "one" | "multi" | "bool" | "number"
    values: tuple[str, ...] = ()
    integer: bool = False

    def empty(self):
        return {"multi": [], "bool": False}.get(self.kind)

    def is_filled(self, value):
        return value not in (None, [], False)


@dataclass(frozen=True)
class Group:
    """A finding type with sub-descriptors (e.g. Mass -> Shape, Margin).

    `toggle` is the group's own Bool variable when the lexicon names one; otherwise the
    group is only a heading and nothing is exported for it.
    """

    label: str
    toggle: Descriptor | None
    members: tuple[Descriptor, ...]

    @property
    def key(self):
        return self.toggle.variable if self.toggle else _slug(self.label)


@dataclass(frozen=True)
class Modality:
    key: str
    name: str
    exam: tuple[Descriptor, ...]
    finding: tuple  # Descriptor | Group, in lexicon order
    characteristics: tuple[Descriptor, ...]

    def finding_descriptors(self):
        """Every exported finding variable, including group toggles and characteristics."""
        out = []
        for item in self.finding:
            if isinstance(item, Group):
                out += ([item.toggle] if item.toggle else []) + list(item.members)
            else:
                out.append(item)
        return out + list(self.characteristics)

    def groups(self):
        return [item for item in self.finding if isinstance(item, Group)]


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


def _descriptor(match):
    kind, raw = match["kind"], (match["values"] or "").strip()
    if kind == "Bool":
        return Descriptor(match["variable"], match["label"], "bool")
    if raw.startswith("number"):
        return Descriptor(match["variable"], match["label"], "number", integer="whole" in raw)
    return Descriptor(match["variable"], match["label"], "one" if kind == "one" else "multi", _parse_values(raw))


def load_lexicon(path=LEXICON_FILE):
    """Return {modality_key: Modality} in file order."""
    modalities = {}
    name, section, parts = None, None, None

    def flush():
        if not name:
            return
        finding = []
        for item in parts["finding"]:
            if isinstance(item, dict):  # group header: a Group if it has members
                if item["members"]:
                    finding.append(Group(item["label"], item["toggle"], tuple(item["members"])))
                elif item["toggle"]:
                    finding.append(item["toggle"])
            else:
                finding.append(item)
        key = _slug(name)
        modalities[key] = Modality(
            key, name, tuple(parts["exam"]), tuple(finding), tuple(parts["characteristics"])
        )

    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        modality = _MODALITY.match(line)
        if modality:
            flush()
            # "Contrast-Enhanced Mammography — recombined images" -> "Contrast-Enhanced Mammography"
            name = modality["name"].split(" — ")[0].strip()
            section, parts = None, {"exam": [], "finding": [], "characteristics": []}
            continue
        heading = _SECTION.match(line)
        if heading:
            section = _SECTIONS.get(heading["name"].lower(), section)
            continue
        if not (name and section):
            continue
        target = parts[section]
        item, header = _ITEM.match(line), _HEADER.match(line)
        if item and item["indent"] and section == "finding" and target and isinstance(target[-1], dict):
            if item["variable"]:
                target[-1]["members"].append(_descriptor(item))
        elif item and section == "finding" and item["kind"] == "Bool":
            toggle = _descriptor(item) if item["variable"] else None
            target.append({"label": item["label"], "toggle": toggle, "members": []})
        elif item and item["variable"]:
            target.append(_descriptor(item))
        elif header and section == "finding":
            target.append({"label": header["label"], "toggle": None, "members": []})
    flush()
    return modalities


def lexicon_version(path=LEXICON_FILE):
    match = re.search(r"V\.?\d+(?:\.\d+)*", Path(path).stem)
    return match[0] if match else Path(path).stem
