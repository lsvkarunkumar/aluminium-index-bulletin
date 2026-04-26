from pathlib import Path
import pandas as pd


DATA_DIR = Path("data")
MASTER_FILE = DATA_DIR / "master_index_list.csv"
OUTPUT_FILE = DATA_DIR / "master_index_final.csv"


# ---------------------------
# FIXED GRAPH ITEMS (LOCKED)
# ---------------------------
FIXED_ITEMS = {
    "SMM Aluminum Index",
    "Petroleum Coke Index",
    "Prebaked Anode",
    "Coal Tar Pitch",
}


# ---------------------------
# SECTION ORDER (LOCKED)
# ---------------------------
SECTION_ORDER = [
    "Primary Aluminium",
    "Alumina & Bauxite",
    "Carbon Raw Materials",
    "Carbon Products",
    "Alloy",
    "Processing Products",
    "Scrap",
    "Other",
]


def map_section(name):
    n = name.lower()

    if "aluminum index" in n or "ingot" in n or "premium" in n:
        return "Primary Aluminium"

    if "alumina" in n or "hydroxide" in n or "bauxite" in n:
        return "Alumina & Bauxite"

    if "coke" in n or "pitch" in n:
        return "Carbon Raw Materials"

    if "anode" in n:
        return "Carbon Products"

    if "alloy" in n:
        return "Alloy"

    if any(x in n for x in ["billet", "rod", "foil", "plate", "sheet", "strip", "extrusion", "coil"]):
        return "Processing Products"

    if "scrap" in n:
        return "Scrap"

    return "Other"


def map_sub_section(name):
    n = name.lower()

    if "index" in n:
        return "Index"
    if "premium" in n:
        return "Premium"
    if "coke" in n:
        return "CPC"
    if "pitch" in n:
        return "Pitch"
    if "anode" in n:
        return "Anode"
    if "alloy" in n:
        return "Alloy"
    if "billet" in n:
        return "Billet"
    if "rod" in n:
        return "Rod"
    if "foil" in n:
        return "Foil"
    if "plate" in n or "sheet" in n:
        return "Flat Products"
    if "extrusion" in n:
        return "Extrusion"
    if "coil" in n:
        return "Coil"

    return ""


def main():
    df = pd.read_csv(MASTER_FILE)

    # Apply correct structure
    df["Section"] = df["Index Name"].apply(map_section)
    df["Sub Section"] = df["Index Name"].apply(map_sub_section)

    # Flags
    df["Fixed Graph"] = df["Index Name"].apply(lambda x: "YES" if x in FIXED_ITEMS else "NO")
    df["Dropdown Graph"] = "YES"

    # Order Sections
    df["Section Order"] = df["Section"].apply(lambda x: SECTION_ORDER.index(x) if x in SECTION_ORDER else 999)

    # Sort
    df = df.sort_values(by=["Section Order", "Sub Section", "Index Name"])

    # Clean columns
    df = df.drop(columns=["Section Order"])

    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(f"Final structured master created: {len(df)} rows")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
