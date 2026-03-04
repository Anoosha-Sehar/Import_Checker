import pandas as pd
import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from collections import defaultdict
from datetime import datetime

# -----------------------------
# CONFIG
# -----------------------------
import_path = "/Users/anoosha/GitHub/GenEpiO/src/ontology/imports/"
templates_folder = "/Users/anoosha/GitHub/import_checker/templates/"

# -----------------------------
# Load IDs from import files
# -----------------------------
def load_ids_from_file(file_path):
    ids = set()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    ids.update(line.split())
        return ids
    except FileNotFoundError:
        print(f"⚠️ File not found: {file_path}")
        return set()

import_sets = {}
for filename in os.listdir(import_path):
    if filename.endswith(".txt"):
        full_path = os.path.join(import_path, filename)
        ids = load_ids_from_file(full_path)
        import_sets[filename] = {"file": full_path, "ids": ids}
        print(f"✅ Loaded {filename}: {len(ids)} IDs")
print(f"\nTotal import files loaded: {len(import_sets)}\n")

# -----------------------------
# Helper functions
# -----------------------------
def normalize_to_iri(oid):
    if ":" in oid:
        prefix, local_id = oid.split(":", 1)
        return f"http://purl.obolibrary.org/obo/{prefix}_{local_id}"
    return oid

def check_id_in_imports(oid):
    iri = normalize_to_iri(oid)
    for data in import_sets.values():
        if oid in data["ids"] or iri in data["ids"]:
            return os.path.basename(data["file"])
    return None

# -----------------------------
# Auto-detect templates
# -----------------------------
templates = []
slots_files = sorted([f for f in os.listdir(templates_folder) if f.endswith("-slots.tsv")])

for slots_file in slots_files:
    template_name = slots_file.replace("-slots.tsv", "")
    slots_path = os.path.join(templates_folder, slots_file)
    enums_path = os.path.join(templates_folder, f"{template_name}-enums.tsv")
    if os.path.exists(enums_path):
        templates.append({
            "name": template_name,
            "slots_file": slots_path,
            "enums_file": enums_path
        })
    else:
        print(f"⚠️ Enum file missing for template {template_name}, skipping this template")

if not templates:
    raise RuntimeError("No valid templates found. Check templates folder and file names.")

print(f"✅ Templates loaded: {[t['name'] for t in templates]}")

# -----------------------------
# Initialize PDF
# -----------------------------
pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

pdf.set_font("Helvetica", 'B', 16)
pdf.cell(0, 10, "Import Checker Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
pdf.ln(3)

pdf.set_font("Helvetica", '', 12)
date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
pdf.multi_cell(0, 6,
    f"This report checks all IDs from DataHarmonizer templates (slots and enums) "
    f"against the ontology import files, excluding GENEPIO IDs. "
    f"It highlights missing IDs.\n\nReport generated on: {date_str}"
)
pdf.ln(5)

# -----------------------------
# Section: Import files checked
# -----------------------------
pdf.set_font("Helvetica", 'B', 12)
pdf.cell(0, 8, "--- Import Files Checked ---", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_font("Helvetica", '', 12)
for fname in sorted(import_sets.keys()):
    pdf.cell(0, 7, fname, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.ln(5)

# -----------------------------
# TSV output collection
# -----------------------------
tsv_rows = []

# -----------------------------
# Loop over templates
# -----------------------------
for template in templates:
    template_name = template["name"]

    # Load template files
    slots_df = pd.read_csv(template["slots_file"], sep='\t', dtype=str)
    enums_df = pd.read_csv(template["enums_file"], sep='\t', dtype=str)

    slots_ids = set(slots_df['slot_uri'].dropna())
    enums_ids = set(enums_df['meaning'].dropna())
    all_ids_raw = slots_ids.union(enums_ids)
    gene_ids = {oid for oid in all_ids_raw if oid.startswith("GENEPIO:")}
    all_ids = all_ids_raw - gene_ids

    # Map source type for TSV
    id_source_map = {}
    for oid in slots_ids:
        id_source_map[oid] = "Unique Slot ID"
    for oid in enums_ids:
        id_source_map[oid] = "Unique Enum ID"

    # Check IDs
    missing_ids = []
    for oid in sorted(all_ids):
        source_type = id_source_map.get(oid, "")
        result = check_id_in_imports(oid)
        tsv_rows.append({
            "Ontology ID": oid,
            "Template": template_name,
            "Template Source": source_type,
            "Status": "Found" if result else "Missing",
            "Source Import File": os.path.basename(result) if result else "",
            "Report Generated": date_str
        })
        if not result:
            missing_ids.append(oid)

    # Template Summary
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 8, f"--- Template: {template_name} ---",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", '', 12)
    pdf.cell(50, 7, "Unique Slot IDs:", border=1)
    pdf.cell(50, 7, str(len(slots_ids)), border=1)
    pdf.ln(7)
    pdf.cell(50, 7, "Unique Enum IDs:", border=1)
    pdf.cell(50, 7, str(len(enums_ids)), border=1)
    pdf.ln(7)
    pdf.cell(50, 7, "Total IDs:", border=1)
    pdf.cell(50, 7, str(len(all_ids_raw)), border=1)
    pdf.ln(7)
    pdf.cell(50, 7, "GENEPIO IDs skipped:", border=1)
    pdf.cell(50, 7, str(len(gene_ids)), border=1)
    pdf.ln(7)
    pdf.cell(50, 7, "Checked IDs:", border=1)
    pdf.cell(50, 7, str(len(all_ids)), border=1)
    pdf.ln(7)
    pdf.cell(50, 7, "Missing IDs:", border=1)
    pdf.cell(50, 7, str(len(missing_ids)), border=1)
    pdf.ln(10)

    # Missing IDs by Prefix
    missing_by_prefix = defaultdict(int)
    for mid in missing_ids:
        prefix = mid.split(":")[0]
        missing_by_prefix[prefix] += 1

    pdf.set_font("Helvetica", '', 11)
    pdf.cell(0, 7, "--- Missing IDs by Ontology Prefix ---",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", '', 10)
    for prefix, count in sorted(missing_by_prefix.items()):
        pdf.cell(0, 6, f"{prefix} - Missing: {count}",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Page break before next template
    pdf.add_page()
# -----------------------------
# Save PDF and TSV
# -----------------------------
pdf_file = "Import_Checker_Report.pdf"
tsv_file = "Import_Checker_Output.tsv"

pdf.output(pdf_file)
print(f"✅ PDF report generated: {pdf_file}")

tsv_df = pd.DataFrame(tsv_rows)
tsv_df = tsv_df[[
    "Ontology ID", "Template", "Template Source", "Status", "Source Import File", "Report Generated"
]]
tsv_df.to_csv(tsv_file, sep='\t', index=False)
print(f"✅ TSV output generated: {tsv_file}")