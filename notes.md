# Adversarial AI Control Plane — Notes

---

## ✅ Project Anchors (How I Explain My System)

### 🔹 Opening / Closing Statement
"I built the control plane outside the AI so security decisions are independent, auditable, and something I can actually control."

---

### 🔹 How the System Works
"The control plane processes incoming events through a loop, validates each event, classifies its risk level based on policy thresholds, enforces a corresponding action, and logs the outcome for audit and traceability."

---

### 🔹 Recent Update (Class 6 — Nested Data)
"I extended the control plane to support nested data by adding a checks list to each event, and used a nested loop to process those checks while keeping validation, classification, and enforcement logic intact."

---

## ✅ System Understanding (What / When / Why / How)

### 🔹 Control Plane Core
- **What:** Processes events and enforces decisions
- **When:** Every event at runtime
- **Why:** Ensure independent, consistent, auditable decisions
- **How:** Loop → Validate → Classify → Enforce → Log

---

### 🔹 Event Processing Loop
- **What:** Iterates through each event
- **When:** Each loop cycle
- **Why:** Ensure no event is skipped
- **How:** `for idx, event in enumerate(security_events)`

---

### 🔹 Validation Layer
- **What:** Input validation
- **When:** Before classification
- **Why:** Prevent bad input from affecting logic
- **How:**
    - Check `"risk_score"` exists
    - Check `input_valid`

---

### 🔹 Classification + Enforcement
- **What:** Risk-based decision making
- **When:** After validation passes
- **Why:** Apply consistent policy
- **How:**
    - `> 80 → BLOCK`
    - `> 50 → MONITOR`
    - Else → ALLOW

---

### 🔹 Nested Data (Class 6)
- **What:** Each event includes multiple checks
- **When:** At start of processing
- **Why:** Allow more structured input
- **How:**
```python
for check in event["checks"]:
    print(f"Running check: {check}")

## ✅ Recent Milestone (Class 6)

- Added nested `checks` list to each event  
- Implemented nested loop to process checks  
- Maintained existing validation and classification logic  
- System remains stable and deterministic  

---
### 🔹 Nested Checks Execution (Class 6 Implementation)
- **What:** The system processes each check within an event
- **When:** Immediately after the event begins processing
- **Why:** To reflect that events may contain multiple checks or attributes
- **How:**
```python
if "checks" in event:
    for check in event["checks"]:
        print(f"Running check: {check}")

# Portfolio Code Log: Control Plane Evaluation Logic

## 1. (The Meaning)

Think of this like a security guard checking people at a gate.

Each person (event) comes up in line.  
The guard first checks if they have the right ID (valid data).  

If something is wrong (missing info or bad ID), the guard turns them away immediately.

If they pass, the guard then checks extra rules (checks list), like:
- Are they acting suspicious?
- Do they meet certain requirements?

After that, the guard gives a final decision:
- Safe → ALLOW
- Something looks off → MONITOR
- Dangerous → BLOCK

So the system is basically:
check → verify → decide

---

## 2. (The Code Logic)

1. Start with a list of events  
2. Loop through each event one at a time  
3. For each event:
   - Check if required data exists (`risk_score`)
   - Check if input is valid
4. If anything fails:
   - Add "REJECT" to the results
   - Skip to the next event
5. If it passes validation:
   - Extract the score
6. Check if there are additional checks:
   - Loop through each check
   - If a "verify" check fails:
       - Reject the event
       - Stop checking further rules
7. If the event is still valid:
   - Apply classification thresholds:
       - score > 80 → BLOCK
       - score > 50 → MONITOR
       - else → ALLOW
8. Store the decision
9. Return all results as a list

---

## 3.(Clean + Professional)

The control plane processes a list of structured events by iterating through each item and applying layered validation and decision logic.

First, it validates the integrity of each event by checking for required fields and input validity.  
Invalid or malformed inputs are rejected early to prevent them from influencing downstream logic.

Next, the system evaluates optional nested checks within each event, allowing for multi-signal inspection before classification.

Finally, it applies deterministic policy thresholds to assign a decision—ALLOW, MONITOR, or BLOCK—ensuring consistent and explainable enforcement.

This design demonstrates controlled data processing, layered validation, and policy-driven decision-making, which aligns with secure system design principles.        