# BI-RADS Annotator

Streamlit app to annotate breast imaging reports with the ACR BI-RADS lexicon.

- **Left:** upload a `.txt` report and read it. The text each finding is based on is highlighted and tagged `F1`, `F2`, ….
- **Right:** the BI-RADS descriptors extracted by the OpenAI API in a single request:
  - **Exam level:** one block per modality in the report, holding only that modality's `Exam_level` descriptors (e.g. breast composition, BPE, assessment category).
  - **Findings:** one finding per finding type present (a mass with skin thickening is two findings), each with a modality, its `Finding_type` descriptors and its `Characteristics` (location). Group items such as Mass show their sub-descriptors (shape, margin, …) only when ticked, and are ticked automatically when a sub-descriptor is filled. Changing a finding's modality re-extracts that finding's descriptors for the new modality.
  - Negative statements ("No axillary lymphadenopathy") do not create findings.
- Every value can be corrected. Descriptors not stated in the report are left empty (`null`, `[]` for multi-value, `false` for Bool).
- Enter your name, optionally rename the output file, then **Download results (JSON)**.

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

Descriptors and their allowed values are read from `lexicon/Descriptors_V.1.2.md`. To change the lexicon, edit that file, keeping its structure (`## Modality`, `### Exam_level:`, `### Finding_type:`, `#### Characteristics`) and line format:

    - Label — `variable` (one | multi | Bool): value_a, value_b, ...
        Sub-descriptor — `variable` (one | multi): ...   (indented under a Bool group)

Groups without a variable name (e.g. ultrasound "Masses — (Bool)") are shown as a toggle in the UI but not exported; their sub-descriptors are.

## Output

```json
{
  "annotator": "…",
  "download_date": "2026-10-22T10:30:57+00:00",
  "lexicon_version": "V.1.2",
  "model": "gpt-5.6-sol",
  "report": {"file_name": "…", "text": "…"},
  "exam_level": [{"modality": "Mammography", "descriptors": {"breast_composition": "scattered_fibroglandular", "assessment_category": "2"}}],
  "findings": [{"id": 1, "modality": "Ultrasound", "evidence": ["…"], "descriptors": {"simple_cyst": true, "mass_shape": "round", "laterality": "right", "…": null}}]
}
```
