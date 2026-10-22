# BI-RADS Annotator

Streamlit app to annotate breast imaging reports with the ACR BI-RADS lexicon.

- **Left:** upload a `.txt` report and read it. The text each finding is based on is highlighted and tagged `F1`, `F2`, ….
- **Right:** the BI-RADS descriptors extracted by the OpenAI API in a single request:
  - **Exam level:** one block per modality in the report, for statements about the breasts or the exam as a whole, including negative statements (e.g. "No axillary lymphadenopathy" → `lymph_node_axillary = normal`).
  - **Findings:** each finding has a modality and its descriptors. Changing a finding's modality re-extracts that finding's descriptors for the new modality.
- Every value can be corrected. Descriptors not stated in the report are left empty (`null`, or `[]` for multi-value descriptors).
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

Descriptors and their allowed values are read from `lexicon/Descriptors_V.1.0.2.md`. To change the lexicon, edit that file, keeping the line format:

    - Label — `variable` (one | multi): value_a, value_b, ...

## Output

```json
{
  "annotator": "…",
  "download_date": "2026-10-22T10:30:57+00:00",
  "lexicon_version": "V.1.0.2",
  "model": "gpt-5.6-sol",
  "report": {"file_name": "…", "text": "…"},
  "exam_level": [{"modality": "Mammography", "descriptors": {"breast_composition": "scattered_fibroglandular", "…": null}}],
  "findings": [{"id": 1, "modality": "Ultrasound", "evidence": ["…"], "descriptors": {"mass_shape": "round", "…": null}}]
}
```
