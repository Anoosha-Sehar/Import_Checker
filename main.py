import pandas as pd
import os
from fpdf import FPDF
from collections import defaultdict

# ------------------- CONFIG -------------------
templates = [
    {
        "name": "CanCOGeN",
        "slots_file": "/Users/anoosha/GitHub/import_checker/CanCOGeN-slots.tsv",
        "enums_file": "/Users/anoosha/GitHub/import_checker/CanCOGeN-enums.tsv"
    },
    # Example future template:
    # {
    #     "name": "Mpox",
    #     "slots_file": "path/to/mpox-slots.tsv",
    #     "enums_file": "path/to/mpox-enums.tsv"
    # }
]

import_path = "/Users/anoosha/GitHub/GenEpiO/src/ontology/imports/"
debug = False  # True to print first 5 rows of templates

# ------------------- FUNCTIONS -------------------

def load_ids_from_file(file_path):
    """Load all IDs from a given import file."""
    ids = set()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    ids.update(line.split())
        return ids
    except FileNotFoundError:
        print(f"⚠️ File not found: {file_path}")
        return set()

def normalize_to_iri(oid):
    """Normalize CURIE to OBO IRI."""
    if ":" in oid:
        prefix, local_id = oid.split(":", 1)
        return f"http://purl.obolibrary.org/obo/{prefix}_{local_id}"
    return oid

def check_id_in_imports(oid, import_sets):
    """Check if the ID exists in any import file."""
    iri = normalize_to_iri(oid)
    for data in import_sets.values():
        if oid in data["ids"] or iri in data["ids"]:
            return os.path.basename(data["file"])
    return None

def format_ids_in_columns(ids_list, col_width=5):
    """Return IDs as string in multiple columns for PDF."""
    lines = []
    for i in range(0, len(ids_list), col_width):
        line_ids = ids_list[i:i+col_width]
        lines.append(", ".join(line_ids))
    return lines

# ------------------- LOAD IMPORT FILES -------------------
import_sets = {}
for filename in os.listdir(import_path):
    if filename.endswith(".txt"):
        full_path = os.path.join(import_path, filename)
        ids = load_ids_from_file(full_path)
        import_sets[filename] = {"file": full_path, "ids": ids}
        print(f"✅ Loaded {filename}: {len(ids)} IDs")

print(f"\nTotal import files loaded: {len(import_sets)}\n")

# Keep a set of all checked import file names for PDF
import_files_checked = sorted(import_sets.keys())

# ------------------- PDF SETUP -------------------
pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()
pdf.set_font("Arial", 'B', 16)
pdf.cell(0, 10, "Import Checker Report", ln=True, align="C")
pdf.ln(3)

pdf.set_font("Arial", '', 12)
pdf.multi_cell(0, 6,
               "This report checks all IDs from DataHarmonizer templates "
               "(slots and enums) against ontology import files, excluding GENEPIO IDs. "
               "It highlights missing IDs and where IDs were found in import files.")
pdf.ln(5)

# ------------------- PROCESS EACH TEMPLATE -------------------
all_missing_ids = defaultdict(list)  # Group missing IDs across all templates by prefix
all_found_details = defaultdict(list)  # Group found IDs across all templates by prefix

for template in templates:
    template_name = template["name"]

    # Load template files
    slots_df = pd.read_csv(template["slots_file"], sep='\t', dtype=str)
    enums_df = pd.read_csv(template["enums_file"], sep='\t', dtype=str)
    if debug:
        print(f"Template {template_name} Slots columns:", list(slots_df.columns))
        print(f"Template {template_name} Enums columns:", list(enums_df.columns))

    slots_ids = set(slots_df['slot_uri'].dropna())
    enums_ids = set(enums_df['meaning'].dropna())
    all_ids_raw = slots_ids.union(enums_ids)

    # Separate GENEPIO IDs
    gene_ids = {oid for oid in all_ids_raw if oid.startswith("GENEPIO:")}
    all_ids = all_ids_raw - gene_ids

    # Check IDs
    found_details = []
    missing_ids = []
    for oid in all_ids:
        result = check_id_in_imports(oid, import_sets)
        if result:
            found_details.append((oid, result))
            all_found_details[oid.split(":")[0]].append((oid, result))
        else:
            missing_ids.append(oid)
            all_missing_ids[oid.split(":")[0]].append(oid)

    # ------------------- TEMPLATE SUMMARY -------------------
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"--- Template: {template_name} ---", ln=True)
    pdf.set_font("Arial", '', 12)

    summary_lines = [
        f"Total IDs in slots file: {len(slots_ids)}",
        f"Total IDs in enums file: {len(enums_ids)}",
        f"Combined IDs (unique): {len(all_ids_raw)}",
        f"GENEPIO IDs skipped: {len(gene_ids)}",
        f"Total checked against imports: {len(all_ids)}",
        f"  - Found: {len(found_details)}",
        f"  - Missing: {len(missing_ids)}"
    ]
    for line in summary_lines:
        pdf.cell(0, 7, line, ln=True)
    pdf.ln(5)

# ------------------- IMPORT FILES CHECKED -------------------
pdf.set_font("Arial", 'B', 12)
pdf.cell(0, 8, "--- Import Files Checked ---", ln=True)
pdf.set_font("Arial", '', 12)
pdf.multi_cell(0, 7, ", ".join(import_files_checked))
pdf.ln(5)

# ------------------- MISSING IDS SUMMARY -------------------
pdf.set_font("Arial", 'B', 12)
pdf.cell(0, 8, "--- Missing IDs by Ontology Prefix ---", ln=True)
pdf.set_font("Arial", '', 12)

for prefix, ids_list in sorted(all_missing_ids.items()):
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 7, f"{prefix} ({len(ids_list)} missing):", ln=True)
    pdf.set_font("Arial", '', 11)
    lines = format_ids_in_columns(sorted(ids_list), col_width=5)
    for l in lines:
        pdf.cell(0, 6, l, ln=True)
    pdf.ln(2)
pdf.ln(5)

# ------------------- FOUND IDS SUMMARY -------------------
pdf.set_font("Arial", 'B', 12)
pdf.cell(0, 8, "--- Found IDs by Ontology Prefix ---", ln=True)
pdf.set_font("Arial", '', 12)

for prefix, items in sorted(all_found_details.items()):
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 7, f"{prefix} ({len(items)} found):", ln=True)
    pdf.set_font("Arial", '', 11)
    # Print in columns: ID -> file
    lines = []
    for oid, ffile in items:
        lines.append(f"{oid} -> {ffile}")
    col_lines = format_ids_in_columns(lines, col_width=3)  # fewer columns because long strings
    for l in col_lines:
        pdf.cell(0, 6, l, ln=True)
    pdf.ln(2)

# ------------------- SAVE PDF -------------------
pdf.output("Import_Checker_Report.pdf")
print("✅ PDF report generated: Import_Checker_Report.pdf")