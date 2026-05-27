---
name: ctl-write-test
description: Write clear, maintainable, and effective tests based on defined requirements and behavior.
---

## Test Requirements

A testing task is considered **valid and actionable** only if it includes the following:

### Required

- **System Under Test (SUT)**
  Clearly identify the class, function, or module being tested.

- **Behavior to Validate**
  Define what behavior, rule, or outcome must be verified. Focus on observable outputs, not internal implementation.

- **Acceptance Criteria**  
  Explicit, testable conditions that define success. These should directly map to assertions.

### Optional (but recommended)

- **Edge Cases**
  Boundary conditions, invalid inputs, and failure scenarios.

- **Dependencies / Collaborators**
  External systems, services, or components that may need to be mocked or stubbed.

- **Test Data**
  Known inputs and expected outputs.

---

## Validation Rule

If any **required information is missing or unclear**, you must:
- Halt test implementation
- Do not infer intended behavior
- Ask for clarification

---

## Test Structure (Mandatory)

All tests MUST follow the **Arrange / Act / Assert (AAA)** pattern:

```text
Arrange: Set up inputs, dependencies, and test context
Act: Execute the system under test
Assert: Verify the expected outcome
```

### Example

```csharp
[Fact]
public void CalculateTotal_ShouldReturnSum_WhenInputsAreValid()
{
    // Arrange
    var calculator = new Calculator();
    var a = 5;
    var b = 10;

    // Act
    var result = calculator.CalculateTotal(a, b);

    // Assert
    result.Should().Be(15);
}
```

---

## Implementation Guidelines

- **Test Behavior, Not Implementation**
  - Avoid testing internal/private methods directly
  - Focus on inputs → outputs

- **Descriptive Naming**
  Use clear, consistent naming:
  ```csharp
  MethodName_ShouldExpectedBehavior_WhenCondition
  ```

  When applicable, provide a display name:
  ```csharp
  [Fact(DisplayName = "Case 123 - Should {ExpectedBehavior} when {Condition}")]
  ```

- **Single Responsibility per Test**
  - Each test should validate one behavior only
  - Avoid multiple assertions unless they validate the same outcome

- **Deterministic Tests**
  - Tests must be repeatable and produce consistent results
  - Avoid randomness, time-dependence, or external state unless controlled

- **Isolation**
  - Mock or stub external dependencies
  - Do not rely on real databases, APIs, or file systems unless explicitly required

- **Minimal Setup**
  - Only include what is necessary for the test

---

## Mocking & Dependencies

- Mock external dependencies when:
  - They introduce non-determinism
  - They are slow or expensive (e.g., database, network)
  - They are within the scope of the test

- Prefer:
  - Simple stubs for straightforward scenarios
  - Mocks only when verifying interactions is necessary

---

## Assertions

- Use **clear and expressive assertions**
- Prefer fluent/assertion libraries when available
- Assertions must directly reflect acceptance criteria

Examples:
```csharp
result.Should().Be(expected);
result.Should().NotBeNull();
result.Should().Throw<InvalidOperationException>();
```

---

## Edge Case Coverage

When edge cases are provided, ensure tests cover:
- Null or empty inputs
- Boundary values
- Invalid or malformed data
- Error conditions and exceptions

---

## Code Quality

- Follow existing project conventions
- Keep tests readable and concise
- Avoid duplication (extract helpers if needed, but do not over-abstract)

---

## Validation Before Completion

Ensure:
- All acceptance criteria are covered by tests
- Tests follow Arrange / Act / Assert structure
- Tests are deterministic and isolated
- Naming is clear and consistent
- No unnecessary complexity or duplication exists

---

## Execution Behavior

- Do not write tests without clear expected outcomes
- Do not assume behavior that is not explicitly defined
- Do not test implementation details
- Prefer clarity and maintainability over clever or compact tests
