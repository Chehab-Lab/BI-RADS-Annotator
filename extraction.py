"""Extract findings and BI-RADS descriptors from a report with the OpenAI API.

Uses Chat Completions with a strict JSON schema, so any OpenAI-compatible server
(set OPENAI_BASE_URL) can be swapped in later.
"""

import json

from openai import OpenAI

from lexicon import LEXICON_FILE

SYSTEM_PROMPT = """You are an expert breast radiologist annotating radiology reports with the ACR BI-RADS lexicon \
given below. For each modality the lexicon lists Exam_level descriptors, Finding_type descriptors and \
Characteristics (location of a finding).

Findings:
- Extract EVERY abnormality, lesion or positive observation described in the current imaging (masses, opacities, \
nodules, foci, calcifications, asymmetries, cysts, duct changes, skin changes, lymph nodes, enhancements, ...). \
Do not skip any; completeness matters as much as accuracy.
- A finding is one lesion in one imaging modality, with all of its attributes. Features described as belonging to \
or associated with that lesion are part of the same finding: e.g. a mass with associated skin thickening is ONE \
finding with both mass and skin_thickening filled, not two findings. Create a separate finding only for a separate \
lesion or abnormality. Indented descriptors belong to the item above them (e.g. mass shape and margin).
- If a lesion cannot be mapped to any Finding_type item with certainty (e.g. unspecified "foci" or a "slight \
over-opacity"), still create the finding: leave its Finding_type descriptors empty (false for Bool) and fill only \
what is stated, such as its Characteristics.
- Do not create findings for general descriptions of the breast tissue (e.g. "fibrous and fibrocystic changes", \
"involutive changes", "glandular-mixed type", density); they are not lesions and belong at most to the exam level.
- If the same lesion is described in several modalities, create one finding per modality.
- If one sentence describes several distinct lesions, create one finding per lesion.
- Fill the Characteristics (laterality, location, depth, distance from nipple, ...) of each finding from its own text.
- For each finding give its modality, the verbatim excerpt(s) of the report it is based on (copied exactly, \
character for character), and its descriptors.
- Assign each sentence to the modality whose section or sentence it belongs to (e.g. text under "Mammographically:" \
or a sentence starting "Ultrasound shows" belongs to that modality).
- Do not create findings for negative or normal statements (e.g. "No axillary lymphadenopathy", \
"Clear axillary regions", "No pathological calcifications"); ignore them.
- Bool descriptors are true only when that item is present in the finding; otherwise false.

Exam level:
- For each modality reported in the exam, fill only its Exam_level descriptors (e.g. breast density, background \
enhancement, overall assessment category). Use null for modalities not reported.

Strict evidence rules (most important):
- Every descriptor value must be supported by the finding's own excerpts. Every excerpt used must be listed in evidence.
- Never carry information across modalities: a finding's descriptors come only from that modality's text. \
E.g. if the MRI text says "the formation in the right breast", fill laterality = right but leave location and depth \
empty even if the ultrasound gave them.
- Do not fill finding descriptors from the conclusion/impression. The conclusion may only be used for the exam-level \
assessment_category of the modalities it names.
- Only use the allowed values. Map wording to a lexicon value only when the meaning is explicitly the same; do not add \
qualifiers the report does not state (e.g. "peripheral vascularization" is not "peripheral hypervascularity"). \
Calcifications described as "scattered" have the distribution diffuse.
- Do not infer a lesion type the report does not name (e.g. unspecified "foci" or "opacities" are not calcifications \
or masses unless stated). This only limits the descriptors: the finding itself must still be extracted.
- If the wording is ambiguous, contradictory, or would need clinical interpretation, leave the descriptor empty.
- Leave a descriptor empty (null, [] for lists, false for Bool) when the report does not state it. Never guess.
- Ignore information about prior exams and pathology results; only annotate the current imaging.

BI-RADS descriptor lexicon:
"""


def _descriptor_schema(descriptor):
    if descriptor.kind == "bool":
        return {"type": "boolean", "description": descriptor.label}
    if descriptor.kind == "number":
        return {"type": ["number", "null"], "description": descriptor.label}
    if descriptor.kind == "multi":
        return {
            "type": "array",
            "items": {"type": "string", "enum": list(descriptor.values)},
            "description": descriptor.label,
        }
    return {"type": ["string", "null"], "enum": [*descriptor.values, None], "description": descriptor.label}


def _object_schema(descriptors):
    return {
        "type": "object",
        "properties": {d.variable: _descriptor_schema(d) for d in descriptors},
        "required": [d.variable for d in descriptors],
        "additionalProperties": False,
    }


def _ref(name):
    return {"$ref": f"#/$defs/{name}"}


def _defs(modalities):
    defs = {}
    for m in modalities:
        defs[f"{m.key}_exam"] = _object_schema(m.exam)
        defs[f"{m.key}_finding"] = _object_schema(m.finding_descriptors())
    return defs


def report_schema(lexicon):
    findings = [
        {
            "type": "object",
            "properties": {
                "modality": {"type": "string", "enum": [m.key]},
                "evidence": {"type": "array", "items": {"type": "string"}},
                "descriptors": _ref(f"{m.key}_finding"),
            },
            "required": ["modality", "evidence", "descriptors"],
            "additionalProperties": False,
        }
        for m in lexicon.values()
    ]
    return {
        "type": "object",
        "properties": {
            "exam_level": {
                "type": "object",
                "properties": {k: {"anyOf": [_ref(f"{k}_exam"), {"type": "null"}]} for k in lexicon},
                "required": list(lexicon),
                "additionalProperties": False,
            },
            "findings": {"type": "array", "items": {"anyOf": findings}},
        },
        "required": ["exam_level", "findings"],
        "additionalProperties": False,
        "$defs": _defs(lexicon.values()),
    }


def finding_schema(modality):
    return {
        "type": "object",
        "properties": {"descriptors": _ref(f"{modality.key}_finding")},
        "required": ["descriptors"],
        "additionalProperties": False,
        "$defs": {f"{modality.key}_finding": _object_schema(modality.finding_descriptors())},
    }


def clean_descriptors(descriptors, raw):
    """Keep only allowed values; fill missing descriptors with empty values."""
    raw = raw or {}
    cleaned = {}
    for d in descriptors:
        value = raw.get(d.variable)
        if d.kind == "bool":
            cleaned[d.variable] = value is True
        elif d.kind == "number":
            cleaned[d.variable] = (
                (int(round(value)) if d.integer else float(value))
                if isinstance(value, (int, float)) and not isinstance(value, bool)
                else None
            )
        elif d.kind == "multi":
            values = value if isinstance(value, list) else []
            cleaned[d.variable] = [v for v in d.values if v in values]
        else:
            cleaned[d.variable] = value if value in d.values else None
    return cleaned


def clean_finding(modality, raw):
    values = clean_descriptors(modality.finding_descriptors(), raw)
    for group in modality.groups():  # a filled sub-descriptor ticks its group
        if group.toggle and any(d.is_filled(values[d.variable]) for d in group.members):
            values[group.toggle.variable] = True
    return values


class Extractor:
    def __init__(self, lexicon, api_key, model, base_url=None):
        self.lexicon = lexicon
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url or None)
        self.system_prompt = SYSTEM_PROMPT + LEXICON_FILE.read_text(encoding="utf-8")

    def _complete(self, user_prompt, name, schema):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": name, "strict": True, "schema": schema},
            },
        )
        message = response.choices[0].message
        if getattr(message, "refusal", None):
            raise RuntimeError(f"The model refused: {message.refusal}")
        return json.loads(message.content)

    def extract_report(self, report):
        """One request: findings with modality and descriptors, plus exam-level descriptors per modality."""
        data = self._complete(f"Report:\n\n{report}", "birads_report", report_schema(self.lexicon))
        exam_level = {
            key: clean_descriptors(self.lexicon[key].exam, raw)
            for key, raw in (data.get("exam_level") or {}).items()
            if key in self.lexicon and raw is not None
        }
        findings = []
        for f in data.get("findings") or []:
            if f.get("modality") not in self.lexicon:
                continue
            finding = {
                "modality": f["modality"],
                "evidence": [e for e in f.get("evidence", []) if isinstance(e, str) and e.strip()],
                "descriptors": clean_finding(self.lexicon[f["modality"]], f.get("descriptors")),
            }
            if finding not in findings:  # drop exact duplicates (same modality, excerpts and values)
                findings.append(finding)
        return {"exam_level": exam_level, "findings": findings}

    def extract_finding(self, report, evidence, modality_key):
        """Re-extract the descriptors of one finding for the given modality."""
        modality = self.lexicon[modality_key]
        excerpts = "\n".join(f"- {e}" for e in evidence) or "- (no excerpt)"
        prompt = (
            f"Report:\n\n{report}\n\n"
            f"Extract the {modality.name} descriptors of this single finding only, "
            f"based on these excerpts of the report:\n{excerpts}"
        )
        data = self._complete(prompt, "birads_finding", finding_schema(modality))
        return clean_finding(modality, data.get("descriptors"))
