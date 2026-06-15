import time
from security_control import evaluate_control_plane_request

# Merging your event validation checks into unified testing assertions
ATTACK_SCENARIOS = {
    "Brute Force Check": [
        {"user_role": "attacker_script", "action": "admin_access", "has_mfa": False, "input_valid": True,
         "expected": "REJECT"},
        {"user_role": "attacker_script", "action": "admin_access", "has_mfa": False, "input_valid": True,
         "expected": "REJECT"},
        {"user_role": "attacker_script", "action": "admin_access", "has_mfa": False, "input_valid": True,
         "expected": "REJECT"}
    ],
    "Input Malformation Check (Your Event 3)": [
        {"user_role": "admin", "action": "data_read", "has_mfa": True, "input_valid": False, "expected": "REJECT"}
    ],
    "Privileged Abuse Flight": [
        {"user_role": "analyst", "action": "sys_shutdown", "has_mfa": True, "input_valid": True, "expected": "REJECT"}
    ],
    "Weak Authentication Check": [
        {"user_role": "engineer", "action": "admin_access", "has_mfa": False, "input_valid": True,
         "expected": "ISOLATE"}
    ],
    "Clean Traffic Baseline": [
        {"user_role": "admin", "action": "admin_access", "has_mfa": True, "input_valid": True, "expected": "ALLOW"}
    ]
}


def run_tests():
    total = 0
    passed = 0
    print("\n🚀 RUNNING ALIGNED SYSTEM EXPLOIT MATRIX\n" + "=" * 60)

    for scenario, events in ATTACK_SCENARIOS.items():
        print(f"📡 TESTING BLOCK: {scenario}")
        for e in events:
            total += 1
            # Passing parameters cleanly to our core module interface
            result = evaluate_control_plane_request(
                user_role=e["user_role"],
                action=e["action"],
                has_mfa=e["has_mfa"],
                input_valid=e["input_valid"]
            )
            actual = result["decision"]
            expected = e["expected"]

            if actual == expected:
                print(f"  PASS ✅ Log Output: {result}")
                passed += 1
            else:
                print(f"  FAIL ❌ Expected: {expected} | Got: {actual} | Log: {result}")
            time.sleep(0.01)
        print("-" * 60)

    print(f"\n📊 SYSTEM VERIFICATION SCORE: {passed}/{total}")


if __name__ == "__main__":
    run_tests()