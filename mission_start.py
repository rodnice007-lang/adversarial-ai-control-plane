# Control Plane: Validation + Classification


security_events = [
    {"risk_score": 20, "input_valid": True, "checks": ["validate", "verify"]},
    {"risk_score": 65, "input_valid": True, "checks": ["validate", "verify"]},
    {"risk_score": 90, "input_valid": True, "checks": ["validate", "verify"]},
    {"risk_score": 40, "input_valid": False, "checks": ["validate", "verify"]},
    {"input_valid": True, "checks": ["validate"]}
]


for idx, event in enumerate(security_events):

    print(f"\nProcessing Event {idx}")

    # ✅ Class 6: nested checks (ADD THIS)
    if "checks" in event:
        for check in event["checks"]:
            print(f"Running check: {check}")

    # ✅ VALIDATION (keep only one version)

    if "risk_score" not in event:
        print("⚠️ Validation Failed: Missing risk_score → Reject")
        continue

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