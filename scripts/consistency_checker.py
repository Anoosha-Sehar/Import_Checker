import pandas as pd
import os
import re
from collections import defaultdict
from datetime import datetime

# -----------------------------
# CONFIG
# -----------------------------
templates_folder = "/Users/anoosha/GitHub/import_checker/templates/"
output_folder = "/Users/anoosha/GitHub/import_checker/Output Reports/"
os.makedirs(output_folder, exist_ok=True)

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def extract_id_from_text(text):
    """Extract ID inside brackets if exists, else return text itself."""
    text = str(text).strip()
    match = re.search(r"\[([A-Za-z0-9:_-]+)\]", text)
    return match.group(1) if match else text

def normalize_prefix(oid, canonical_prefix_map):
    """Fix prefix casing based on majority-case mapping."""
    if ":" not in oid:
        return oid
    prefix, rest = oid.split(":", 1)
    canonical_prefix = canonical_prefix_map.get(prefix.lower(), prefix)
    return f"{canonical_prefix}:{rest}"

# -----------------------------
# LOAD TEMPLATES
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
# Determine canonical prefix casing (majority-based)
# -----------------------------
prefix_case_counter = defaultdict(lambda: defaultdict(int))
for template in templates:
    slots_df = pd.read_csv(template["slots_file"], sep="\t", dtype=str)
    enums_df = pd.read_csv(template["enums_file"], sep="\t", dtype=str)
    all_ids_raw = set(slots_df["slot_uri"].dropna()).union(enums_df["meaning"].dropna())
    for oid in all_ids_raw:
        if ":" in oid:
            prefix = oid.split(":")[0]
            prefix_case_counter[prefix.lower()][prefix] += 1

canonical_prefix_map = {
    pl: max(cases.items(), key=lambda x: x[1])[0]
    for pl, cases in prefix_case_counter.items()
}

# -----------------------------
# Consistency check
# -----------------------------
rows = []
for template in templates:
    template_name = template["name"]
    slots_df = pd.read_csv(template["slots_file"], sep="\t", dtype=str)
    enums_df = pd.read_csv(template["enums_file"], sep="\t", dtype=str)

    # Collect meaning IDs (skip GENEPIO)
    meaning_ids = {normalize_prefix(x.strip(), canonical_prefix_map)
                   for x in enums_df["meaning"].dropna()
                   if not str(x).strip().lower().startswith("genepio:")}

    # Prepare all IDs found in menus/text
    menu_text_ids = set()
    for col in ["menu_1", "menu_2", "menu_3", "text"]:
        if col in enums_df.columns:
            extracted_ids = enums_df[col].dropna().astype(str).apply(extract_id_from_text)
            # skip GENEPIO
            extracted_ids = [normalize_prefix(x.strip(), canonical_prefix_map)
                             for x in extracted_ids
                             if not x.lower().startswith("genepio:")]
            menu_text_ids.update(extracted_ids)

    # Union of all IDs to check
    all_ids_to_check = meaning_ids.union(menu_text_ids)

    for oid in all_ids_to_check:
        # Determine where it appears
        locations = []
        for col in ["menu_1", "menu_2", "menu_3", "text"]:
            if col in enums_df.columns:
                extracted_ids = enums_df[col].dropna().astype(str).apply(extract_id_from_text)
                extracted_ids = [normalize_prefix(x.strip(), canonical_prefix_map)
                                 for x in extracted_ids
                                 if not x.lower().startswith("genepio:")]
                if oid in set(extracted_ids):
                    locations.append(col)

        # Determine status
        if oid in meaning_ids and oid in menu_text_ids:
            # Appears in both meaning and menus/text
            # Check exact match across menus/text
            mismatch = False
            for col in ["menu_1", "menu_2", "menu_3", "text"]:
                if col in enums_df.columns:
                    extracted_ids = enums_df[col].dropna().astype(str).apply(extract_id_from_text)
                    extracted_ids = [normalize_prefix(x.strip(), canonical_prefix_map)
                                     for x in extracted_ids
                                     if not x.lower().startswith("genepio:")]
                    # If appears but differs (case/typo)
                    if any(x != oid for x in extracted_ids if x.lower() == oid.lower()):
                        mismatch = True
            status = "Mismatch" if mismatch else "OK"
        elif oid in meaning_ids and oid not in menu_text_ids:
            status = "Missing in Menu/Text"
        elif oid not in meaning_ids and oid in menu_text_ids:
            status = "Missing in Meaning"
        else:
            status = "Missing in menus/text"  # shouldn't normally happen

        rows.append({
            "Ontology ID": oid,
            "Template": template_name,
            "Columns Found": ", ".join(locations) if locations else "",
            "Status": status,
            "Report Generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

# -----------------------------
# Save TSV
# -----------------------------
output_file = os.path.join(output_folder, "Consistency_Check_Report.tsv")
pd.DataFrame(rows).to_csv(output_file, sep="\t", index=False)
print(f"✅ Consistency check report generated: {output_file}")