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
from lexicon import load_lexicon, lexicon_version

ROOT = Path(__file__).parent
LOGO = ROOT / "assets" / "logo.png"
PANEL_HEIGHT = 760
MODALITY_COLORS = {
    "mammography": "#fde68a",
    "ultrasound": "#a5f3fc",
    "mri": "#bbf7d0",
    "contrast_enhanced_mammography": "#ddd6fe",
}
NAV_EXAM, NAV_ADD = "exam", "add"

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

# Streamlit forgets the value of a widget that is not drawn in a run, and only the selected finding is drawn.
# Re-assigning the annotation values keeps them across navigation (buttons are excluded: they cannot be set).
_KEEP = re.compile(r"\|(finding:|exam:|modality\|)")
for _key in [k for k in state if isinstance(k, str) and k.startswith(f"{state.rev}|") and _KEEP.search(k)]:
    state[_key] = state[_key]


def widget_key(scope, variable):
    return f"{state.rev}|{scope}|{variable}"


def finding_scope(finding):
    # keyed by the stable uid: the displayed id changes when findings are removed
    return f"finding:{finding['uid']}:{finding['modality']}:{finding['frev']}"


def nav_key():
    return f"{state.rev}|nav"


def current_value(scope, descriptor, defaults):
    key = widget_key(scope, descriptor.variable)
    return state[key] if key in state else defaults.get(descriptor.variable, descriptor.empty())


def read_exam(modality_key, scope, defaults):
    """Current (possibly user-corrected) exam-level values of one modality."""
    return {d.variable: current_value(scope, d, defaults) for d in LEXICON[modality_key].exam}


def read_finding(modality_key, scope, defaults):
    """Current finding values: every attribute of the modality, as shown."""
    return {d.variable: current_value(scope, d, defaults) for d in LEXICON[modality_key].finding_descriptors()}


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
        return False
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    metadata, body = split_header(text.replace("\r\n", "\n"))
    state.report = {"file_name": uploaded.name, "metadata": metadata, "text": body, "hash": digest}
    state.result = None
    state.extract_error = None
    state.extract_pending = True  # extraction starts by itself after an upload
    state.rev += 1
    state.next_output_name = f"{Path(uploaded.name).stem}_annotation"  # applied before the field is drawn
    return True


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
        state.extract_error = f"Extraction failed: {error}"
        return
    state.extract_error = None
    for i, finding in enumerate(result["findings"], start=1):
        finding.update(id=i, uid=i, frev=0, error=None)
    result["next_uid"] = len(result["findings"]) + 1
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


def go_to(target):
    state[nav_key()] = target


def renumber_findings():
    for i, finding in enumerate(state.result["findings"], start=1):
        finding["id"] = i


def remove_finding(uid):
    findings = state.result["findings"]
    index = next(i for i, f in enumerate(findings) if f["uid"] == uid)
    del findings[index]
    renumber_findings()
    if findings:  # show the finding that took its place, or the new last one
        go_to(f"f:{findings[min(index, len(findings) - 1)]['uid']}")
    else:
        go_to(NAV_EXAM)


def add_finding(select_key, excerpt_key):
    """Append a finding; with an excerpt, its descriptors are extracted from it, otherwise left empty."""
    modality_key = state[select_key]
    excerpt = state.get(excerpt_key, "").strip()
    state[excerpt_key] = ""
    modality = LEXICON[modality_key]
    finding = {
        "uid": state.result["next_uid"],
        "modality": modality_key,
        "evidence": [excerpt] if excerpt else [],
        "descriptors": {d.variable: d.empty() for d in modality.finding_descriptors()},
        "frev": 0,
        "error": None,
    }
    state.result["next_uid"] += 1
    if excerpt:
        try:
            finding["descriptors"] = extractor().extract_finding(state.report["text"], [excerpt], modality_key)
        except Exception as error:
            finding["error"] = f"Extraction failed, fill the descriptors manually: {error}"
    state.result["findings"].append(finding)
    renumber_findings()
    go_to(f"f:{finding['uid']}")


def remove_exam(modality_key):
    state.result["exam_level"].pop(modality_key, None)
    prefix = widget_key(f"exam:{modality_key}", "")
    for key in [k for k in state if isinstance(k, str) and k.startswith(prefix)]:
        del state[key]  # so a modality added back starts empty


def add_exam(select_key):
    modality_key = state.get(select_key)
    if modality_key and modality_key not in state.result["exam_level"]:
        state.result["exam_level"][modality_key] = {}


def exam_modalities():
    """Exam-level modality keys present in the result, in lexicon order."""
    return [k for k in LEXICON if k in state.result["exam_level"]]


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
                "descriptors": read_exam(key, f"exam:{key}", result["exam_level"][key]),
            }
            for key in exam_modalities()
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


def report_html(text, findings, selected_uid=None):
    """The report with each finding's excerpts highlighted; the selected finding stands out."""
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
            f'<sup class="badge{" sel" if f["uid"] == selected_uid else ""}">F{f["id"]}</sup>'
            for f in sorted({f["id"]: f for f in starts.get(a, [])}.values(), key=lambda f: f["id"])
        )
        covering = sorted({f["id"]: f for s, e, f in spans if s <= a and b <= e}.values(), key=lambda f: f["id"])
        chunk = html.escape(text[a:b])
        if covering:
            color = MODALITY_COLORS.get(covering[0]["modality"], "#e5e7eb")
            title = ", ".join(f"F{f['id']} · {LEXICON[f['modality']].name}" for f in covering)
            selected = selected_uid is not None and any(f["uid"] == selected_uid for f in covering)
            dim = selected_uid is not None and not selected
            cls = "sel" if selected else "dim" if dim else ""
            chunk = f'<mark class="{cls}" style="background:{color}" title="{html.escape(title)}">{chunk}</mark>'
        parts.append(badges + chunk)
    return f'<div class="report">{"".join(parts)}</div>'


def humanize(value):
    """Display form of a lexicon value: clock_10 -> 10 o'clock, heterogeneously_dense -> Heterogeneously dense."""
    if value is None:
        return "—"
    text = str(value)
    if text.startswith("clock_"):
        return f"{text[6:]} o'clock"
    text = text.replace("_", " ")
    return text[:1].upper() + text[1:]


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
            format="%d" if d.integer else "%.1f", help=d.variable, placeholder="Not stated",
        )
    elif d.kind == "multi":
        st.multiselect(d.label, d.values, key=key, format_func=humanize, help=d.variable, placeholder="Not stated")
    else:
        st.selectbox(
            d.label, [None, *d.values], key=key, format_func=humanize, help=d.variable, placeholder="Not stated"
        )


def descriptor_grid(scope, descriptors, defaults):
    """Value pickers in two columns, then checkboxes in three."""
    for kinds, n in (({"one", "multi", "number"}, 2), ({"bool"}, 3)):
        batch = [d for d in descriptors if d.kind in kinds]
        if batch:
            columns = st.columns(n)
            for i, d in enumerate(batch):
                with columns[i % n]:
                    descriptor_widget(scope, d, defaults)




def nav_label(option):
    if option == NAV_EXAM:
        return "Exam level"
    if option == NAV_ADD:
        return ":material/add:"
    return f"F{finding_by_nav(option)['id']}"


def finding_by_nav(option):
    uid = int(option.split(":", 1)[1])
    return next(f for f in state.result["findings"] if f["uid"] == uid)


def delete_button(key, on_click, args):
    """A delete icon behind a small confirmation, to prevent accidental removals."""
    with st.popover("", icon=":material/delete:", help="Delete"):
        st.button("Delete", key=key, on_click=on_click, args=args, type="primary")


def exam_view():
    for key in exam_modalities():
        head, action = st.columns([6, 1], vertical_alignment="center")
        head.markdown(f"**{LEXICON[key].name}**")
        with action:
            delete_button(f"{state.rev}|remove-exam|{key}", remove_exam, (key,))
        descriptor_grid(f"exam:{key}", LEXICON[key].exam, state.result["exam_level"][key])
        st.divider()
    missing = [k for k in LEXICON if k not in state.result["exam_level"]]
    if missing:
        with st.popover("Add modality", icon=":material/add:"):
            select_key = f"{state.rev}|add-exam"
            st.selectbox("Modality", missing, key=select_key, format_func=lambda k: LEXICON[k].name)
            st.button("Add", key=f"{state.rev}|add-exam-button", on_click=add_exam, args=(select_key,),
                      type="primary")


def finding_view(finding):
    scope = finding_scope(finding)
    title, modality_col, action = st.columns([1, 5, 1], vertical_alignment="bottom")
    title.markdown(f"### F{finding['id']}")
    modality_key = f"{state.rev}|modality|{finding['uid']}"
    if modality_key not in state:
        state[modality_key] = finding["modality"]
    modality_col.selectbox(
        "Modality", list(LEXICON), key=modality_key, format_func=lambda k: LEXICON[k].name,
        on_change=on_modality_change, args=(finding, modality_key),
        help="Changing the modality re-extracts this finding's attributes.",
    )
    with action:
        delete_button(f"{state.rev}|remove-finding|{finding['uid']}", remove_finding, (finding["uid"],))
    for excerpt in finding["evidence"]:
        st.markdown(f'<div class="evidence">{html.escape(excerpt)}</div>', unsafe_allow_html=True)
    if finding["error"]:
        st.error(finding["error"])
    descriptor_grid(scope, LEXICON[finding["modality"]].finding_descriptors(), finding["descriptors"])


def add_view():
    modality_key, excerpt_key = f"{state.rev}|add-finding-modality", f"{state.rev}|add-finding-excerpt"
    st.selectbox("Modality", list(LEXICON), key=modality_key, format_func=lambda k: LEXICON[k].name)
    st.text_area(
        "Report excerpt (optional)", key=excerpt_key, height=100,
        placeholder="Paste the sentence it is based on: it will be highlighted and its attributes pre-filled",
    )
    st.button("Add finding", key=f"{state.rev}|add-finding-button", icon=":material/add:", type="primary",
              on_click=add_finding, args=(modality_key, excerpt_key))


st.markdown(
    """
    <style>
    .block-container { padding-top: 2.5rem; }
    [data-testid="stButtonGroup"] > div { flex-wrap: wrap; row-gap: 6px; overflow-x: visible; }
    .report { white-space: pre-wrap; font-family: ui-serif, Georgia, serif; font-size: 1rem; line-height: 1.75; }
    .report mark { border-radius: 4px; padding: 1px 2px; color: inherit; }
    .report mark.dim { opacity: 0.45; }
    .report mark.sel { box-shadow: 0 0 0 2px #0e9aa7; }
    .report .badge { font-family: ui-sans-serif, system-ui; font-size: 0.65rem; font-weight: 700;
                     background: #6b7280; color: #fff; border-radius: 4px; padding: 0 4px; margin-right: 2px; }
    .report .badge.sel { background: #0e9aa7; }
    .metadata { display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 0.8rem; opacity: 0.75;
                padding-bottom: 8px; margin-bottom: 8px; border-bottom: 1px solid rgba(128, 128, 128, 0.3); }
    .evidence { border-left: 3px solid #0e9aa7; padding: 4px 10px; margin: 0 0 10px; font-style: italic;
                background: rgba(14, 154, 167, 0.06); border-radius: 0 6px 6px 0; }
    .footer { opacity: 0.8; font-size: 0.85rem; }
    .footer img { height: 22px; vertical-align: middle; margin-left: 4px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- title, download and settings ----------

annotator = state.get("annotator", "").strip()
title_col, download_col, settings_col = st.columns([12, 1, 1], vertical_alignment="center")
title_col.title("BI-RADS Annotator")
with download_col:
    ready = bool(state.result and annotator)
    st.download_button(
        "",
        data=json.dumps(export_json(annotator), indent=2, ensure_ascii=False) if ready else "",
        file_name=output_file_name(),
        mime="application/json",
        disabled=not ready,
        icon=":material/download:",
        help="Download JSON" if ready else "Download JSON (enter your name in settings first)",
    )
with settings_col:
    with st.popover("", icon=":material/settings:", help="Settings"):
        st.text_input("Annotator name", key="annotator", placeholder="Your name")
        if "next_output_name" in state:
            state.output_name = state.pop("next_output_name")
        state.setdefault("output_name", "annotation")
        st.text_input("Download file name", key="output_name", help="Saved as <name>.json")
        if st.button("Re-extract", icon=":material/refresh:", disabled=not state.report,
                     help="Runs the model again and replaces all corrections."):
            state.extract_pending = True
        logo_b64 = base64.b64encode(LOGO.read_bytes()).decode()
        st.markdown(
            f'<div class="footer">Made with ❤️ by <img src="data:image/png;base64,{logo_b64}" alt="logo"></div>',
            unsafe_allow_html=True,
        )

# ---------- report | findings ----------

report_col, findings_col = st.columns(2, gap="large")

with findings_col:
    nav = None
    if state.report and state.get("extract_pending"):
        state.extract_pending = False
        run_extraction()  # reruns the app on success, so the report is drawn with its highlights
    if state.result:
        options = [NAV_EXAM, *(f"f:{f['uid']}" for f in state.result["findings"]), NAV_ADD]
        if state.get(nav_key()) is None and state.get("last_nav") in options:
            state[nav_key()] = state.last_nav  # clicking the selected pill deselects it: keep it selected
        if state.get(nav_key()) not in options:
            first = options[1] if len(options) > 2 else NAV_EXAM
            state[nav_key()] = first
        nav = state.last_nav = state[nav_key()]
        st.pills("Findings", options, key=nav_key(), format_func=nav_label, label_visibility="collapsed")
        with st.container(height=PANEL_HEIGHT, border=True):
            if nav == NAV_EXAM:
                exam_view()
            elif nav == NAV_ADD:
                add_view()
            else:
                finding_view(finding_by_nav(nav))
    elif state.get("extract_error"):
        st.error(state.extract_error)
        if st.button("Retry", icon=":material/refresh:"):
            state.extract_pending = True
            st.rerun()
    else:
        st.caption("Findings appear here after you upload a report.")

selected = finding_by_nav(nav) if nav and nav.startswith("f:") else None

with report_col:
    uploaded = st.file_uploader("Upload a report (.txt)", type=["txt"], accept_multiple_files=False,
                                label_visibility="collapsed")
    if uploaded is not None:
        if load_report(uploaded):
            st.rerun()  # extract and draw the findings for the new report
    elif state.report:
        clear_report()
        st.rerun()
    if state.report:
        with st.container(height=PANEL_HEIGHT - 40, border=True):
            if state.report["metadata"]:
                st.html('<div class="metadata">' + "".join(
                    f"<span><b>{html.escape(k)}</b> {html.escape(v)}</span>"
                    for k, v in state.report["metadata"].items()
                ) + "</div>")
            findings = state.result["findings"] if state.result else []
            st.html(report_html(state.report["text"], findings, selected["uid"] if selected else None))
