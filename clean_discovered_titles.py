from pathlib import Path
import re
import pandas as pd


DATA_DIR = Path("data")
INPUT_FILE = DATA_DIR / "discovered_index_list.csv"
OUTPUT_FILE = DATA_DIR / "cleaned_index_list.csv"


CODE_PATTERN = re.compile(r"\bSMM-[A-Z]+-[A-Z]+-\d+\b")


def clean_name(text):
    text = str(text).strip()

    # Remove live price/date fragments after SMM code
    code_match = CODE_PATTERN.search(text)
    if code_match:
        code = code_match.group(0)
        name = text[: code_match.start()].strip()
        return name, code

    # Remove visible price/date fragments
    text = re.sub(r"\b\d{1,2}/\d{1,2}/\d{4}\b", "", text)
    text = re.sub(r"\bUSD/tonne\b", "", text, flags=re.I)
    text = re.sub(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?\s*%?", "", text)

    text = " ".join(text.split()).strip()
    return text, ""


def is_category_only(name):
    category_only = {
        "Aluminum",
        "Aluminum Ingot",
        "Bauxite",
        "Alumina",
        "Imported Scrap",
        "Aluminum Accessory",
    }
    return name in category_only


def make_column_name(name):
    return f"{name} (USD/t)"


def main():
    df = pd.read_csv(INPUT_FILE)

    rows = []
    seen = set()

    for _, row in df.iterrows():
        raw = row.get("Index Name", "")
        name, smm_code = clean_name(raw)

        if not name:
            continue

        if is_category_only(name):
            continue

        key = name.lower()

        if key in seen:
            continue

        seen.add(key)

        rows.append(
            {
                "Section": "",
                "Sub Section": "",
                "Index Name": name,
                "SMM Code": smm_code,
                "Column Name": make_column_name(name),
                "Currency": "USD",
                "Unit": "t",
                "Source URL": row.get("Source URL", ""),
                "Active": "TRUE",
                "Review Status": "Pending",
            }
        )

    out = pd.DataFrame(rows)
    out.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(f"Cleaned rows saved: {len(out)}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
