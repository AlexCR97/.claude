# Domain-Driven Design

## What is Domain-Driven Design?

Domain-Driven Design (DDD) is a collection of principles and patterns introduced by Eric Evans in his 2003 book *Domain-Driven Design: Tackling Complexity in the Heart of Software*. It centers development on a **domain model** that has a rich understanding of the processes and rules of a domain, closing the gap between business reality and code.

The core idea is that **our focus should not be primarily on technology — it should be primarily on the business**. DDD is particularly suited to complex domains where a lot of often-messy logic needs to be organized.

> "The software you create is not the true model. It is only a manifestation of the application Form you set out to achieve." — David Laribee

---

## Strategic Design

Strategic patterns operate at the highest level of organization — how you divide, organize, and relate large parts of a system.

### Ubiquitous Language

A shared vocabulary used consistently by **all stakeholders** — developers, domain experts, and business teams. The same terminology should appear in conversations and in the code.

- If the domain expert says "underwriting" or "rate set," those words should be class names in the code.
- Ubiquitous Language is scoped to a Bounded Context — the same word can mean different things in different contexts.
- It evolves through implementation, not just documentation.

### Bounded Context

A specific area of the domain where a particular model and language are consistently applied. It establishes clear boundaries for terms that may have different meanings across system parts.

- Each Bounded Context owns its own Ubiquitous Language.
- A "Policy" in the auditing context is a different thing from a "Policy" in the core workflow context — they should be different models.
- Breaking large domains into Bounded Contexts prevents the **Big Ball of Mud** anti-pattern: an amorphous, tightly coupled system where everything has an association to everything else.

### Context Map

A diagram or document that defines the relationships between Bounded Contexts, identifying overlaps and communication agreements between them.

Common context mapping patterns include:
- **Partnership**: Two contexts collaborate closely, evolving together.
- **Shared Kernel**: A common subset of the domain model that two contexts share.
- **Customer-Supplier**: One context depends on another and negotiates its needs.
- **Anti-Corruption Layer**: A translation layer that protects the core domain from external or legacy models.

### Anti-Corruption Layer (ACL)

A translation layer that protects the core domain model from incompatible external systems or legacy code. It transforms data flowing in and out, keeping the domain model pure.

- Repositories are a type of ACL — they keep SQL and ORM constructs outside the domain.
- ACLs are a great technique for introducing seams when refactoring legacy code.

### Core Domain

The Bounded Context that delivers the most business value. This is where custom software lives, where the client has a competitive edge, and where DDD investment pays off the most. Senior effort should be concentrated here.

---

## Tactical Design

Tactical patterns operate at the class level — how you model the objects and behaviors within a single Bounded Context.

### Entity

A domain object with **distinct identity and a lifecycle**. Think of entities as units of behavior, not units of data.

- Identified by a unique ID, not by its attribute values.
- Has mutable state; its properties may change over time.
- Should encapsulate its own behavior — avoid external validation services that manipulate the entity from the outside (anemic domain model).
- When an entity needs an external service to perform its behavior, prefer injecting the dependency directly into the command method:

```csharp
public class Policy
{
    public void Renew(IAuditNotifier notifier)
    {
        // internal state changes...
        notifier.ScheduleAuditFor(this);
    }
}
```

### Value Object

A domain object that **describes** or **measures** something in the domain. It has no identity of its own.

- Compared by attribute equality, not by reference.
- **Immutable**: once created, it cannot change. Operations return new instances.
- Describes entity properties in an intention-revealing way (e.g., `Money` is more expressive than `decimal`).

```csharp
public sealed record Money(decimal Amount, Currency Currency)
{
    public Money Add(Money other)
    {
        // returns a new Money — does not mutate this one
        return new Money(Amount + other.Amount, Currency);
    }
}
```

### Aggregate

A **cluster of domain objects** (entities and value objects) treated as a single unit for the purpose of data consistency.

- One entity within the cluster is designated the **Aggregate Root**.
- External code may only hold references to the Aggregate Root — never to internal entities directly.
- The Aggregate Root guards its sub-entities and enforces all invariants.
- This constraint prevents over-coupling: it stops the system from creating a web of references between everything.

### Aggregate Root

The single entity in an Aggregate that external consumers reference directly.

- All operations on child entities must go through the Aggregate Root.
- Avoid "deep dotting" (Law of Demeter violations): prefer `policy.Renew()` over `policy.CurrentPeriod().Renew()`.
- Aggregate roots often act as state machines: commands are invoked on them and they manage their own internal state.

```csharp
// Bad: exposes internals, creates coupling to Period
policy.CurrentPeriod().Renew();

// Good: aggregate root encapsulates the decision
policy.Renew();
```

### Repository

Provides an **in-memory collection abstraction** for storing and retrieving Aggregate Roots. There is conventionally one repository per Aggregate Root.

- Keeps SQL, ORM constructs, and persistence concerns out of the domain model.
- Is a form of Anti-Corruption Layer.
- Represents infrastructure, not domain logic.

```csharp
public interface IRepository<T> where T : IEntity
{
    Task<T?> FindAsync(int id, CancellationToken cancellationToken = default);
    Task SaveAsync(T entity, CancellationToken cancellationToken = default);
    Task DeleteAsync(T entity, CancellationToken cancellationToken = default);
}
```

### Factory

Encapsulates complex object creation logic. Used when constructing an Aggregate or Entity requires non-trivial steps that would be inappropriate in a constructor.

- Keeps constructors simple (they should only assign, not execute logic).
- Use a static factory method on the class itself for common cases.

### Domain Service

Represents **behavior or an operation** that does not naturally belong to any single entity or value object.

- Typically stateless and highly cohesive.
- Named after verbs or business activities from the Ubiquitous Language (e.g., `PolicyRenewalProcessor`).
- Use when: multiple dependencies are involved, or when the Ubiquitous Language describes a process as a first-order concept.

```csharp
public sealed class PolicyRenewalProcessor
{
    private readonly IAuditNotifier _notifier;

    public PolicyRenewalProcessor(IAuditNotifier notifier)
    {
        _notifier = notifier;
    }

    public void Renew(Policy policy)
    {
        policy.Renew();
        _notifier.ScheduleAuditFor(policy);
    }
}
```

### Application Service

Orchestrates domain objects to fulfill use cases. Lives outside the domain model itself.

- Maps data between the domain model and the shapes required by clients (DTOs, view models).
- Integrates multiple Bounded Contexts.
- Brings infrastructure dependencies (logging, WCF, messaging) into the mix without polluting the domain model.
- Should be broad and shallow — thin coordinators, not business logic holders.

### Domain Events

Represent **significant occurrences** within the domain that other parts of the system may react to.

- Capture important state changes and business activities.
- Named in past tense to reflect that something happened (e.g., `PolicyRenewedEvent`).
- Should carry a unique identifier named after the domain model (e.g., `PolicyId`, not just `Id`).

```csharp
public record PolicyRenewedEvent(Guid PolicyId, DateTime RenewedAt);
```

### Modules

A way to organize groups of related classes within a Bounded Context. In .NET, modules map to namespaces.

- Use modules to surface mini-models within a model.
- If a module feels too distinct, question whether it is a separate Bounded Context.

---

## Key Principles

| Principle | Description |
|---|---|
| **Model-driven design** | Domain understanding is expressed directly in code, not in separate documentation. |
| **Ubiquitous Language** | Developers and domain experts speak the same vocabulary; it appears in the code. |
| **Encapsulate behavior** | Entities should own and manage their own state — avoid anemic models. |
| **Protect invariants** | Aggregate Roots enforce consistency boundaries for their sub-entities. |
| **Separate concerns** | Persistence, infrastructure, and UI logic are kept outside the domain model. |
| **Core domain focus** | Invest DDD effort where the business has its competitive edge. |

---

## Common Anti-Patterns

- **Anemic Domain Model**: entities with only properties and no behavior; business logic lives in external service/manager classes.
- **Big Ball of Mud**: no Bounded Contexts; everything references everything; changes cascade unpredictably.
- **Deep dotting**: violates the Law of Demeter; exposes internal aggregate structure to consumers.
- **Database-first modeling**: the database schema drives the object model; behavior is an afterthought.

---

## References

- *Domain-Driven Design: Tackling Complexity in the Heart of Software* — Eric Evans (2003)
- *Implementing Domain-Driven Design* — Vaughn Vernon (2013)
- [An Introduction to Domain-Driven Design — David Laribee, MSDN Magazine 2009](https://learn.microsoft.com/en-us/archive/msdn-magazine/2009/february/best-practice-an-introduction-to-domain-driven-design)
- [Domain Driven Design — Martin Fowler](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [Domain-Driven Design (DDD) — GeeksforGeeks](https://www.geeksforgeeks.org/system-design/domain-driven-design-ddd/)
- [The Big Ball of Mud — Foote & Yoder (1999)](https://laputan.org/mud)
