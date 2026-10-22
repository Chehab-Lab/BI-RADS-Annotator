"""Extract findings and BI-RADS descriptors from a report with the OpenAI API.

Uses Chat Completions with a strict JSON schema, so any OpenAI-compatible server
(set OPENAI_BASE_URL) can be swapped in later.
"""

import json

from openai import OpenAI

from lexicon import LEXICON_FILE

SYSTEM_PROMPT = """You are an expert breast radiologist annotating radiology reports with the ACR BI-RADS lexicon.

Findings:
- A finding is one lesion or abnormality described in one imaging modality. If the same lesion is described in \
several modalities (e.g. a mammographic opacity that corresponds to an ultrasound mass), create one finding per modality.
- If one sentence describes several distinct lesions, create one finding per lesion.
- For each finding give its modality, the verbatim excerpt(s) of the report it is based on (copied exactly, \
character for character), and its descriptors.
- Assign each sentence to the modality whose section or sentence it belongs to (e.g. text under "Mammographically:" \
or a sentence starting "Ultrasound shows" belongs to that modality).

Exam level:
- For each modality reported in the exam, fill the exam-level descriptors: statements about the breasts or the \
exam as a whole rather than one finding (e.g. breast density, background enhancement, overall assessment category), \
and negative statements (e.g. "No axillary lymphadenopathy" -> lymph_node_axillary = normal, \
"no architectural distortion" -> architectural_distortion = absent). Use null for modalities not reported.

Strict evidence rules (most important):
- Every descriptor value must be supported by the finding's own excerpts. Every excerpt used must be listed in evidence.
- Never carry information across modalities: a finding's descriptors come only from that modality's text. \
E.g. if the MRI text says "the formation in the right breast", fill laterality = right but leave location and depth \
empty even if the ultrasound gave them.
- Do not fill finding descriptors from the conclusion/impression, except assessment_category when the conclusion \
explicitly assigns a BI-RADS category to that finding or to the modalities it names.
- Only use the allowed values. Map wording to a lexicon value only when the meaning is explicitly the same; do not add \
qualifiers the report does not state (e.g. "peripheral vascularization" is not "peripheral hypervascularity").
- Do not infer a lesion type the report does not name (e.g. unspecified "foci" or "opacities" are not calcifications \
or masses unless stated).
- If the wording is ambiguous, contradictory, or would need clinical interpretation, leave the descriptor empty.
- Leave a descriptor empty (null, or [] for lists) when the report does not state it. Never guess.
- Ignore information about prior exams and pathology results; only annotate the current imaging.

BI-RADS descriptor lexicon:
"""


def _descriptor_schema(descriptor):
    if descriptor.numeric:
        return {"type": ["number", "null"], "description": descriptor.label}
    if descriptor.multiple:
        return {
            "type": "array",
            "items": {"type": "string", "enum": list(descriptor.values)},
            "description": descriptor.label,
        }
    return {"type": ["string", "null"], "enum": [*descriptor.values, None], "description": descriptor.label}


def _modality_schema(modality):
    return {
        "type": "object",
        "properties": {d.variable: _descriptor_schema(d) for d in modality.descriptors},
        "required": [d.variable for d in modality.descriptors],
        "additionalProperties": False,
    }


def _ref(modality):
    return {"$ref": f"#/$defs/{modality.key}"}


def report_schema(lexicon):
    findings = [
        {
            "type": "object",
            "properties": {
                "modality": {"type": "string", "enum": [m.key]},
                "evidence": {"type": "array", "items": {"type": "string"}},
                "descriptors": _ref(m),
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
                "properties": {k: {"anyOf": [_ref(m), {"type": "null"}]} for k, m in lexicon.items()},
                "required": list(lexicon),
                "additionalProperties": False,
            },
            "findings": {"type": "array", "items": {"anyOf": findings}},
        },
        "required": ["exam_level", "findings"],
        "additionalProperties": False,
        "$defs": {k: _modality_schema(m) for k, m in lexicon.items()},
    }


def finding_schema(modality):
    return {
        "type": "object",
        "properties": {"descriptors": _ref(modality)},
        "required": ["descriptors"],
        "additionalProperties": False,
        "$defs": {modality.key: _modality_schema(modality)},
    }


def clean_descriptors(modality, raw):
    """Keep only allowed values; fill missing descriptors with empty values."""
    raw = raw or {}
    cleaned = {}
    for d in modality.descriptors:
        value = raw.get(d.variable)
        if d.numeric:
            cleaned[d.variable] = (
                (int(round(value)) if d.integer else float(value))
                if isinstance(value, (int, float)) and not isinstance(value, bool)
                else None
            )
        elif d.multiple:
            values = value if isinstance(value, list) else []
            cleaned[d.variable] = [v for v in d.values if v in values]
        else:
            cleaned[d.variable] = value if value in d.values else None
    return cleaned


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
            key: clean_descriptors(self.lexicon[key], raw)
            for key, raw in (data.get("exam_level") or {}).items()
            if key in self.lexicon and raw is not None
        }
        findings = [
            {
                "modality": f["modality"],
                "evidence": [e for e in f.get("evidence", []) if isinstance(e, str) and e.strip()],
                "descriptors": clean_descriptors(self.lexicon[f["modality"]], f.get("descriptors")),
            }
            for f in data.get("findings") or []
            if f.get("modality") in self.lexicon
        ]
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
        return clean_descriptors(modality, data.get("descriptors"))
