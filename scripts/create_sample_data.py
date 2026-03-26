import pandas as pd
from pathlib import Path

data = [
    {
        "rfi_id": 1,
        "project_name": "North Hall Renovation",
        "trade": "Structural",
        "spec_section": "03 30 00",
        "subject": "Rebar spacing at shear wall",
        "question_text": "Please confirm required rebar spacing at the level 2 shear wall near grid B3 because the drawings appear inconsistent.",
        "response_text": "Use 12 inches on center as indicated in structural detail S-421. The architectural sheet is not governing for rebar spacing.",
        "status": "Closed",
        "date_created": "2026-01-10",
    },
    {
        "rfi_id": 2,
        "project_name": "North Hall Renovation",
        "trade": "Electrical",
        "spec_section": "26 05 00",
        "subject": "Conduit routing conflict above ceiling",
        "question_text": "There is a conflict between conduit routing and ductwork above corridor C on level 1. Please advise acceptable reroute.",
        "response_text": "Route conduit along the east side of the corridor and maintain required clearance from ductwork. Coordinate final path with mechanical contractor.",
        "status": "Closed",
        "date_created": "2026-01-14",
    },
    {
        "rfi_id": 3,
        "project_name": "West Medical Office",
        "trade": "Mechanical",
        "spec_section": "23 07 00",
        "subject": "Pipe insulation thickness",
        "question_text": "Please confirm insulation thickness for chilled water piping in mechanical room 102.",
        "response_text": "Provide 1.5 inch insulation thickness in mechanical room 102 in accordance with spec section 23 07 00.",
        "status": "Closed",
        "date_created": "2026-01-20",
    },
    {
        "rfi_id": 4,
        "project_name": "West Medical Office",
        "trade": "Architectural",
        "spec_section": "09 29 00",
        "subject": "Drywall finish level in lobby",
        "question_text": "Please confirm drywall finish level required in the main lobby feature wall.",
        "response_text": "Provide level 5 finish at the main lobby feature wall due to paint sheen and lighting conditions.",
        "status": "Closed",
        "date_created": "2026-01-22",
    },
    {
        "rfi_id": 5,
        "project_name": "East Parking Structure",
        "trade": "Civil",
        "spec_section": "31 20 00",
        "subject": "Subgrade compaction requirement",
        "question_text": "Please confirm required compaction percentage for subgrade beneath the access drive.",
        "response_text": "Subgrade beneath the access drive shall be compacted to 95 percent of maximum dry density.",
        "status": "Closed",
        "date_created": "2026-02-01",
    },
    {
        "rfi_id": 6,
        "project_name": "East Parking Structure",
        "trade": "Structural",
        "spec_section": "03 30 00",
        "subject": "Concrete strength at elevated slab",
        "question_text": "Please confirm required concrete compressive strength for the elevated slab at level 3.",
        "response_text": "Provide 5000 psi concrete at 28 days for the elevated slab at level 3.",
        "status": "Closed",
        "date_created": "2026-02-05",
    },
    {
        "rfi_id": 7,
        "project_name": "South Lab Expansion",
        "trade": "Plumbing",
        "spec_section": "22 11 00",
        "subject": "Domestic water pipe material",
        "question_text": "Please confirm whether domestic cold water piping above ceiling in lab support space should be copper or PEX.",
        "response_text": "Use type L copper piping above ceiling in lab support spaces. PEX is not permitted in this area.",
        "status": "Closed",
        "date_created": "2026-02-11",
    },
    {
        "rfi_id": 8,
        "project_name": "South Lab Expansion",
        "trade": "Electrical",
        "spec_section": "26 24 16",
        "subject": "Panel schedule discrepancy",
        "question_text": "The panel schedule on sheet E-601 does not match circuiting shown on sheet E-211 for lab bench receptacles. Please confirm which should govern.",
        "response_text": "Sheet E-211 governs for receptacle circuiting at lab benches. Revise panel schedule accordingly.",
        "status": "Closed",
        "date_created": "2026-02-18",
    },
]

output_path = Path("data/raw/rfis.csv")
output_path.parent.mkdir(parents=True, exist_ok=True)

df = pd.DataFrame(data)
df.to_csv(output_path, index=False)

print(f"Created sample dataset at {output_path}")
print(df[["rfi_id", "trade", "subject"]].to_string(index=False))
