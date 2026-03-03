# Import Checker

**Import Checker** is a Python script that verifies ontology IDs from DataHarmonizer template files (slots and enums) against ontology import files.  
It generates a PDF report summarizing missing IDs by ontology prefix and a TSV file with detailed status for each ID.

---

## Features
- Checks **slot IDs** and **enum IDs** from DataHarmonizer templates.
- Compares IDs against ontology import files in `imports/`.
- Skips GENEPIO IDs from checks.
- Generates:
  - **PDF report** summarizing counts and missing IDs.
  - **TSV file** listing each ID with status, source template, and source import file.
- Includes a **timestamp** in the report for traceability.

---

## Prerequisites
- **Python 3.8 or higher**
- Python packages:
  ```bash
  pip install pandas fpdf
•	Ontology import files should be placed in the imports/ directory.

•	DataHarmonizer template files (slots and enums) should be present in the repository.

## Usage

Run the script from the root of the repository:
```bash
python main.py

## Output:
	•	Import_Checker_Report.pdf – PDF summary of template checks and missing IDs.
	•	Import_Checker_Output.tsv – Detailed TSV with all IDs and status.

## Notes:

	•	PDF includes missing ID summaries by ontology prefix.
  
	•	TSV includes columns: Ontology ID, Template, Template Source (Slots/Enum), Status (Found/Missing), and Source Import File.
  
	•	Running the script overwrites existing PDF and TSV files with updated content.

## Customization
	•	Add your own DataHarmonizer templates to the templates list in main.py.
	•	Add new ontology import files to the imports/ directory. The script automatically loads all .txt files in that folder.
