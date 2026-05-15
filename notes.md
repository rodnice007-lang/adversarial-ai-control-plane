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