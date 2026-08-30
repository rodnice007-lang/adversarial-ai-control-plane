def evaluate_control_plane_request(user_role, action, has_mfa, input_valid, risk_score=0):

    # Step 1: input validation
    if not input_valid:
        return {"decision": "REJECT", "reason": "Invalid input"}

    # Step 2: enforce MFA
    if action == "admin_access" and not has_mfa:
        return {"decision": "REJECT", "reason": "Missing MFA"}

    # Step 3: malicious role
    if user_role == "attacker_script":
        return {"decision": "REJECT", "reason": "Malicious role"}

    # Step 4: weak auth
    if user_role == "engineer" and not has_mfa:
        return {"decision": "ISOLATE", "reason": "Weak authentication"}

    # Step 5: safe default
    return {"decision": "ALLOW", "reason": "Clean request"}

