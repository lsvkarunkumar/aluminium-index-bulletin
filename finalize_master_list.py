from pathlib import Path
import pandas as pd


DATA_DIR = Path("data")
INPUT_FILE = DATA_DIR / "cleaned_index_list.csv"
MASTER_FILE = DATA_DIR / "master_index_list.csv"


BAD_EXACT_NAMES = {
    "Aluminum Aluminum Ingot / SMM AAluminum Ingot",
    "Aluminum Ingot / SMM AAluminum Ingot",
}


def infer_section(name: str) -> str:
    n = name.lower()

    if "coke" in n or "pitch" in n:
        return "Carbon Raw Materials"
    if "anode" in n:
        return "Carbon Products"
    if "alumina" in n or "hydroxide" in n:
        return "Alumina"
    if "bauxite" in n:
        return "Bauxite"
    if "scrap" in n:
        return "Scrap"
    if "alloy" in n:
        return "Alloy"
    if any(x in n for x in ["billet", "rod", "foil", "plate", "sheet", "strip", "slab", "extrusion", "coil", "powder"]):
        return "Processing Products"
    if "premium" in n or "index" in n or "ingot" in n:
        return "Primary Aluminium"

    return "Other"


def infer_sub_section(name: str) -> str:
    n = name.lower()

    if "coke" in n:
        return "Petroleum Coke"
    if "pitch" in n:
        return "Coal Tar Pitch"
    if "anode" in n:
        return "Prebaked Anode"
    if "premium" in n:
        return "Premium"
    if "ingot" in n:
        return "Ingot"
    if "alloy" in n:
        return "Alloy"
    if "scrap" in n:
        return "Scrap"
    if "foil" in n:
        return "Foil"
    if "billet" in n:
        return "Billet"
    if "rod" in n:
        return "Rod"
    if "plate" in n or "sheet" in n or "strip" in n:
        return "Plate / Sheet / Strip"
    if "extrusion" in n:
        return "Extrusion"
    if "coil" in n:
        return "Coil"

    return ""


def main():
    df = pd.read_csv(INPUT_FILE)

    df = df[~df["Index Name"].isin(BAD_EXACT_NAMES)]

    df["Index Name"] = df["Index Name"].astype(str).str.strip()
    df = df[df["Index Name"] != ""]
    df = df.drop_duplicates(subset=["Index Name"], keep="last")

    df["Section"] = df["Index Name"].apply(infer_section)
    df["Sub Section"] = df["Index Name"].apply(infer_sub_section)

    required_cols = [
        "Section",
        "Sub Section",
        "Index Name",
        "SMM Code",
        "Column Name",
        "Currency",
        "Unit",
        "Source URL",
        "Active",
        "Review Status",
    ]

    for col in required_cols:
        if col not in df.columns:
            df[col] = ""

    df = df[required_cols]

    df.to_csv(MASTER_FILE, index=False, encoding="utf-8-sig")

    print(f"Master list finalized: {len(df)} rows")
    print(f"Saved to: {MASTER_FILE}")


if __name__ == "__main__":
    main()
