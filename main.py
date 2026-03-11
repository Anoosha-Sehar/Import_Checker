import pandas as pd
import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from collections import defaultdict
from datetime import datetime
from owlready2 import get_ontology

# -----------------------------
# CONFIG
# -----------------------------
templates_folder = "/Users/anoosha/GitHub/import_checker/templates/"
owl_file = "/Users/anoosha/GitHub/GenEpiO/src/ontology/genepio-merged.owl"

# -----------------------------
# Load ontology
# -----------------------------
print(f"🔹 Loading OWL ontology from: {owl_file} ...")
onto = get_ontology(f"file://{owl_file}").load()
all_ids = {cls.name.replace("_", ":") for cls in onto.classes()}
print(
    f"✅ Ontology loaded. Total IDs in merged ontology: {len(all_ids)}\n")

# -----------------------------
# Auto-detect templates
# -----------------------------
templates = []
slots_files = sorted([f for f in os.listdir(templates_folder) if
                      f.endswith("-slots.tsv")])
for slots_file in slots_files:
    template_name = slots_file.replace("-slots.tsv", "")
    slots_path = os.path.join(templates_folder, slots_file)
    enums_path = os.path.join(templates_folder,
                              f"{template_name}-enums.tsv")
    if os.path.exists(enums_path):
        templates.append({
            "name": template_name,
            "slots_file": slots_path,
            "enums_file": enums_path
        })
    else:
        print(
            f"⚠️ Enum file missing for template {template_name}, skipping")
if not templates:
    raise RuntimeError("No valid templates found.")
print(f"✅ Templates loaded: {[t['name'] for t in templates]}\n")

# -----------------------------
# Initialize PDF
# -----------------------------
pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()
date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

pdf.set_font("Helvetica", '', 10)
pdf.cell(0, 6, f"Report generated on: {date_str}", new_x=XPos.LMARGIN,
         new_y=YPos.NEXT, align="R")
pdf.ln(3)

pdf.set_font("Helvetica", 'B', 16)
pdf.cell(0, 10, "Import Checker Report", new_x=XPos.LMARGIN,
         new_y=YPos.NEXT, align="C")
pdf.ln(5)

# -----------------------------
# Collect all external IDs across templates
# -----------------------------
all_ids_across_templates = set()
all_missing_ids_across_templates = set()
total_ids_referenced = 0
id_to_templates = defaultdict(
    lambda: {"templates": set(), "sources": set(), "status": ""})

for template in templates:
    slots_df = pd.read_csv(template["slots_file"], sep="\t", dtype=str)
    enums_df = pd.read_csv(template["enums_file"], sep="\t", dtype=str)

    slots_ids = set(slots_df["slot_uri"].dropna())
    enums_ids = set(enums_df["meaning"].dropna())

    all_ids_raw = slots_ids.union(enums_ids)
    total_ids_referenced += len(all_ids_raw)

    gene_ids = {oid for oid in all_ids_raw if
                oid.startswith("GENEPIO:")}
    external_ids = all_ids_raw - gene_ids
    all_ids_across_templates.update(external_ids)

    # Populate TSV info
    for oid in external_ids:
        id_to_templates[oid]["templates"].add(template["name"])
        if oid in slots_ids:
            id_to_templates[oid]["sources"].add("Slot")
        if oid in enums_ids:
            id_to_templates[oid]["sources"].add("Enum")
        id_to_templates[oid][
            "status"] = "Found" if oid in all_ids else "Missing"

# Unique missing IDs across all templates
for oid in all_ids_across_templates:
    if oid not in all_ids:
        all_missing_ids_across_templates.add(oid)

# -----------------------------
# Overall Summary Across All Templates (PDF)
# -----------------------------
pdf.set_font("Helvetica", 'B', 12)
pdf.cell(0, 8, "--- Overall Summary Across All Templates ---",
         new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_font("Helvetica", '', 12)

total_checked = len(all_ids_across_templates)
total_missing = len(all_missing_ids_across_templates)
total_found = total_checked - total_missing

summary_items = [
    ("Total Templates", len(templates)),
    ("Total IDs Referenced in Templates", total_ids_referenced),
    ("Total Unique IDs Checked (excluding GENEPIO)", total_checked),
    ("Total Unique Found in Ontology", total_found),
    ("Total Unique Missing in Ontology", total_missing)
]

for label, value in summary_items:
    pdf.cell(100, 7, label, border=1)
    pdf.cell(40, 7, str(value), border=1)
    pdf.ln(7)
pdf.ln(5)

# -----------------------------
# Notes / Explanation
# -----------------------------
pdf.set_font("Helvetica", '', 9)
line_height = 5
note_lines = [
    ("Total Templates",
     " indicates how many DataHarmonizer templates were analyzed."),
    ("Total IDs Referenced in Templates",
     " counts every ontology ID usage across all templates, including duplicates."),
    ("Total Unique IDs Checked",
     " counts distinct ontology IDs across all templates (excluding GENEPIO IDs) that were checked against genepio-merged.owl ontology."),
    ("Total Unique Found IDs",
     " counts how many of these unique IDs were found in genepio-merged.owl ontology."),
    ("Total Unique Missing IDs",
     " counts how many unique IDs were not found in genepio-merged.owl ontology.")
]

for bold_text, normal_text in note_lines:
    pdf.set_font("Helvetica", 'B', 9)
    pdf.write(line_height, bold_text)
    pdf.set_font("Helvetica", '', 9)
    pdf.write(line_height, normal_text)
    pdf.ln(line_height)
pdf.ln(7)

# -----------------------------
# Templates Included (Clickable Links)
# -----------------------------
pdf.set_font("Helvetica", 'B', 12)
pdf.cell(0, 8, "--- Templates Included ---", new_x=XPos.LMARGIN,
         new_y=YPos.NEXT)
pdf.set_font("Helvetica", '', 12)

template_links = {}
for template in templates:
    link = pdf.add_link()
    template_links[template["name"]] = link
    pdf.set_text_color(0, 0, 255)
    pdf.cell(0, 6, f"- {template['name']}", new_x=XPos.LMARGIN,
             new_y=YPos.NEXT, link=link)
pdf.set_text_color(0, 0, 0)
pdf.ln(5)

# -----------------------------
# Unique Missing IDs by Ontology Prefix (PDF Table)
# -----------------------------
unique_missing_prefix_counts = defaultdict(int)
for oid in all_missing_ids_across_templates:
    prefix = oid.split(":")[0]
    unique_missing_prefix_counts[prefix] += 1

pdf.set_font("Helvetica", 'B', 12)
pdf.cell(0, 8, "--- Top Missing Ontology Prefixes (Unique IDs) ---",
         new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_font("Helvetica", 'B', 11)
pdf.cell(60, 7, "Ontology Prefix", border=1)
pdf.cell(40, 7, "Unique Missing IDs", border=1)
pdf.ln(7)

pdf.set_font("Helvetica", '', 11)
for prefix, count in sorted(unique_missing_prefix_counts.items(),
                            key=lambda x: x[1], reverse=True):
    pdf.cell(60, 7, prefix, border=1)
    pdf.cell(40, 7, str(count), border=1)
    pdf.ln(7)
pdf.ln(5)
pdf.add_page()
# -----------------------------
# Detailed Template Analysis
# -----------------------------
pdf.set_font("Helvetica", 'B', 14)
pdf.cell(0, 10, "Detailed Template Analysis", new_x=XPos.LMARGIN,
         new_y=YPos.NEXT)
pdf.ln(5)

for template in templates:
    template_name = template["name"]
    pdf.set_link(template_links[template_name])

    slots_df = pd.read_csv(template["slots_file"], sep="\t", dtype=str)
    enums_df = pd.read_csv(template["enums_file"], sep="\t", dtype=str)
    slots_ids = set(slots_df["slot_uri"].dropna())
    enums_ids = set(enums_df["meaning"].dropna())
    all_ids_raw = slots_ids.union(enums_ids)
    gene_ids = {oid for oid in all_ids_raw if
                oid.startswith("GENEPIO:")}
    external_ids = all_ids_raw - gene_ids

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

    pdf.cell(50, 7, "GENEPIO skipped:", border=1)
    pdf.cell(50, 7, str(len(gene_ids)), border=1)
    pdf.ln(7)

    pdf.cell(50, 7, "Checked IDs:", border=1)
    pdf.cell(50, 7, str(len(external_ids)), border=1)
    pdf.ln(7)

    # Missing by prefix for this template
    missing_ids = [oid for oid in external_ids if oid not in all_ids]
    missing_by_prefix = defaultdict(int)
    for mid in missing_ids:
        prefix = mid.split(":")[0]
        missing_by_prefix[prefix] += 1

    pdf.set_font("Helvetica", '', 11)
    pdf.cell(0, 7, "--- Missing IDs by Ontology Prefix ---",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", '', 10)
    for prefix, count in sorted(missing_by_prefix.items(),
                                key=lambda x: x[1], reverse=True):
        pdf.cell(0, 6, f"{prefix} - Missing: {count}",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.add_page()

# -----------------------------
# Save outputs
# -----------------------------
pdf_file = "Import_Checker_Report.pdf"
tsv_file = "Import_Checker_Output.tsv"
pdf.output(pdf_file)
print(f"✅ PDF report generated: {pdf_file}")

# TSV with all templates listed per ID
tsv_rows_final = []
for oid, info in id_to_templates.items():
    tsv_rows_final.append({
        "Ontology ID": oid,
        "Template": ", ".join(sorted(info["templates"])),
        "Template Source": ", ".join(sorted(info["sources"])),
        "Status": info["status"],
        "Report Generated": date_str
    })

tsv_rows_final = sorted(tsv_rows_final, key=lambda x: x["Ontology ID"])
tsv_df = pd.DataFrame(tsv_rows_final)
tsv_df.to_csv(tsv_file, sep="\t", index=False)
print(f"✅ TSV output generated: {tsv_file}")