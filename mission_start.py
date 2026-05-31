# Control Plane: Validation + Classification + Enforcement

security_events = [
    {"risk_score": 20, "input_valid": True, "checks": ["validate", "verify"]},
    {"risk_score": 65, "input_valid": True, "checks": ["validate", "verify"]},
    {"risk_score": 90, "input_valid": True, "checks": ["validate", "verify"]},
    {"risk_score": 40, "input_valid": False, "checks": ["validate", "verify"]},
    {"input_valid": True, "checks": ["validate"]}
]

for idx, event in enumerate(security_events):

    print(f"\nProcessing Event {idx}")

    # Nested checks
    if "checks" in event:
        for check in event["checks"]:
            print(f"Running check: {check}")

    # VALIDATION
    if "risk_score" not in event:
        print("⚠️ Validation Failed: Missing risk_score → REJECT")
        continue

    if not event["input_valid"]:
        print("❌ Validation Failed: Invalid input → REJECT")
        continue

    # SAFE TO PROCESS
    score = event["risk_score"]
    print(f"✅ Validation Passed | Risk Score: {score}")

    # ✅ ENFORCEMENT LAYER
    if score > 80:
        action = "BLOCK"
        print("🚫 Threat Level: HIGH")
    elif score > 50:
        action = "ISOLATE"
        print("⚠️ Threat Level: MEDIUM")
    else:
        action = "ALLOW"
        print("✅ Threat Level: LOW")

    print(f"✅ Enforcement Action: {action}")