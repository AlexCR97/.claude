# SOLID Principles

## What is SOLID?

SOLID is an acronym for five object-oriented design principles introduced by Robert C. Martin ("Uncle Bob") in his 2000 essay *Design Principles and Design Patterns*. The acronym itself was later coined by Michael Feathers. These principles guide developers toward writing code that is **understandable, maintainable, testable, and adaptable** to changing requirements.

At their core, the SOLID principles promote **loose coupling** and **high cohesion** — classes are less dependent on one another, making the codebase more reusable, flexible, and stable.

---

## Table of Contents

1. [Single Responsibility Principle (SRP)](#1-single-responsibility-principle-srp)
2. [Open-Closed Principle (OCP)](#2-open-closed-principle-ocp)
3. [Liskov Substitution Principle (LSP)](#3-liskov-substitution-principle-lsp)
4. [Interface Segregation Principle (ISP)](#4-interface-segregation-principle-isp)
5. [Dependency Inversion Principle (DIP)](#5-dependency-inversion-principle-dip)
6. [Why SOLID Matters](#why-solid-matters)
7. [Common Anti-Patterns](#common-anti-patterns)

---

## 1. Single Responsibility Principle (SRP)

> **"A class should have one, and only one, reason to change."**

A class should be responsible for a single part of the system's functionality. When a class handles multiple concerns, a change in one concern forces the class to change for an unrelated reason — making it harder to maintain and test.

### Violation

```
class Invoice {
    calculate() { ... }   // business logic
    printToConsole() { ... }  // presentation
    saveToFile() { ... }  // persistence
}
```

`Invoice` has three distinct reasons to change: calculation rules, output format, and storage mechanism. A change in how invoices are printed should not require touching the class that calculates totals.

### Corrected Design

```
class Invoice {
    calculate() { ... }
}

class InvoicePrinter {
    print(invoice) { ... }
}

class InvoicePersistence {
    saveToFile(invoice) { ... }
}
```

Each class now has a single, well-defined job. Changes to printing do not risk breaking calculation logic.

### Benefits

- Easier to locate and fix bugs (one responsibility = one place to look).
- Reduces the chance of merge conflicts in team environments.
- Simplifies unit testing — each class can be tested in isolation.

---

## 2. Open-Closed Principle (OCP)

> **"Software entities should be open for extension, but closed for modification."**

You should be able to add new behavior to a system without editing existing, working code. New requirements are met by writing new code (subclasses, implementations), not by modifying what already works. This reduces the risk of introducing bugs in stable code.

### Violation

```
class AreaCalculator {
    totalArea(shapes[]) {
        total = 0
        for each shape in shapes {
            if (shape.type == "circle") {
                total += PI * shape.radius * shape.radius
            } else if (shape.type == "square") {
                total += shape.side * shape.side
            }
            // Adding a triangle requires editing this method
        }
        return total
    }
}
```

Every new shape type requires modifying `AreaCalculator`, risking regressions.

### Corrected Design

```
interface Shape {
    area(): float
}

class Circle implements Shape {
    area() { return PI * radius * radius }
}

class Square implements Shape {
    area() { return side * side }
}

class Triangle implements Shape {
    area() { return 0.5 * base * height }
}

class AreaCalculator {
    totalArea(shapes[]) {
        total = 0
        for each shape in shapes {
            total += shape.area()
        }
        return total
    }
}
```

Adding `Triangle` requires no changes to `AreaCalculator`. The abstraction (`Shape`) acts as the extension point.

### Benefits

- New features can be added without touching existing, tested code.
- Reduces the risk of introducing regressions.
- Encourages interface-driven and polymorphic design.

---

## 3. Liskov Substitution Principle (LSP)

> **"Derived or child classes must be able to replace their base or parent classes without altering the correctness of the program."**

Named after Barbara Liskov, who introduced the concept in 1987. A subclass should honor all the contracts (behavior, return types, preconditions, postconditions) established by its parent class. If substituting a child for a parent causes unexpected behavior, the inheritance hierarchy is broken.

### Violation

```
class Rectangle {
    setWidth(w)  { width = w }
    setHeight(h) { height = h }
    area()       { return width * height }
}

class Square extends Rectangle {
    setWidth(w)  { width = w; height = w }   // forces both dimensions equal
    setHeight(h) { width = h; height = h }   // forces both dimensions equal
}

// Caller that works fine for Rectangle:
r = new Square()
r.setWidth(5)
r.setHeight(4)
assert r.area() == 20  // fails! area is 16, not 20
```

`Square` silently breaks the behavior that callers expect from `Rectangle`.

### Corrected Design

If two types have fundamentally different invariants, they should not share an inheritance relationship. Prefer a shared abstraction:

```
interface Shape {
    area(): float
}

class Rectangle implements Shape {
    area() { return width * height }
}

class Square implements Shape {
    area() { return side * side }
}
```

### Benefits

- Enables safe and predictable polymorphism.
- Prevents subtle bugs that only surface at runtime when substituting objects.
- Reinforces trustworthy inheritance hierarchies.

---

## 4. Interface Segregation Principle (ISP)

> **"Clients should not be forced to depend on methods they do not use."**

Prefer many small, focused interfaces over one large, general-purpose interface. When an interface is too broad, implementing classes are forced to provide stubs or empty implementations for methods that are irrelevant to them — a sign of poor cohesion.

### Violation

```
interface ParkingLot {
    parkVehicle(vehicle)
    removeVehicle(vehicle)
    calculateFee(vehicle): float
    processPayment(vehicle, amount)
}

class FreeParking implements ParkingLot {
    parkVehicle(vehicle)   { ... }
    removeVehicle(vehicle) { ... }
    calculateFee(vehicle)  { return 0 }      // forced, makes no sense
    processPayment(...)    { /* not needed */ }  // forced, makes no sense
}
```

`FreeParking` is forced to implement payment methods it will never use.

### Corrected Design

```
interface ParkingOperations {
    parkVehicle(vehicle)
    removeVehicle(vehicle)
}

interface PaymentOperations {
    calculateFee(vehicle): float
    processPayment(vehicle, amount)
}

class FreeParking implements ParkingOperations {
    parkVehicle(vehicle)   { ... }
    removeVehicle(vehicle) { ... }
}

class PaidParking implements ParkingOperations, PaymentOperations {
    parkVehicle(vehicle)       { ... }
    removeVehicle(vehicle)     { ... }
    calculateFee(vehicle)      { ... }
    processPayment(vehicle, a) { ... }
}
```

Each class implements only what it needs.

### Benefits

- Reduces unnecessary coupling between unrelated concerns.
- Promotes composition over large inheritance chains.
- Makes interfaces easier to understand and implement correctly.

---

## 5. Dependency Inversion Principle (DIP)

> **"High-level modules should not depend on low-level modules. Both should depend on abstractions. Abstractions should not depend on details. Details should depend on abstractions."**

Instead of high-level business logic classes directly instantiating or referencing concrete low-level classes (like a specific database driver), both sides should depend on a shared abstraction (an interface). This "inverts" the typical top-down dependency flow, decoupling the two layers.

As Uncle Bob noted: if OCP defines the *goal* of a resilient architecture, DIP provides the *primary mechanism* for achieving it.

### Violation

```
class MySQLConnection {
    connect() { ... }
    query(sql) { ... }
}

class UserRepository {
    // Directly depends on a concrete implementation
    db = new MySQLConnection()

    findUser(id) {
        db.connect()
        return db.query("SELECT * FROM users WHERE id = " + id)
    }
}
```

Swapping `MySQLConnection` for `PostgreSQLConnection` requires editing `UserRepository`.

### Corrected Design

```
interface DatabaseConnection {
    connect()
    query(sql): result
}

class MySQLConnection implements DatabaseConnection {
    connect() { ... }
    query(sql) { ... }
}

class PostgreSQLConnection implements DatabaseConnection {
    connect() { ... }
    query(sql) { ... }
}

class UserRepository {
    // Depends on the abstraction, not the concrete class
    constructor(db: DatabaseConnection) {
        this.db = db
    }

    findUser(id) {
        this.db.connect()
        return this.db.query("SELECT * FROM users WHERE id = " + id)
    }
}
```

The database implementation can be swapped — or replaced with a test double — without touching `UserRepository`.

### Benefits

- Increases flexibility: swap implementations without modifying consumers.
- Enables dependency injection and inversion-of-control containers.
- Makes unit testing straightforward (inject mocks or fakes at the boundary).

---

## Why SOLID Matters

| Problem (without SOLID) | SOLID Solution |
|---|---|
| **Rigidity** — one change cascades through many classes | SRP keeps concerns isolated |
| **Fragility** — unrelated code breaks after a change | OCP and LSP establish stable contracts |
| **Immobility** — code cannot be reused elsewhere | DIP and ISP decouple implementations from callers |
| **Viscosity** — shortcuts feel easier than proper design | All five principles together lower the cost of doing the right thing |

Collectively, the SOLID principles produce code that is:

- **Maintainable** — clear responsibilities make changes localized and predictable.
- **Scalable** — new features are added by extension, not by mutation.
- **Testable** — loosely coupled components can be verified independently.
- **Collaborative** — well-defined boundaries reduce merge conflicts on teams.

---

## Common Anti-Patterns

- **God Class**: a single class doing everything — the clearest violation of SRP.
- **Shotgun Surgery**: a single change requires edits across many classes — usually caused by poor separation of concerns.
- **Refused Bequest**: a subclass inherits methods it doesn't need and leaves them empty or throws exceptions — a violation of LSP.
- **Fat Interface**: one interface with dozens of methods — a violation of ISP.
- **Concrete Dependency**: high-level code `new`ing low-level implementations directly — a violation of DIP.

---

## References

- Robert C. Martin, *Design Principles and Design Patterns* (2000)
- [S.O.L.I.D: The First 5 Principles of Object Oriented Design — DigitalOcean](https://www.digitalocean.com/community/conceptual-articles/s-o-l-i-d-the-first-five-principles-of-object-oriented-design)
- [SOLID Principle in Programming: Understand With Real Life Examples — GeeksforGeeks](https://www.geeksforgeeks.org/system-design/solid-principle-in-programming-understand-with-real-life-examples/)
- [SOLID Design Principles — BMC Blogs](https://www.bmc.com/blogs/solid-design-principles/)
- [SOLID Principles Explained in Plain English — freeCodeCamp](https://www.freecodecamp.org/news/solid-principles-explained-in-plain-english/)
