# Diagram-design skill: quickstart prompt

A ready-to-paste prompt for generating architecture diagrams of this codebase
with the `diagram-design` Claude Code plugin
([cathrynlavery/diagram-design](https://github.com/cathrynlavery/diagram-design)).

## How to use

1. Install the plugin once. Run this in a terminal:

   ```
   claude plugin marketplace add cathrynlavery/diagram-design
   claude plugin install diagram-design@diagram-design
   ```

   Or type the same commands inside a Claude Code session:

   ```
   /plugin marketplace add cathrynlavery/diagram-design
   /plugin install diagram-design@diagram-design
   ```

2. Start a new Claude Code session in the root of this repo, so the skill is
   loaded.
3. Paste the prompt below.

## Prompt

```
Use the diagram-design skill to generate three architecture diagrams for this
repo:

1. An architecture diagram — the high-level system: major components/services
   and how they connect.
2. A deployment diagram — where each component actually runs (hosted vs.
   local, separate services/processes, dependency boundaries).
3. A sequence diagram — one representative end-to-end request/flow through
   the system, showing which component is responsible for what at each step.

Look at the actual code/structure of this repo first so the diagrams reflect
what's really here, not a generic template.
```

## Notes

- The plugin is installed for your whole Claude Code account
  (`~/.claude/settings.json`), not just this repo.
- If the skill doesn't trigger, restart the Claude Code session or say
  "use the diagram-design skill" explicitly.
