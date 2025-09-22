# scripts/add_ids_to_questions.py
import json, uuid, os

QFILE = "board/questions.json"  # adjust path if your file is elsewhere

if not os.path.exists(QFILE):
    print("questions.json not found")
    raise SystemExit(1)

with open(QFILE, "r", encoding="utf-8") as f:
    data = json.load(f)

changed = 0
for atype, levels in data.items():
    for lvl, qs in levels.items():
        for q in qs:
            if "id" not in q:
                q["id"] = str(uuid.uuid4())
                changed += 1

if changed:
    with open(QFILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Added id to {changed} questions")
else:
    print("All questions already have ids")
