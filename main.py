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
        print(f"⚠️ Enum file missing for template {template_name}, skipping")

if not templates:
    raise RuntimeError("No valid templates found.")

print(f"✅ Templates loaded: {[t['name'] for t in templates]}")

# -----------------------------
# Initialize PDF
# -----------------------------
pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

# -----------------------------
# Report header with timestamp
# -----------------------------
date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Print timestamp first, right-aligned
pdf.set_font("Helvetica", '', 10)
pdf.cell(0, 6, f"Report generated on: {date_str}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")
pdf.ln(3)  # spacing before title

# Print main title centered
pdf.set_font("Helvetica", 'B', 16)
pdf.cell(0, 10, "Import Checker Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
pdf.ln(3)  # small spacing before the next section
# -----------------------------
# Import Files Loaded
# -----------------------------
pdf.set_font("Helvetica", 'B', 12)
pdf.cell(0, 8, "--- Import Files Loaded ---", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_font("Helvetica", '', 12)
for fname in sorted(import_sets.keys()):
    pdf.cell(0, 7, fname, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.ln(5)

# -----------------------------
# Templates Included
# -----------------------------
pdf.set_font("Helvetica", 'B', 12)
pdf.cell(0, 8, "--- Templates Included ---", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_font("Helvetica", '', 12)

template_links = {}
for template in templates:
    link = pdf.add_link()
    template_links[template["name"]] = link
    pdf.set_text_color(0, 0, 255)
    pdf.cell(0, 6, f"- {template['name']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, link=link)
pdf.set_text_color(0, 0, 0)
pdf.ln(5)

# -----------------------------
# Collect UNIQUE IDs across templates
# -----------------------------
all_ids_across_templates = set()
all_missing_ids_across_templates = set()
total_ids_referenced = 0

for template in templates:
    slots_df = pd.read_csv(template["slots_file"], sep="\t", dtype=str)
    enums_df = pd.read_csv(template["enums_file"], sep="\t", dtype=str)

    slots_ids = set(slots_df["slot_uri"].dropna())
    enums_ids = set(enums_df["meaning"].dropna())
    all_ids_raw = slots_ids.union(enums_ids)
    total_ids_referenced += len(all_ids_raw)

    gene_ids = {oid for oid in all_ids_raw if oid.startswith("GENEPIO:")}
    all_ids = all_ids_raw - gene_ids
    all_ids_across_templates.update(all_ids)

    for oid in all_ids:
        if not check_id_in_imports(oid):
            all_missing_ids_across_templates.add(oid)

# -----------------------------
# Compute unique missing IDs by prefix
# -----------------------------
unique_missing_prefix_counts = defaultdict(int)
for oid in all_missing_ids_across_templates:
    prefix = oid.split(":")[0]
    unique_missing_prefix_counts[prefix] += 1

# -----------------------------
# Overall Summary
# -----------------------------
pdf.set_font("Helvetica", 'B', 12)
pdf.cell(0, 8, "--- Overall Summary Across All Templates ---", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_font("Helvetica", '', 12)

label_width = 90
value_width = 30
total_checked = len(all_ids_across_templates)
total_missing = len(all_missing_ids_across_templates)
total_found = total_checked - total_missing

summary_items = [
    ("Total Templates", len(templates)),
    ("Total IDs Referenced in Templates", total_ids_referenced),
    ("Total Unique IDs Checked", total_checked),
    ("Total Unique Found IDs", total_found),
    ("Total Unique Missing IDs", total_missing)
]

for label, value in summary_items:
    pdf.cell(label_width, 7, label, border=1)
    pdf.cell(value_width, 7, str(value), border=1)
    pdf.ln(7)

# -----------------------------
# Notes / Explanation
# -----------------------------
pdf.ln(2)
pdf.set_font("Helvetica", '', 9)
line_height = 5
note_lines = [
    ("Total Templates", " indicates how many DataHarmonizer templates were analyzed."),
    ("Total IDs Referenced in Templates", " counts every ontology ID usage across all templates, including duplicates."),
    ("Total Unique IDs Checked", " counts distinct ontology IDs across all templates (excluding GENEPIO IDs) that were checked against the ontology import files."),
    ("Total Unique Found IDs", " counts how many of these unique IDs were found in at least one import file."),
    ("Total Unique Missing IDs", " counts how many unique IDs were not found in any import file.")
]

for bold_text, normal_text in note_lines:
    pdf.set_font("Helvetica", 'B', 9)
    pdf.write(line_height, bold_text)
    pdf.set_font("Helvetica", '', 9)
    pdf.write(line_height, normal_text)
    pdf.ln(line_height)
pdf.ln(7)

# -----------------------------
# Prefix summary (UNIQUE)
# -----------------------------
pdf.set_font("Helvetica", 'B', 12)
pdf.cell(0, 8, "--- Top Missing Ontology Prefixes (Unique IDs) ---", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_font("Helvetica", 'B', 11)
pdf.cell(60, 7, "Ontology Prefix", border=1)
pdf.cell(40, 7, "Unique Missing IDs", border=1)
pdf.ln(7)

pdf.set_font("Helvetica", '', 11)
for prefix, count in sorted(unique_missing_prefix_counts.items(), key=lambda x: x[1], reverse=True):
    pdf.cell(60, 7, prefix, border=1)
    pdf.cell(40, 7, str(count), border=1)
    pdf.ln(7)
pdf.ln(5)
pdf.add_page()

# -----------------------------
# Detailed Template Analysis Label
# -----------------------------
pdf.set_font("Helvetica", 'B', 14)
pdf.cell(0, 10, "Detailed Template Analysis", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.ln(5)

# -----------------------------
# Detailed template analysis
# -----------------------------
tsv_rows = []

for template in templates:
    template_name = template["name"]
    pdf.set_link(template_links[template_name])

    slots_df = pd.read_csv(template["slots_file"], sep="\t", dtype=str)
    enums_df = pd.read_csv(template["enums_file"], sep="\t", dtype=str)

    slots_ids = set(slots_df["slot_uri"].dropna())
    enums_ids = set(enums_df["meaning"].dropna())
    all_ids_raw = slots_ids.union(enums_ids)

    gene_ids = {oid for oid in all_ids_raw if oid.startswith("GENEPIO:")}
    all_ids = all_ids_raw - gene_ids

    id_source_map = {oid: "Slot ID" for oid in slots_ids}
    id_source_map.update({oid: "Enum ID" for oid in enums_ids})

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

    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 8, f"--- Template: {template_name} ---", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", '', 12)

    pdf.cell(50,7,"Unique Slot IDs:",border=1)
    pdf.cell(50,7,str(len(slots_ids)),border=1)
    pdf.ln(7)

    pdf.cell(50,7,"Unique Enum IDs:",border=1)
    pdf.cell(50,7,str(len(enums_ids)),border=1)
    pdf.ln(7)

    pdf.cell(50,7,"Total IDs:",border=1)
    pdf.cell(50,7,str(len(all_ids_raw)),border=1)
    pdf.ln(7)

    pdf.cell(50,7,"GENEPIO skipped:",border=1)
    pdf.cell(50,7,str(len(gene_ids)),border=1)
    pdf.ln(7)

    pdf.cell(50,7,"Checked IDs:",border=1)
    pdf.cell(50,7,str(len(all_ids)),border=1)
    pdf.ln(7)

    pdf.cell(50,7,"Missing IDs:",border=1)
    pdf.cell(50,7,str(len(missing_ids)),border=1)
    pdf.ln(10)

    missing_by_prefix = defaultdict(int)
    for mid in missing_ids:
        prefix = mid.split(":")[0]
        missing_by_prefix[prefix] += 1

    pdf.set_font("Helvetica",'',11)
    pdf.cell(0,7,"--- Missing IDs by Ontology Prefix ---",new_x=XPos.LMARGIN,new_y=YPos.NEXT)
    pdf.set_font("Helvetica",'',10)
    for prefix,count in sorted(missing_by_prefix.items()):
        pdf.cell(0,6,f"{prefix} - Missing: {count}",new_x=XPos.LMARGIN,new_y=YPos.NEXT)

    pdf.add_page()

# -----------------------------
# Save outputs
# -----------------------------
pdf_file = "Import_Checker_Report.pdf"
tsv_file = "Import_Checker_Output.tsv"

pdf.output(pdf_file)
print(f"✅ PDF report generated: {pdf_file}")

tsv_df = pd.DataFrame(tsv_rows)
tsv_df = tsv_df[
    ["Ontology ID","Template","Template Source","Status","Source Import File","Report Generated"]
]
tsv_df.to_csv(tsv_file, sep="\t", index=False)
print(f"✅ TSV output generated: {tsv_file}")