import base64
import hashlib
import html
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from extraction import Extractor
from lexicon import Group, load_lexicon, lexicon_version

ROOT = Path(__file__).parent
LOGO = ROOT / "assets" / "logo.png"
PANEL_HEIGHT = 680
MODALITY_COLORS = {
    "mammography": "#fde68a",
    "ultrasound": "#a5f3fc",
    "mri": "#bbf7d0",
    "contrast_enhanced_mammography": "#ddd6fe",
}

st.set_page_config(page_title="BI-RADS Annotator", page_icon=str(LOGO), layout="wide")


@st.cache_resource
def get_lexicon():
    return load_lexicon()


LEXICON = get_lexicon()


def setting(name, default=None):
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:  # no secrets file
        pass
    return os.environ.get(name, default)


@st.cache_resource
def get_extractor(api_key, model, base_url):
    return Extractor(LEXICON, api_key, model, base_url)


def extractor():
    api_key = setting("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set (environment variable or .streamlit/secrets.toml).")
    return get_extractor(api_key, setting("OPENAI_MODEL", "gpt-5.6-sol"), setting("OPENAI_BASE_URL"))


# ---------- state ----------

state = st.session_state
state.setdefault("report", None)  # {"file_name", "text", "hash"}
state.setdefault("result", None)  # {"exam_level": {...}, "findings": [...], "model": str}
state.setdefault("rev", 0)  # bumped on every full extraction so widgets reset


def widget_key(scope, variable):
    return f"{state.rev}|{scope}|{variable}"


def finding_scope(finding):
    return f"finding:{finding['id']}:{finding['modality']}:{finding['frev']}"


def current_value(scope, descriptor, defaults):
    key = widget_key(scope, descriptor.variable)
    return state[key] if key in state else defaults.get(descriptor.variable, descriptor.empty())


def group_key(scope, group):
    return widget_key(scope, group.toggle.variable if group.toggle else f"group:{group.key}")


def group_on(scope, group, defaults):
    key = group_key(scope, group)
    if key in state:
        return state[key]
    if group.toggle:
        return bool(defaults.get(group.toggle.variable))
    return any(d.is_filled(defaults.get(d.variable, d.empty())) for d in group.members)


def read_exam(modality_key, scope, defaults):
    """Current (possibly user-corrected) exam-level values of one modality."""
    return {d.variable: current_value(scope, d, defaults) for d in LEXICON[modality_key].exam}


def read_finding(modality_key, scope, defaults):
    """Current finding values; sub-descriptors of an unticked group are exported empty."""
    modality = LEXICON[modality_key]
    values = {}
    for item in modality.finding:
        if isinstance(item, Group):
            on = group_on(scope, item, defaults)
            if item.toggle:
                values[item.toggle.variable] = on
            for d in item.members:
                values[d.variable] = current_value(scope, d, defaults) if on else d.empty()
        else:
            values[item.variable] = current_value(scope, item, defaults)
    for d in modality.characteristics:
        values[d.variable] = current_value(scope, d, defaults)
    return values


# ---------- actions ----------

_HEADER_LINE = re.compile(r"^(?P<key>[A-Za-z_][\w ]*):\s*(?P<value>.*)$")


def split_header(text):
    """Split an optional metadata header ("---" / "key: value" lines / "---") from the report text."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text
    metadata = {}
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return metadata, "\n".join(lines[i + 1:]).strip("\n")
        match = _HEADER_LINE.match(line.strip())
        if not match:
            break
        metadata[match["key"].strip()] = match["value"].strip()
    return {}, text


def load_report(uploaded):
    raw = uploaded.getvalue()
    digest = hashlib.sha256(raw).hexdigest()
    if state.report and state.report["hash"] == digest and state.report["file_name"] == uploaded.name:
        return
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    metadata, body = split_header(text.replace("\r\n", "\n"))
    state.report = {"file_name": uploaded.name, "metadata": metadata, "text": body, "hash": digest}
    state.result = None
    state.rev += 1
    state.output_name = f"{Path(uploaded.name).stem}_annotation"


def clear_report():
    state.report = None
    state.result = None
    state.rev += 1


def output_file_name():
    name = re.sub(r'[\\/:*?"<>|]+', "_", state.get("output_name", "").strip())
    name = re.sub(r"\.json$", "", name, flags=re.IGNORECASE) or "annotation"
    return f"{name}.json"


def run_extraction():
    try:
        with st.spinner("Extracting findings and descriptors…"):
            ex = extractor()
            result = ex.extract_report(state.report["text"])
    except Exception as error:
        st.error(f"Extraction failed: {error}")
        return
    for i, finding in enumerate(result["findings"], start=1):
        finding.update(id=i, frev=0, error=None)
    result["model"] = ex.model
    state.result = result
    state.rev += 1
    st.rerun()  # the report panel was already drawn without highlights


def on_modality_change(finding, key):
    new_modality = state.get(key, finding["modality"])
    if new_modality == finding["modality"]:
        return
    finding["modality"] = new_modality
    finding["frev"] += 1
    finding["error"] = None
    try:
        finding["descriptors"] = extractor().extract_finding(
            state.report["text"], finding["evidence"], new_modality
        )
    except Exception as error:
        finding["descriptors"] = {d.variable: d.empty() for d in LEXICON[new_modality].finding_descriptors()}
        finding["error"] = f"Re-extraction failed: {error}"


def export_json(annotator):
    result = state.result
    return {
        "annotator": annotator,
        "download_date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lexicon_version": lexicon_version(),
        "model": result["model"],
        "report": {
            "file_name": state.report["file_name"],
            "metadata": state.report["metadata"],
            "text": state.report["text"],
        },
        "exam_level": [
            {
                "modality": LEXICON[key].name,
                "descriptors": read_exam(key, f"exam:{key}", defaults),
            }
            for key, defaults in result["exam_level"].items()
        ],
        "findings": [
            {
                "id": f["id"],
                "modality": LEXICON[f["modality"]].name,
                "evidence": f["evidence"],
                "descriptors": read_finding(f["modality"], finding_scope(f), f["descriptors"]),
            }
            for f in result["findings"]
        ],
    }


# ---------- rendering ----------

def find_spans(text, excerpt):
    """Locate an excerpt in the report, tolerating whitespace differences."""
    words = excerpt.split()
    if not words:
        return []
    pattern = r"\s+".join(re.escape(w) for w in words)
    return [m.span() for m in re.finditer(pattern, text, flags=re.IGNORECASE)]


def report_html(text, findings):
    spans = []  # (start, end, finding)
    for f in findings:
        for excerpt in f["evidence"]:
            spans += [(s, e, f) for s, e in find_spans(text, excerpt)]
    if not spans:
        return f'<div class="report">{html.escape(text)}</div>'

    bounds = sorted({0, len(text), *(s for s, _, _ in spans), *(e for _, e, _ in spans)})
    starts = {}
    for s, _, f in spans:
        starts.setdefault(s, []).append(f)
    parts = []
    for a, b in zip(bounds, bounds[1:]):
        badges = "".join(
            f'<sup class="badge">F{f["id"]}</sup>'
            for f in sorted({f["id"]: f for f in starts.get(a, [])}.values(), key=lambda f: f["id"])
        )
        covering = sorted({f["id"]: f for s, e, f in spans if s <= a and b <= e}.values(), key=lambda f: f["id"])
        chunk = html.escape(text[a:b])
        if covering:
            color = MODALITY_COLORS.get(covering[0]["modality"], "#e5e7eb")
            title = ", ".join(f"F{f['id']} · {LEXICON[f['modality']].name}" for f in covering)
            chunk = f'<mark style="background:{color}" title="{html.escape(title)}">{chunk}</mark>'
        parts.append(badges + chunk)
    return f'<div class="report">{"".join(parts)}</div>'


def fmt(value):
    return "—" if value is None else value


def descriptor_widget(scope, d, defaults):
    key = widget_key(scope, d.variable)
    if key not in state:
        default = defaults.get(d.variable, d.empty())
        state[key] = list(default) if d.kind == "multi" else default
    if d.kind == "bool":
        st.checkbox(d.label, key=key, help=d.variable)
    elif d.kind == "number":
        st.number_input(
            d.label, key=key, min_value=0 if d.integer else 0.0, step=1 if d.integer else 0.1,
            format="%d" if d.integer else "%.1f", help=d.variable, placeholder="—",
        )
    elif d.kind == "multi":
        st.multiselect(d.label, d.values, key=key, help=d.variable, placeholder="—")
    else:
        st.selectbox(d.label, [None, *d.values], key=key, format_func=fmt, help=d.variable, placeholder="—")


def descriptor_grid(scope, descriptors, defaults):
    """Value pickers in two columns, then checkboxes in three."""
    for kinds, n in (({"one", "multi", "number"}, 2), ({"bool"}, 3)):
        batch = [d for d in descriptors if d.kind in kinds]
        if batch:
            columns = st.columns(n)
            for i, d in enumerate(batch):
                with columns[i % n]:
                    descriptor_widget(scope, d, defaults)


def exam_widgets(modality_key, scope, defaults):
    descriptor_grid(scope, LEXICON[modality_key].exam, defaults)


def finding_widgets(modality_key, scope, defaults):
    modality = LEXICON[modality_key]
    st.markdown("**Finding type**")
    pending = []  # consecutive plain descriptors, rendered together
    for item in [*modality.finding, None]:
        if isinstance(item, Group) or item is None:
            descriptor_grid(scope, pending, defaults)
            pending = []
        else:
            pending.append(item)
            continue
        if item is None:
            break
        key = group_key(scope, item)
        if key not in state:
            state[key] = group_on(scope, item, defaults)
        if st.toggle(item.label, key=key, help=item.toggle.variable if item.toggle else None):
            with st.container(border=True):
                descriptor_grid(scope, item.members, defaults)
    st.markdown("**Characteristics**")
    descriptor_grid(scope, modality.characteristics, defaults)


def filled_count(values):
    return sum(1 for v in values.values() if v not in (None, [], False))


st.markdown(
    """
    <style>
    .report { white-space: pre-wrap; font-family: ui-serif, Georgia, serif; font-size: 0.98rem; line-height: 1.6; }
    .report mark { border-radius: 3px; padding: 0 1px; color: inherit; }
    .report .badge { font-family: ui-sans-serif, system-ui; font-size: 0.65rem; font-weight: 700;
                     background: #1f2937; color: #fff; border-radius: 4px; padding: 0 3px; margin-right: 2px; }
    .metadata { display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 0.8rem; opacity: 0.8;
                padding-bottom: 8px; border-bottom: 1px solid rgba(128, 128, 128, 0.3); }
    .evidence { border-left: 3px solid #9ca3af; padding: 2px 8px; margin: 2px 0 6px; font-style: italic; opacity: 0.9; }
    .footer { text-align: center; margin-top: 2rem; opacity: 0.85; font-size: 0.95rem; }
    .footer img { height: 32px; vertical-align: middle; margin-left: 6px; }
    </style>
    """,
    unsafe_allow_html=True,
)

title_col, name_col = st.columns([3, 1], vertical_alignment="bottom")
with title_col:
    st.title("BI-RADS Annotator")
with name_col:
    annotator = st.text_input("Annotator name", key="annotator", placeholder="Your name")

report_col, annotation_col = st.columns(2, gap="large")

with report_col:
    st.subheader("Report")
    uploaded = st.file_uploader("Upload a report (.txt)", type=["txt"], accept_multiple_files=False)
    if uploaded is not None:
        load_report(uploaded)
    elif state.report:
        clear_report()
    with st.container(height=PANEL_HEIGHT, border=True):
        if state.report:
            if state.report["metadata"]:
                st.html(
                    '<div class="metadata">'
                    + "".join(
                        f"<span><b>{html.escape(k)}</b> {html.escape(v)}</span>"
                        for k, v in state.report["metadata"].items()
                    )
                    + "</div>"
                )
            findings = state.result["findings"] if state.result else []
            st.html(report_html(state.report["text"], findings))
        else:
            st.caption("Upload a text report to view it here.")

with annotation_col:
    st.subheader("BI-RADS descriptors")
    label = "Re-extract" if state.result else "Extract descriptors"
    if st.button(label, type="primary", disabled=not state.report, use_container_width=True):
        run_extraction()
    name_col, download_col = st.columns([3, 2], vertical_alignment="bottom")
    with name_col:
        state.setdefault("output_name", "annotation")
        st.text_input("Download file name", key="output_name", help="Saved as <name>.json")
    with download_col:
        ready = bool(state.result and annotator.strip())
        st.download_button(
            "Download results (JSON)",
            data=json.dumps(export_json(annotator.strip()), indent=2, ensure_ascii=False) if ready else "",
            file_name=output_file_name(),
            mime="application/json",
            disabled=not ready,
            use_container_width=True,
        )
    # always render the caption so later elements (the tabs) keep their identity across reruns
    st.caption("Enter your name to enable the download." if state.result and not annotator.strip() else "&nbsp;")

    with st.container(height=PANEL_HEIGHT - 60, border=True):
        if not state.result:
            st.caption("Upload a report and click **Extract descriptors**.")
        else:
            exam_tab, findings_tab = st.tabs(
                [f"Exam level ({len(state.result['exam_level'])})", f"Findings ({len(state.result['findings'])})"]
            )
            with exam_tab:
                if not state.result["exam_level"]:
                    st.caption("No modality-level descriptors were extracted.")
                for key, defaults in state.result["exam_level"].items():
                    scope = f"exam:{key}"
                    filled = filled_count(read_exam(key, scope, defaults))
                    with st.expander(f"{LEXICON[key].name} · {filled} filled", expanded=True):
                        exam_widgets(key, scope, defaults)
            with findings_tab:
                if not state.result["findings"]:
                    st.caption("No findings were extracted.")
                for finding in state.result["findings"]:
                    scope = finding_scope(finding)
                    filled = filled_count(read_finding(finding["modality"], scope, finding["descriptors"]))
                    name = LEXICON[finding["modality"]].name
                    with st.expander(f"F{finding['id']} · {name} · {filled} filled", expanded=True):
                        for excerpt in finding["evidence"]:
                            st.markdown(f'<div class="evidence">{html.escape(excerpt)}</div>', unsafe_allow_html=True)
                        modality_key = f"{state.rev}|modality|{finding['id']}"
                        if modality_key not in state:
                            state[modality_key] = finding["modality"]
                        st.selectbox(
                            "Modality",
                            list(LEXICON),
                            key=modality_key,
                            format_func=lambda k: LEXICON[k].name,
                            on_change=on_modality_change,
                            args=(finding, modality_key),
                            help="Changing the modality re-extracts this finding's descriptors.",
                        )
                        if finding["error"]:
                            st.error(finding["error"])
                        finding_widgets(finding["modality"], scope, finding["descriptors"])

logo_b64 = base64.b64encode(LOGO.read_bytes()).decode()
st.markdown(
    f'<div class="footer">Made with ❤️ by <img src="data:image/png;base64,{logo_b64}" alt="logo"></div>',
    unsafe_allow_html=True,
)
