print("SCRIPT STARTED")

import time
from control_plane.continuous_control_plane import evaluate_control_plane_request

ATTACK_SCENARIOS = {
    "Basic Test": [
        {"user_role": "admin", "action": "admin_access", "has_mfa": True, "input_valid": True, "expected": "ALLOW"}
    ]
}

def run_tests():
    print("RUNNING TESTS")

    for scenario, events in ATTACK_SCENARIOS.items():
        print("\n[SCENARIO]", scenario)

        for e in events:
            result = evaluate_control_plane_request(
                user_role=e["user_role"],
                action=e["action"],
                has_mfa=e["has_mfa"],
                input_valid=e["input_valid"]
            )

            print("RESULT:", result)

            time.sleep(0.01)

if __name__ == "__main__":
    run_tests()
