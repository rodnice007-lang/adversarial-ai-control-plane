from datetime import datetime, timezone

# ==========================================
# CENTRAL ACCREDITATION & ACCESS POLICIES
# ==========================================
POLICIES = {
    "admin_access": {"allowed_roles": ["admin", "engineer"], "requires_mfa": True},
    "data_read": {"allowed_roles": ["admin", "engineer", "analyst"], "requires_mfa": False},
    "malicious_injection": {"allowed_roles": [], "requires_mfa": True},
    "sys_shutdown": {"allowed_roles": ["admin"], "requires_mfa": True}
}

TRAFFIC_HISTORY = {}
RATE_LIMIT_WINDOW = 2.0
MAX_REQUESTS_IN_WINDOW = 2


def calculate_risk(user_role, action, has_mfa, is_flooding, input_valid=True):
    """Computes risk, instantly slamming the score to max if input is invalid."""
    if not input_valid:
        return 99  # Invalid data format triggers an immediate critical score
    if is_flooding:
        return 100
    if action == "malicious_injection":
        return 95
    if action == "sys_shutdown" and user_role != "admin":
        return 85
    if user_role in ["guest", "attacker_script"]:
        return 70
    if action == "admin_access" and not has_mfa:
        return 60
    return 15


def determine_state(risk_score):
    if risk_score >= 80:
        return "REJECT"
    elif risk_score >= 50:
        return "ISOLATE"
    elif risk_score >= 20:
        return "ENFORCE"
    else:
        return "ALLOW"


def evaluate_control_plane_request(user_role, action, has_mfa, input_valid=True):
    """Processes incoming data packets through the centralized security logic matrix."""
    now = datetime.now(timezone.utc)
    timestamp = now.isoformat()
    epoch = now.timestamp()

    # Input validation tracking check
    if not input_valid:
        return generate_log(timestamp, user_role, action, "REJECT", "Invalid Input Format", 99)

    key = f"{user_role}:{action}"
    if key not in TRAFFIC_HISTORY:
        TRAFFIC_HISTORY[key] = []

    TRAFFIC_HISTORY[key] = [t for t in TRAFFIC_HISTORY[key] if epoch - t <= RATE_LIMIT_WINDOW]
    TRAFFIC_HISTORY[key].append(epoch)

    is_flooding = len(TRAFFIC_HISTORY[key]) > MAX_REQUESTS_IN_WINDOW

    risk_score = calculate_risk(user_role, action, has_mfa, is_flooding, input_valid)
    state = determine_state(risk_score)

    if state == "REJECT":
        reason = "Rate Limit Triggered" if is_flooding else "High Risk Vulnerability"
        return generate_log(timestamp, user_role, action, state, reason, risk_score)

    if action not in POLICIES:
        return generate_log(timestamp, user_role, action, "REJECT", "Unknown Action Target", risk_score)

    policy = POLICIES[action]
    if user_role not in policy["allowed_roles"]:
        return generate_log(timestamp, user_role, action, "REJECT", "Unauthorized Identity Role", risk_score)

    if policy["requires_mfa"] and not has_mfa:
        return generate_log(timestamp, user_role, action, "ISOLATE", "MFA Authentication Required", risk_score)

    return generate_log(timestamp, user_role, action, state, "Policy Controls Passed", risk_score)


def generate_log(timestamp, user, action, decision, reason, risk_score):
    return {
        "timestamp": timestamp,
        "user_role": user,
        "action": action,
        "decision": decision,
        "reason": reason,
        "risk_score": risk_score
    }