# config.py

# Path to DataHarmonizer templates
templates_folder = "/Users/anoosha/GitHub/import_checker/templates/"

# Path to GenEpiO merged ontology
owl_file = "/Users/anoosha/GitHub/GenEpiO/src/ontology/genepio-merged.owl"

# Output folder for PDF and TSV reports
output_folder = "/Users/anoosha/GitHub/import_checker/Output Reports/"

# -----------------------------
# Additional config for consistency check
# -----------------------------
# Columns to check for IDs
check_columns = ["menu_1", "menu_2", "menu_3", "text"]

# Prefixes to skip (like GENEPIO IDs)
skip_prefixes = ["genepio:"]

# Regex pattern for valid IDs
id_pattern = r"[A-Za-z0-9_-]+:[A-Za-z0-9_-]+"