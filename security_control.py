security_state = {
    "prompt_injection_attempts": 0,
    "jailbreak_attempts": 0,
    "risk_score": 0,
    "input_valid": True
}
security_state["prompt_injection_attempts"] += 1
security_state["risk_score"] = 85
if security_state["risk_score"] > 80:
    print("⚠️ High risk detected — blocking input")
else:
    print("✅ Input allowed")
