# Spiderweb Reduction

## Principle

Connector topology is part of beautification. Do not accept "technically fine" routing when a cleaner lane layout is available.

## What Causes Spiderweb

- Too many unrelated lanes sharing one corridor
- A hub positioned off-center relative to its contributors
- Fan-in and fan-out happening in the same crowded area
- Over-optimizing for minimum tool count
- Branches that begin without owning their own horizontal or vertical space

## Core Remedies

### 1. Separate lanes before you simplify

- Give each major branch or feed family its own lane.
- Keep velocity/prep lanes away from dimension-enrichment lanes when possible.
- Avoid routing unrelated connectors through the same whitespace just because it is available.

### 2. Reorder peer inputs

- Reorder sibling sources so their visual order matches the hub they feed.
- The best source order is the one that minimizes crossings, not the one that matches the folder listing.

### 3. Center hubs intentionally

- A merge or branch hub should be centered on the contributors it visually governs.
- If a hub is biased too high or too low, the reader pays for it with extra connector untangling.

### 4. Stage merges when one mega-hub gets ugly

- A single `Join Multiple` or mega-merge is only good when it actually improves the picture.
- If one hub creates a dense fan-in knot, back off to staged joins.
- It is acceptable to trade a few extra tools for a much clearer canvas.

### 5. Isolate unavoidable fan-in

- Some tools, like `Join Multiple`, may require visible connection identifiers or concentrated fan-in.
- When that happens, isolate that hub in clear whitespace and keep other lanes away from it.
- Do not let one unavoidable knot attract additional avoidable clutter.

### 6. Clean up fan-out too

- Spiderweb is not only about inputs.
- Sort/output branches can also tangle if they split too early or too close to one another.
- Space the branch origin and output targets so each branch reads as owned space.

## Decision Rule

If a crossing or knot can be removed by moving tools, reordering siblings, separating lanes, or staging the merge differently, remove it.
