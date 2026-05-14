# Control Plane: Validation + Classification

security_events = [
    {"risk_score": 20, "input_valid": True},
    {"risk_score": 65, "input_valid": True},
    {"risk_score": 90, "input_valid": True},
    {"risk_score": 40, "input_valid": False},   # invalid test case
    {"input_valid": True}                       # missing risk_score test case
]

for idx, event in enumerate(security_events):

    print(f"\nProcessing Event {idx}")

    # ✅ VALIDATION LAYER

    # 1. Check required keys exist
    if "risk_score" not in event:
        print("⚠️ Validation Failed: Missing risk_score → Reject")
        continue

    # 2. Check input validity
    if not event["input_valid"]:
        print("❌ Validation Failed: Invalid input → Reject")
        continue

    # ✅ SAFE TO PROCESS
    score = event["risk_score"]

    print(f"✅ Validation Passed | Risk Score: {score}")

    # ✅ CLASSIFICATION + ENFORCEMENT

    if score > 80:
        print("🚫 Threat Level: HIGH")
        print("Action: BLOCK")
    elif score > 50:
        print("⚠️ Threat Level: MEDIUM")
        print("Action: MONITOR")
    else:
        print("✅ Threat Level: LOW")
        print("Action: ALLOW")