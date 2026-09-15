import argparse
import csv
import re

ALLOWED_CATEGORIES = [
    "Pothole",
    "Flooding",
    "Streetlight",
    "Waste",
    "Noise",
    "Road Damage",
    "Heritage Damage",
    "Heat Hazard",
    "Drain Blockage",
    "Other",
]

SEVERITY_KEYWORDS = [
    "injury",
    "child",
    "school",
    "hospital",
    "ambulance",
    "fire",
    "hazard",
    "fell",
    "collapse",
]

CATEGORY_RULES = [
    ("Pothole", [r"\bpothole(s)?\b"]),
    ("Flooding", [r"\bflood(ed|ing|s)?\b", r"\bknee-deep\b", r"\bwaterlogged\b"]),
    ("Streetlight", [r"\bstreetlight(s)?\b", r"\blights? out\b", r"\blamp(s)?\b"]),
    ("Waste", [r"\bgarbage\b", r"\bwaste\b", r"\bbins?\b", r"\bdead animal\b", r"\bdump(ed)?\b"]),
    ("Noise", [r"\bnoise\b", r"\bmusic\b", r"\bloudspeaker(s)?\b", r"\bdecibel\b"]),
    ("Drain Blockage", [r"\bdrain(s)?\b", r"\bblockage\b", r"\bblocked drain\b", r"\bmanhole\b"]),
    ("Heritage Damage", [r"\bheritage\b", r"\bmonument\b", r"\bhistoric(al)?\b"]),
    ("Heat Hazard", [r"\bheat\b", r"\bheatwave\b", r"\bsunstroke\b"]),
    ("Road Damage", [r"\broad surface\b", r"\bfootpath\b", r"\btiles broken\b", r"\bsinking\b", r"\bcracked\b"]),
]


def classify_complaint(row: dict) -> dict:
    """
    Classify a single complaint row.
    Returns: dict with keys: complaint_id, category, priority, reason, flag
    """
    complaint_id = row.get("complaint_id", "").strip()
    desc = (row.get("description") or "").strip()
    loc = (row.get("location") or "").strip()
    text = f"{desc} {loc}".strip()

    if not desc:
        return {
            "complaint_id": complaint_id,
            "category": "Other",
            "priority": "Standard",
            "reason": "Missing complaint description.",
            "flag": "NEEDS_REVIEW",
        }

    lower_desc = desc.lower()

    # Check urgent severity keywords
    triggered_severity = [kw for kw in SEVERITY_KEYWORDS if re.search(rf"\b{kw}(ren)?\b", lower_desc)]
    if triggered_severity:
        priority = "Urgent"
    else:
        priority = "Standard"

    # Category matching
    matched_categories = []
    matched_phrases = []
    for cat, patterns in CATEGORY_RULES:
        for pat in patterns:
            match = re.search(pat, lower_desc)
            if match:
                if cat not in matched_categories:
                    matched_categories.append(cat)
                    matched_phrases.append(match.group(0))

    flag = ""
    if len(matched_categories) == 1:
        category = matched_categories[0]
        cite = matched_phrases[0]
    elif len(matched_categories) > 1:
        # Ambiguous complaint matching multiple categories
        category = matched_categories[0]
        cite = ", ".join(matched_phrases[:2])
        flag = "NEEDS_REVIEW"
    else:
        category = "Other"
        cite = desc[:30]
        flag = "NEEDS_REVIEW"

    # Construct one-sentence justification citing specific words
    if triggered_severity:
        reason = f"Classified as {category} based on '{cite}'; marked Urgent due to severity keyword '{triggered_severity[0]}'."
    else:
        reason = f"Classified as {category} because description refers to '{cite}'."

    return {
        "complaint_id": complaint_id,
        "category": category,
        "priority": priority,
        "reason": reason,
        "flag": flag,
    }


def batch_classify(input_path: str, output_path: str):
    """
    Read input CSV, classify each row, write results CSV.
    Must: flag nulls, not crash on bad rows, produce output even if some rows fail.
    """
    fieldnames = ["complaint_id", "category", "priority", "reason", "flag"]
    results = []

    with open(input_path, mode="r", encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            try:
                res = classify_complaint(row)
                results.append(res)
            except Exception as e:
                # Gracefully catch bad row and flag
                results.append({
                    "complaint_id": row.get("complaint_id", "UNKNOWN"),
                    "category": "Other",
                    "priority": "Standard",
                    "reason": f"Classification error: {str(e)}",
                    "flag": "NEEDS_REVIEW",
                })

    with open(output_path, mode="w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UC-0A Complaint Classifier")
    parser.add_argument("--input",  required=True, help="Path to test_[city].csv")
    parser.add_argument("--output", required=True, help="Path to write results CSV")
    args = parser.parse_args()
    batch_classify(args.input, args.output)
    print(f"Done. Results written to {args.output}")

