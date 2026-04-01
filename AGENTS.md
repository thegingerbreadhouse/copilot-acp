# AGENTS.md

## Purpose

This repository should stay easy to navigate for humans first. Any agent working here should favor clear structure, explicit boundaries, and maintainable object-oriented design over clever shortcuts.

## Repository organization

- Keep the folder structure intuitive and shallow where possible.
- Group code by responsibility, not by convenience.
- Prefer predictable locations such as:
  - `src/<package>/client/` for transport or protocol clients
  - `src/<package>/models/` for domain models and typed state
  - `src/<package>/services/` for orchestration and business logic
  - `src/<package>/adapters/` for external integrations
  - `src/<package>/examples/` for runnable examples
  - `tests/` mirroring the source layout
- Avoid dumping unrelated classes into a single module.
- When a module grows beyond a clear single responsibility, split it into a subpackage.
- File and class names should communicate intent without needing extra explanation.

## Readability rules

- Optimize for human readability over minimal file count.
- Keep modules cohesive and focused.
- Prefer explicit names over abbreviations unless the term is standard in the protocol or dependency.
- Make control flow easy to follow.
- Add brief comments only where the design intent is not obvious from the code itself.

## OOP guidance

- Follow strong OOP fundamentals: single responsibility, encapsulation, composition over inheritance, and explicit interfaces.
- Prefer small collaborating classes over large procedural utility modules.
- Use design patterns when they simplify the design in a real way, not as decoration.
- Common acceptable patterns here include:
  - Singleton for process-wide coordination where a true single shared instance is required
  - Factory or Abstract Factory for constructing protocol clients, sessions, or transport implementations
  - Strategy for pluggable behaviors such as permission handling, event routing, or response processing
  - Adapter for wrapping third-party ACP or Copilot APIs behind stable internal interfaces
  - Builder for assembling complex request or session configuration objects
- If a pattern is used, keep the implementation obvious and justified by the problem.

## Implementation expectations

- New features should preserve a clean public API and hide internal complexity behind well-named classes.
- Avoid tight coupling between protocol transport, business logic, and CLI concerns.
- Prefer typed models and explicit contracts at subsystem boundaries.
- Design for future multi-agent coordination rather than one-off scripting.
- Refactor opportunistically when adding code would otherwise worsen structure.

## Version control

- Commit often and atomically.
- Create checkpoints at coherent implementation moments so history stays easy to follow and rollback stays safe.
- Keep each commit scoped to one logical change whenever practical.

## Agent behavior

- Before adding files, consider whether the current package layout still makes sense.
- If you introduce a new subsystem, place it in a dedicated folder with a coherent boundary.
- If the existing structure becomes awkward, reorganize it deliberately instead of layering more exceptions on top.
- Treat this file as an active implementation constraint for all future agents working in this repository.
