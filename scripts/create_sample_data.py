from pathlib import Path
import pandas as pd

rows = [
    {
        "rfi_id": 1,
        "project_name": "Ithaca Medical Office",
        "trade": "Structural",
        "spec_section": "033000",
        "subject": "Anchor bolt spacing at column base",
        "question_text": "Please confirm required anchor bolt spacing at grid B3 column base where existing conditions differ from structural detail.",
        "response_text": "Provide anchor bolt spacing per structural detail S5.2 unless field-verified dimensions require adjustment approved by the structural engineer."
    },
    {
        "rfi_id": 2,
        "project_name": "Ithaca Medical Office",
        "trade": "Electrical",
        "spec_section": "260500",
        "subject": "Conduit routing above corridor ceiling",
        "question_text": "Can conduit be routed above the corridor ceiling in the area with limited clearance due to ductwork conflict?",
        "response_text": "Route conduit above corridor ceiling where feasible. Coordinate final routing with mechanical trades and maintain required clearances."
    },
    {
        "rfi_id": 3,
        "project_name": "Student Housing Phase 2",
        "trade": "Architectural",
        "spec_section": "081113",
        "subject": "Door frame clearance at masonry opening",
        "question_text": "Please confirm acceptable door frame clearance where masonry opening exceeds scheduled width by 1 inch.",
        "response_text": "Shim and align frame plumb within manufacturer tolerances. Any excessive opening variation beyond tolerance shall be corrected before final installation."
    },
    {
        "rfi_id": 4,
        "project_name": "Student Housing Phase 2",
        "trade": "Mechanical",
        "spec_section": "230593",
        "subject": "Pipe support spacing in ceiling space",
        "question_text": "Please confirm required support spacing for copper piping above corridor ceiling.",
        "response_text": "Install supports in accordance with specification section 230593 and manufacturer requirements. Coordinate spacing around other overhead systems."
    },
    {
        "rfi_id": 5,
        "project_name": "Downtown Retail Renovation",
        "trade": "Plumbing",
        "spec_section": "220500",
        "subject": "Floor drain elevation conflict",
        "question_text": "Floor drain elevation conflicts with slab depression shown on architectural plan. Please confirm controlling elevation.",
        "response_text": "Use architectural floor finish elevation as controlling reference and coordinate final drain setting with plumbing and structural drawings."
    },
    {
        "rfi_id": 6,
        "project_name": "Downtown Retail Renovation",
        "trade": "Electrical",
        "spec_section": "262726",
        "subject": "Receptacle mounting height at millwork",
        "question_text": "Confirm mounting height for receptacles above custom millwork where dimensions are not shown.",
        "response_text": "Set receptacles to coordinate with approved millwork shop drawings and maintain code-required accessibility and clearance."
    },
]

df = pd.DataFrame(rows)
out = Path("data/raw/rfis.csv")
out.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out, index=False)

print(f"Wrote {len(df)} sample RFIs to {out}")
