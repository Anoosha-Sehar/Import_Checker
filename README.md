# Import Checker

**Import Checker** is a Python script that verifies ontology IDs from DataHarmonizer template files (slots and enums) against **GenEpiO import files**. It highlights missing IDs and generates a PDF summary and a detailed TSV report.

---

## Ontology Import Files

- The script checks IDs against **GenEpiO import files**, which are maintained in the [GenEpiO repository](https://github.com/GenEpiO/genepio/tree/master/src/ontology/imports).  
- Example file: `general_ontofox.txt`.  
- To run the checker, you must **clone the GenEpiO repository locally**.  
- Make sure the `import_path` in `main.py` points to the `imports/` folder of your local GenEpiO clone, for example:

```python
import_path = "/path/to/GenEpiO/src/ontology/imports/"
```
---
## DataHarmonizer Templates

- Templates can be downloaded from [this spreadsheet](https://docs.google.com/spreadsheets/d/1jPQAIJcL_xa3oBVFEsYRGLGf7ESTOwzsTSjKZ-0CTYE/edit?gid=208305190#gid=208305190).  
- Place all templates in the `templates/` folder of the **Import Checker repository**.  
- Template filenames should follow this recommended format:
  - `template-slots.tsv`
  - `template-enums.tsv`
- The script automatically detects all templates in the `templates/` folder.

---
## Features

- Checks slot IDs and enum IDs from DataHarmonizer templates.  
- Compares IDs against ontology import files in `imports/`.  
- Skips GENEPIO IDs from checks.  
- Auto-detects all templates in `templates/` (slots and enums) and supports multiple templates.  
- Generates:
  - PDF report summarizing counts and missing IDs by ontology prefix for each template, with page breaks between templates.
  - TSV file listing each ID with status, source template, source type, and source import file.
  - Includes a timestamp in both PDF and TSV for traceability.

---
## Prerequisites
- **Python 3.8 or higher**
- Required Python packages:
  ```bash
  pip install pandas fpdf
  ```
- Local clone of [GenEpiO repository](https://github.com/GenEpiO/genepio) for import files.

---
## Template Folder Structure

All DataHarmonizer templates must go into the templates/ folder inside the Import Checker repository inside the **Import Checker repository**.  
The script will automatically detect all templates based on their filenames (recommended format: `template-slots.tsv` and `template-enums.tsv`).

- Recommended format for templates:
  - `<template_name>-slots.tsv`
  - `<template_name>-enums.tsv`

- Example:
  - `Mpox-slots.tsv`
  - `Mpox-enums.tsv`
  - `CanCOGeN-slots.tsv`
  - `CanCOGeN-enums.tsv`

If you download templates from DataHarmonizer without renaming, the script will use the original filenames as they are.

---
## Usage

Run the script from the root of the repository:

```bash
	python main.py
```
The script will automatically detect all templates in the templates/ folder and all import files in the imports/ folder.

---
## Output
After running, the following files will be generated in the same folder:

- `Import_Checker_Report.pdf`
  - Summary of template checks
  - Counts of unique slot IDs, enum IDs, checked IDs, missing IDs
  - Missing IDs summarized by ontology prefix
  - Timestamp of report generation

- `Import_Checker_Output.tsv`
  - Detailed report of all IDs
  - Columns included:
    - **Ontology ID** – the ID being checked
    - **Template** – which template the ID came from
    - **Template Source** – “Unique Slot ID” or “Unique Enum ID”
    - **Status** – “Found” or “Missing”
    - **Source Import File** – which import file the ID was found in (if any)
    - **Report Generated** – timestamp of the run
---
## Notes:

   - GENEPIO IDs are skipped in checks.
   - Running the script overwrites existing PDF and TSV files with updated content.
   - The script auto-detects any number of templates placed in the templates/ folder.
   - 
## Customization

  - Add your own DataHarmonizer templates to the templates/ directory.
  - Add new ontology import files to the imports/ directory. The script automatically loads all .txt files in that folder.
