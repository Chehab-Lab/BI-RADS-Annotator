# BI-RADS Annotator

Streamlit app to annotate breast imaging reports with the ACR BI-RADS lexicon.

The page has a title bar with a **download** icon and a **settings** icon (annotator name, file name, re-extract), the report on the left half and the findings on the right half.

- **Report (left):** upload a `.txt` report. Extraction starts by itself. An optional metadata header at the top of the file is shown above the report, saved in the JSON under `report.metadata`, and never sent to the model:

      ---
      id: BR_0077
      country: Togo
      modality: MR
      ---
      <report text>

  The text each finding is based on is highlighted and tagged `F1`, `F2`, …; the selected finding is outlined and the others are dimmed.
- **Findings (right):** the OpenAI API proposes, in a single request, the exam-level descriptors and the findings. Pills switch between **Exam level**, `F1`, `F2`, … and **+** (add a finding).
  - **Exam level:** one block per modality in the report, holding only that modality's `Exam_level` descriptors (e.g. breast composition, BPE, assessment category). Modalities can be added or deleted.
  - **Findings:** one finding per lesion. A finding is simply a set of attributes: every `Finding_type` and `Characteristics` attribute of its modality is listed, with no grouping (a mass with associated skin thickening is one finding with `mass`, its shape/margin and `skin_thickening` filled). Changing a finding's modality re-extracts its attributes for the new modality.
  - Findings can be deleted (with a confirmation) or added. A new finding starts empty, or, if you paste the report excerpt it is based on, is highlighted and has its attributes extracted from that excerpt. Findings are renumbered `F1`, `F2`, … after each change.
  - Negative statements ("No axillary lymphadenopathy") and general tissue descriptions ("fibrocystic changes") do not create findings. Exact duplicate findings are dropped.
  - Values are shown in readable form (`Heterogeneously dense`, `10 o'clock`) but exported as lexicon values (`heterogeneously_dense`, `clock_10`). Attributes not stated in the report are left empty (`null`, `[]` for multi-value, `false` for Bool).
- **Download:** enter your name under settings, then click the download icon.

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

Group headings without a variable name (e.g. ultrasound "Masses — (Bool)") are neither shown nor exported; their sub-descriptors are listed as ordinary attributes.

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
