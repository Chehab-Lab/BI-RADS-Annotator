# BI-RADS Annotator

Streamlit app to annotate breast imaging reports with the ACR BI-RADS lexicon.

The sidebar walks through the four steps; the report and the review panel sit side by side.

1. **Report:** upload a `.txt` report. An optional metadata header at the top of the file is shown above the report as chips, saved in the JSON under `report.metadata`, and never sent to the model:

       ---
       id: BR_0077
       country: Togo
       modality: MR
       ---
       <report text>

2. **Extract:** the OpenAI API proposes, in a single request, the exam-level descriptors and the findings. The text each finding is based on is highlighted in the report and tagged `F1`, `F2`, ….
3. **Review:** the pills above the review panel switch between **Exam level**, each finding and **Add**. One thing is shown at a time; the selected finding's text is outlined in the report and the others are dimmed.
   - **Exam level:** one block per modality in the report, holding only that modality's `Exam_level` descriptors (e.g. breast composition, BPE, assessment category).
   - **Findings:** one finding per lesion, with all of its attributes (a mass with associated skin thickening is one finding with both filled). Each finding shows all `Finding_type` descriptors of its modality and its `Characteristics` (location), with a one-line readout of what is filled at the top. Group items such as Mass show their sub-descriptors (shape, margin, …) only when ticked, and are ticked automatically when a sub-descriptor is filled. Changing a finding's modality re-extracts its descriptors for the new modality.
   - **Mark reviewed & next** moves through the findings; the sidebar shows how many are reviewed (this is a review aid only and is not exported).
   - Negative statements ("No axillary lymphadenopathy") and general tissue descriptions ("fibrocystic changes") do not create findings. Exact duplicate findings are dropped.
   - Findings and exam-level modalities can be deleted (with a confirmation) or added. A new finding starts empty, or, if you paste the report excerpt it is based on, is highlighted and has its descriptors extracted from that excerpt. Findings are renumbered `F1`, `F2`, … after each change.
   - Values are shown in readable form (`Heterogeneously dense`, `10 o'clock`) but exported as lexicon values (`heterogeneously_dense`, `clock_10`). Descriptors not stated in the report are left empty (`null`, `[]` for multi-value, `false` for Bool).
4. **Download:** enter your name, optionally rename the output file, then **Download JSON**.

## Run

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...        # or use .streamlit/secrets.toml (see the .example file)
streamlit run app.py
```

Optional settings (environment or secrets):

- `OPENAI_MODEL` (default `gpt-5.6-sol`)
- `OPENAI_BASE_URL`, for any OpenAI-compatible server that supports JSON-schema structured outputs

## Lexicon

Descriptors and their allowed values are read from `lexicon/Descriptors_V.1.3.md`. To change the lexicon, edit that file, keeping its structure (`## Modality`, `### Exam_level:`, `### Finding_type:`, `#### Characteristics`) and line format:

    - Label — `variable` (one | multi | Bool): value_a, value_b, ...
        Sub-descriptor — `variable` (one | multi): ...   (indented under a Bool group)

Groups without a variable name (e.g. ultrasound "Masses — (Bool)") are shown as a toggle in the UI but not exported; their sub-descriptors are.

## Output

```json
{
  "annotator": "…",
  "download_date": "2026-10-22T10:30:57+00:00",
  "lexicon_version": "V.1.3",
  "model": "gpt-5.6-sol",
  "report": {"file_name": "…", "metadata": {"id": "…", "country": "…"}, "text": "…"},
  "exam_level": [{"modality": "Mammography", "descriptors": {"breast_composition": "scattered_fibroglandular", "assessment_category": "2"}}],
  "findings": [{"id": 1, "modality": "Ultrasound", "evidence": ["…"], "descriptors": {"simple_cyst": true, "mass_shape": "round", "laterality": "right", "…": null}}]
}
```
