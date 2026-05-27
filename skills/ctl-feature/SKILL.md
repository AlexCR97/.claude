---
name: ctl-feature
description: Implement a new feature based on clearly defined requirements.
---

## Feature Requirements

A task is considered **valid and actionable** only if it includes the specifications below.

### Required

- **Functional Requirements**  
  Define *what* the feature must do from a user or system perspective.  
  Focus on observable behavior, not implementation.

- **Technical Requirements**  
  Specify constraints, architecture decisions, dependencies, performance expectations, and integration points.  
  Include language, frameworks, APIs, data models, and non-functional requirements where relevant.

- **Acceptance Criteria**  
  Define explicit, testable conditions that must be satisfied for the feature to be considered complete.  
  These should be unambiguous and verifiable (e.g., Given/When/Then format is preferred).

### Optional (but recommended)

- **Edge Cases**  
  Identify boundary conditions, failure scenarios, and unusual inputs that must be handled gracefully.

- **References**  
  Provide links or pointers to relevant documentation, examples, designs, or prior implementations.

- **Additional Notes**  
  Any contextual information, assumptions, or constraints not covered above.

### Validation Rule

If any **required section is missing, incomplete, or ambiguous**, you must:
- Halt implementation
- Do not infer or fabricate missing requirements
- Ask the user for clarification

---

## Implementation Guidelines

- **Follow Existing Codebase Conventions**  
  Adhere strictly to established patterns, including:
  - Naming conventions
  - Project structure
  - Architectural style
  - Dependency usage

- **Language-Specific Standards (C#)**  
  When working in C#, comply with:
  ```
  ~/.claude/rules/csharp-conventions.md
  ```

- **Code Quality Principles**
  - Prefer clarity over cleverness
  - Keep functions, classes and modules responsible and focused on 1 thing only
  - Prefer data immutability when it makes sense
  - Avoid unnecessary abstraction
  - Ensure consistency with surrounding code

- **Comments Policy**
  - Do **not** add redundant or obvious comments
  - Add comments only when:
    - Explaining non-trivial business or domain logic
    - Clarifying intent that is not immediately obvious from the code
  - Favor self-explanatory code through good naming and structure

- **Validation Before Completion**
  Ensure:
  - All acceptance criteria are satisfied
  - Edge cases (if provided) are handled
  - Code integrates cleanly with the existing system
  - No assumptions violate the defined requirements

---

## Execution Behavior

- Do not proceed with partial understanding
- Do not introduce features outside the defined scope
- Do not optimize prematurely unless explicitly required
- Prefer deterministic, predictable implementations over speculative ones
