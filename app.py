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
PANEL_HEIGHT = 720
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
_KEEP = re.compile(r"\|(finding:|exam:|reviewed\||modality\|)")
for _key in [k for k in state if isinstance(k, str) and k.startswith(f"{state.rev}|") and _KEEP.search(k)]:
    state[_key] = state[_key]


def widget_key(scope, variable):
    return f"{state.rev}|{scope}|{variable}"


def finding_scope(finding):
    # keyed by the stable uid: the displayed id changes when findings are removed
    return f"finding:{finding['uid']}:{finding['modality']}:{finding['frev']}"


def nav_key():
    return f"{state.rev}|nav"


def reviewed_key(finding):
    return f"{state.rev}|reviewed|{finding['uid']}"


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


def review_and_next(finding, target):
    state[reviewed_key(finding)] = True
    go_to(target)


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
        return ":material/add: Add"
    finding = finding_by_nav(option)
    check = ":material/check_circle: " if state.get(reviewed_key(finding)) else ""
    return f"{check}F{finding['id']} · {LEXICON[finding['modality']].name}"


def finding_by_nav(option):
    uid = int(option.split(":", 1)[1])
    return next(f for f in state.result["findings"] if f["uid"] == uid)


def confirm_delete(label, key, on_click, args):
    """A delete action behind a small confirmation popover, to prevent accidental removals."""
    with st.popover(label, icon=":material/delete:"):
        st.caption("This cannot be undone.")
        st.button("Delete", key=key, on_click=on_click, args=args, type="primary", use_container_width=True)


def exam_view():
    if not state.result["exam_level"]:
        st.info("No exam-level descriptors were extracted. Add a modality below if the report has one.")
    for key in exam_modalities():
        scope = f"exam:{key}"
        with st.container(border=True):
            head, action = st.columns([2.5, 1.2], vertical_alignment="center")
            head.markdown(f"**{LEXICON[key].name}**")
            with action:
                confirm_delete("Remove", f"{state.rev}|remove-exam|{key}", remove_exam, (key,))
            descriptor_grid(scope, LEXICON[key].exam, state.result["exam_level"][key])
    missing = [k for k in LEXICON if k not in state.result["exam_level"]]
    footer = st.columns([1, 1], vertical_alignment="center")
    if missing:
        with footer[0].popover("Add modality", icon=":material/add:"):
            select_key = f"{state.rev}|add-exam"
            st.selectbox("Modality", missing, key=select_key, format_func=lambda k: LEXICON[k].name)
            st.button("Add", key=f"{state.rev}|add-exam-button", on_click=add_exam, args=(select_key,),
                      type="primary", use_container_width=True)
    findings = state.result["findings"]
    if findings:
        footer[1].button(
            "Review findings", key=f"{state.rev}|to-findings", icon=":material/arrow_forward:", type="primary",
            on_click=go_to, args=(f"f:{findings[0]['uid']}",), use_container_width=True,
        )


def finding_view(finding):
    findings = state.result["findings"]
    index = findings.index(finding)
    modality = LEXICON[finding["modality"]]
    scope = finding_scope(finding)
    defaults = finding["descriptors"]

    head, reviewed = st.columns([2, 1], vertical_alignment="center")
    head.markdown(f"#### F{finding['id']} <span class='muted'>of {len(findings)}</span>", unsafe_allow_html=True)
    reviewed.toggle("Reviewed", key=reviewed_key(finding))

    if finding["evidence"]:
        for excerpt in finding["evidence"]:
            st.markdown(f'<div class="evidence">{html.escape(excerpt)}</div>', unsafe_allow_html=True)
    else:
        st.caption("No report excerpt (added by hand).")

    modality_key = f"{state.rev}|modality|{finding['uid']}"
    if modality_key not in state:
        state[modality_key] = finding["modality"]
    st.selectbox(
        "Modality", list(LEXICON), key=modality_key, format_func=lambda k: LEXICON[k].name,
        on_change=on_modality_change, args=(finding, modality_key),
        help="Changing the modality re-extracts this finding's descriptors.",
    )
    if finding["error"]:
        st.error(finding["error"])

    values = read_finding(finding["modality"], scope, defaults)
    filled = [  # a one-line readout of what is filled, to check at a glance
        f"{d.label}: {', '.join(map(humanize, v)) if isinstance(v, list) else 'yes' if v is True else humanize(v)}"
        for d in modality.finding_descriptors()
        if d.is_filled(v := values[d.variable])
    ]
    st.html('<div class="chips">' + ("".join(f'<span class="chip">{html.escape(c)}</span>' for c in filled)
            or '<span class="chip">Nothing filled yet</span>') + "</div>")

    st.markdown("**Descriptors**")
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

    st.divider()
    previous = f"f:{findings[index - 1]['uid']}" if index > 0 else NAV_EXAM
    following = f"f:{findings[index + 1]['uid']}" if index + 1 < len(findings) else None
    delete, back, forward = st.columns([1, 1, 1.7])
    with delete:
        confirm_delete("Delete", f"{state.rev}|remove-finding|{finding['uid']}", remove_finding, (finding["uid"],))
    back.button(
        "Previous", key=f"{state.rev}|prev|{finding['uid']}", icon=":material/arrow_back:",
        on_click=go_to, args=(previous,), use_container_width=True,
    )
    forward.button(
        "Mark reviewed & next" if following else "Mark reviewed",
        key=f"{state.rev}|next|{finding['uid']}", icon=":material/check:", type="primary",
        on_click=review_and_next, args=(finding, following or f"f:{finding['uid']}"), use_container_width=True,
    )


def add_view():
    st.markdown("#### Add a finding")
    st.caption("Use this for a finding the model missed.")
    modality_key, excerpt_key = f"{state.rev}|add-finding-modality", f"{state.rev}|add-finding-excerpt"
    st.selectbox("Modality", list(LEXICON), key=modality_key, format_func=lambda k: LEXICON[k].name)
    st.text_area(
        "Report excerpt (optional)", key=excerpt_key, height=100,
        placeholder="Paste the sentence it is based on: it will be highlighted and its descriptors pre-filled",
    )
    st.button("Add finding", key=f"{state.rev}|add-finding-button", icon=":material/add:", type="primary",
              on_click=add_finding, args=(modality_key, excerpt_key))


st.markdown(
    """
    <style>
    .block-container { padding-top: 3.2rem; }
    [data-testid="stButtonGroup"] > div { flex-wrap: wrap; row-gap: 6px; overflow-x: visible; }
    .report { white-space: pre-wrap; font-family: ui-serif, Georgia, serif; font-size: 1rem; line-height: 1.75; }
    .report mark { border-radius: 4px; padding: 1px 2px; color: inherit; transition: opacity .15s; }
    .report mark.dim { opacity: 0.45; }
    .report mark.sel { box-shadow: 0 0 0 2px #0e9aa7; }
    .report .badge { font-family: ui-sans-serif, system-ui; font-size: 0.65rem; font-weight: 700;
                     background: #6b7280; color: #fff; border-radius: 4px; padding: 0 4px; margin-right: 2px; }
    .report .badge.sel { background: #0e9aa7; }
    .chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; font-size: 0.78rem; }
    .chip { border-radius: 999px; padding: 1px 10px; background: rgba(128, 128, 128, 0.12); }
    .legend { display: flex; flex-wrap: wrap; gap: 12px; font-size: 0.78rem; opacity: 0.8; margin-top: 6px; }
    .legend i { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 4px; }
    .evidence { border-left: 3px solid #0e9aa7; padding: 4px 10px; margin: 0 0 10px; font-style: italic;
                background: rgba(14, 154, 167, 0.06); border-radius: 0 6px 6px 0; }
    .muted { opacity: 0.55; font-weight: 400; font-size: 0.9rem; }
    .step { font-size: 0.72rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase;
            opacity: 0.6; margin: 0.4rem 0 -0.3rem; }
    .footer { text-align: center; opacity: 0.8; font-size: 0.85rem; }
    .footer img { height: 26px; vertical-align: middle; margin-left: 6px; }
    </style>
    """,
    unsafe_allow_html=True,
)


def step(number, title):
    st.markdown(f'<div class="step">{number} · {title}</div>', unsafe_allow_html=True)


# ---------- sidebar: the workflow, one step after the other ----------

with st.sidebar:
    st.markdown("## BI-RADS Annotator")
    step(1, "Report")
    uploaded = st.file_uploader("Upload a report (.txt)", type=["txt"], accept_multiple_files=False)
    if uploaded is not None:
        load_report(uploaded)
    elif state.report:
        clear_report()

    step(2, "Extract")
    if st.button(
        "Re-extract" if state.result else "Extract descriptors",
        type="secondary" if state.result else "primary", disabled=not state.report,
        icon=":material/auto_awesome:", use_container_width=True,
        help="Re-extracting replaces all your corrections." if state.result else None,
    ):
        run_extraction()

    step(3, "Review")
    if state.result and state.result["findings"]:
        done = sum(bool(state.get(reviewed_key(f))) for f in state.result["findings"])
        total = len(state.result["findings"])
        st.progress(done / total, text=f"{done} of {total} findings reviewed")
    else:
        st.caption("Check the exam level and each finding against the report.")

    step(4, "Download")
    annotator = st.text_input("Annotator name", key="annotator", placeholder="Your name")
    state.setdefault("output_name", "annotation")
    st.text_input("File name", key="output_name", help="Saved as <name>.json")
    ready = bool(state.result and annotator.strip())
    st.download_button(
        "Download JSON",
        data=json.dumps(export_json(annotator.strip()), indent=2, ensure_ascii=False) if ready else "",
        file_name=output_file_name(),
        mime="application/json",
        disabled=not ready,
        type="primary" if ready else "secondary",
        icon=":material/download:",
        use_container_width=True,
    )
    if state.result and not annotator.strip():
        st.caption("Enter your name to enable the download.")

    logo_b64 = base64.b64encode(LOGO.read_bytes()).decode()
    st.divider()
    st.markdown(
        f'<div class="footer">Made with ❤️ by <img src="data:image/png;base64,{logo_b64}" alt="logo"></div>',
        unsafe_allow_html=True,
    )


# ---------- main: report and review side by side ----------

if not state.report:
    st.markdown("### Start by uploading a report")
    st.caption(
        "Upload a `.txt` report in the sidebar, then extract its BI-RADS descriptors. "
        "You review the exam level and each finding next to the highlighted report, then download the JSON."
    )
    st.stop()

nav = None
if state.result:
    findings = state.result["findings"]
    options = [NAV_EXAM, *(f"f:{f['uid']}" for f in findings), NAV_ADD]
    if state.get(nav_key()) is None and state.get("last_nav") in options:
        state[nav_key()] = state.last_nav  # clicking the selected segment deselects it: keep it selected
    if state.get(nav_key()) not in options:
        state[nav_key()] = NAV_EXAM
    nav = state.last_nav = state[nav_key()]

selected = finding_by_nav(nav) if nav and nav.startswith("f:") else None
report_col, review_col = st.columns([1, 1.1], gap="large")

with report_col:
    chips = [f"<b>{html.escape(state.report['file_name'])}</b>"] + [
        f"{html.escape(k)}: {html.escape(v)}" for k, v in state.report["metadata"].items()
    ]
    st.html('<div class="chips">' + "".join(f'<span class="chip">{c}</span>' for c in chips) + "</div>")
    with st.container(height=PANEL_HEIGHT, border=True):
        findings = state.result["findings"] if state.result else []
        st.html(report_html(state.report["text"], findings, selected["uid"] if selected else None))
    if state.result and findings:
        used = [k for k in LEXICON if any(f["modality"] == k for f in findings)]
        st.html(
            '<div class="legend">'
            + "".join(f'<span><i style="background:{MODALITY_COLORS.get(k, "#e5e7eb")}"></i>{LEXICON[k].name}</span>'
                      for k in used)
            + "</div>"
        )

with review_col:
    if not state.result:
        with st.container(height=PANEL_HEIGHT + 40, border=True):
            st.markdown("#### Ready to extract")
            st.caption("Click **Extract descriptors** in the sidebar. The model reads the report and proposes "
                       "the exam-level descriptors and one entry per finding, for you to check.")
    else:
        st.pills(
            "Section", options, key=nav_key(), format_func=nav_label, label_visibility="collapsed",
        )
        with st.container(height=PANEL_HEIGHT - 20, border=True):
            if nav == NAV_EXAM:
                exam_view()
            elif nav == NAV_ADD:
                add_view()
            else:
                finding_view(selected)
