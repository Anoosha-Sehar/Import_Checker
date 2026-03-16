import pandas as pd
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

# -------------------------------------------------
# Make parent folder visible so we can import config
# -------------------------------------------------
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import templates_folder, output_folder, skip_prefixes, id_pattern

# -------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------

def extract_ids_from_text(text):
    """
    Extract all ontology IDs inside square brackets.
    Example:
    Pork meat [FOODON:02021718]
    """
    if pd.isna(text):
        return []
    return re.findall(r"\[([A-Za-z0-9_-]+:[A-Za-z0-9_-]+)\]", str(text))


def normalize_prefix(oid, canonical_prefix_map):
    """
    Normalize prefix casing (FOODON vs foodon etc.)
    """
    if ":" not in oid:
        return oid
    prefix, rest = oid.split(":", 1)
    canonical_prefix = canonical_prefix_map.get(prefix.lower(), prefix)
    return f"{canonical_prefix}:{rest}"


def is_valid_id(oid):
    """
    Validate ID format and skip unwanted prefixes.
    """
    if not re.match(id_pattern, oid):
        return False
    for sp in skip_prefixes:
        if oid.lower().startswith(sp):
            return False
    return True


# -------------------------------------------------
# LOAD TEMPLATES
# -------------------------------------------------

templates = []

slots_files = sorted(
    [f for f in os.listdir(templates_folder) if f.endswith("-slots.tsv")]
)

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

if not templates:
    raise RuntimeError("No valid templates found.")

print(f"✅ Templates loaded: {[t['name'] for t in templates]}")


# -------------------------------------------------
# DETERMINE CANONICAL PREFIX CASING
# -------------------------------------------------

prefix_case_counter = defaultdict(lambda: defaultdict(int))

for template in templates:
    enums_df = pd.read_csv(template["enums_file"], sep="\t", dtype=str)

    for col in enums_df.columns:
        for val in enums_df[col].dropna():
            ids = extract_ids_from_text(val)
            for oid in ids:
                prefix = oid.split(":")[0]
                prefix_case_counter[prefix.lower()][prefix] += 1

canonical_prefix_map = {
    pl: max(cases.items(), key=lambda x: x[1])[0]
    for pl, cases in prefix_case_counter.items()
}


# -------------------------------------------------
# CONSISTENCY CHECK (One row per Meaning)
# -------------------------------------------------

rows = []
check_columns = ["menu_1", "menu_2", "menu_3", "text"]

for template in templates:
    template_name = template["name"]
    enums_df = pd.read_csv(template["enums_file"], sep="\t", dtype=str)

    if "meaning" not in enums_df.columns:
        continue

    for _, row in enums_df.iterrows():

        meaning_raw = row.get("meaning", "")
        if pd.isna(meaning_raw):
            continue

        meaning_id = meaning_raw.strip()

        if not is_valid_id(meaning_id):
            continue

        meaning_id = normalize_prefix(meaning_id, canonical_prefix_map)

        found_ids = []
        found_columns = []
        mismatch_details = []

        # Check each column individually
        for col in check_columns:
            if col not in enums_df.columns:
                continue

            cell_value = row.get(col)
            menu_ids = extract_ids_from_text(cell_value)

            normalized_menu_ids = [
                normalize_prefix(mid, canonical_prefix_map)
                for mid in menu_ids
                if is_valid_id(mid)
            ]

            if normalized_menu_ids:
                found_columns.append(col)

            for mid in normalized_menu_ids:
                found_ids.append(mid)
                if mid != meaning_id:
                    mismatch_details.append(f"{col} [{mid}]")

        # -------------------------------------------------
        # Decide Status
        # -------------------------------------------------

        if not found_ids:
            status = "Missing in Menu/Text"
        elif meaning_id in found_ids:
            status = "OK"
        else:
            mismatch_text = ", ".join(mismatch_details)
            status = f"Mismatch: {mismatch_text} ≠ Meaning [{meaning_id}]"

        rows.append({
            "Ontology ID": meaning_id,
            "Template": template_name,
            "Columns Found": ", ".join(found_columns),
            "Status": status,
            "Report Generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })


# -------------------------------------------------
# SAVE REPORT
# -------------------------------------------------

os.makedirs(output_folder, exist_ok=True)

output_file = os.path.join(
    output_folder,
    "Consistency_Check_Report.tsv"
)

pd.DataFrame(rows).to_csv(output_file, sep="\t", index=False)

print(f"✅ Consistency check report generated: {output_file}")