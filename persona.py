# persona.py
import json

persona = {
    "name": "취준생",
    "spending": {
        "카페": 200000,
        "배달": 100000,
        "교통": 150000
    },
    "priority": "할인"
}

with open("persona.json", "w", encoding="utf-8") as f:
    json.dump(persona, f, ensure_ascii=False, indent=4)

print("persona.json 저장 완료")
