import pandas as pd
import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from collections import defaultdict
from datetime import datetime
import textwrap

# -----------------------------
# CONFIG: Add your templates here
# -----------------------------
templates = [
    {
        "name": "CanCOGeN",
        "slots_file": "/Users/anoosha/GitHub/import_checker/CanCOGeN-slots.tsv",
        "enums_file": "/Users/anoosha/GitHub/import_checker/CanCOGeN-enums.tsv"
    }
]

import_path = "/Users/anoosha/GitHub/GenEpiO/src/ontology/imports/"
debug = False

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
# Timestamp
# -----------------------------
gen_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# -----------------------------
# Initialize PDF
# -----------------------------
pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

pdf.set_font("Helvetica", 'B', 16)
pdf.cell(0, 10, "Import Checker Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
pdf.set_font("Helvetica", '', 12)
pdf.cell(0, 8, f"Generated on: {gen_date}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.ln(5)

pdf.multi_cell(0, 6,
    "This report checks all IDs from DataHarmonizer templates (slots and enums) "
    "against the ontology import files, excluding GENEPIO IDs. "
    "It highlights counts and missing IDs."
)
pdf.ln(5)

# -----------------------------
# Import files checked
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

    # Map IDs to source (Slots or Enum)
    id_source_map = {oid: "Unique Slot ID" for oid in slots_ids}
    id_source_map.update({oid: "Unique Enum ID" for oid in enums_ids})

    # Check IDs
    found_details = []
    missing_ids = []
    for oid in sorted(all_ids):
        source_type = id_source_map.get(oid, "")
        result = check_id_in_imports(oid)
        if result:
            found_details.append((oid, result))
            tsv_rows.append({
                "Ontology ID": oid,
                "Template": template_name,
                "Template Source": source_type,
                "Status": "Found",
                "Source Import File": os.path.basename(result),
                "Generated On": gen_date
            })
        else:
            missing_ids.append(oid)
            tsv_rows.append({
                "Ontology ID": oid,
                "Template": template_name,
                "Template Source": source_type,
                "Status": "Missing",
                "Source Import File": "",
                "Generated On": gen_date
            })

    # -----------------------------
    # Template Summary in PDF
    # -----------------------------
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 8, f"--- Template: {template_name} ---", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", '', 12)
    summary = [
        ("Unique Slot IDs", len(slots_ids)),
        ("Unique Enum IDs", len(enums_ids)),
        ("Total IDs", len(all_ids_raw)),
        ("GENEPIO IDs skipped", len(gene_ids)),
        ("Checked IDs", len(all_ids)),
        ("Missing IDs", len(missing_ids))
    ]
    for label, count in summary:
        pdf.cell(70, 7, f"{label}:", border=0)
        pdf.cell(30, 7, str(count), border=0)
        pdf.ln(7)
    pdf.ln(3)

    # -----------------------------
    # Missing IDs summary (PDF)
    # -----------------------------
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 8, "--- Missing IDs by Ontology Prefix (top examples) ---",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", '', 11)

    missing_by_prefix = defaultdict(list)
    for mid in missing_ids:
        prefix = mid.split(":")[0]
        missing_by_prefix[prefix].append(mid)

    for prefix, ids_list in sorted(missing_by_prefix.items()):
        count = len(ids_list)
        # show first 5 examples, wrap text
        examples = ", ".join(ids_list[:5])
        if count > 5:
            examples += ", ..."
        wrapped_lines = textwrap.wrap(examples, width=70)
        pdf.cell(0, 7, f"{prefix} - Missing: {count}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        for line in wrapped_lines:
            pdf.cell(0, 6, f"   Examples: {line}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

# -----------------------------
# Save PDF (overwrite existing file)
# -----------------------------
pdf.output("Import_Checker_Report.pdf")
print("✅ PDF report generated: Import_Checker_Report.pdf")

# -----------------------------
# Save TSV (overwrite existing file)
# -----------------------------
tsv_df = pd.DataFrame(tsv_rows)
tsv_df = tsv_df[["Ontology ID", "Template", "Template Source", "Status", "Source Import File", "Generated On"]]
tsv_df.to_csv("Import_Checker_Output.tsv", sep='\t', index=False)
print("✅ TSV output generated: Import_Checker_Output.tsv")