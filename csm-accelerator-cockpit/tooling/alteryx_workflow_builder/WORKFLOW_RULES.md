# WORKFLOW_RULES.md

All hard rules must be enforced by `verify_workflows.py`.

## Macro Path Rules

### R-MACRO-001 Relative Paths Only
Macro references must be relative paths.

### R-MACRO-002 Forbidden Macro Tokens
Forbidden tokens must not appear in macro references:
- `accounting_automation` when validating non-accounting kits.
- excessive parent escapes such as `..\\..\\..\\..\\`.

### R-MACRO-003 Approved Macro Roots
If macro path matches `Starter Kits\\<root>\\Macros`, `<root>` must equal the current starter-kit slug.

## Layout Containment Rules

### R-LAYOUT-001 Annotation Containment
Annotation text rectangles must be fully contained inside their owning section/comment box with at least 4px internal margin.

### R-LAYOUT-002 Text Containment
Comment/textbox content rectangles must be fully contained inside their own box rectangle with at least 4px internal margin.

### R-LAYOUT-003 Border Intersection Prohibited
Annotation/text rectangles must not intersect any comment/section border band. Container edges may cross connection paths when necessary, but must never obscure tool footprints, tool labels, or tool annotations.

### R-LAYOUT-004 Central Composition
Major workflow sections should be composed around a readable central trunk when the use case is primarily linear with right-side analysis branches. Avoid pushing all downstream containers excessively downward or to one edge when a more centered composition preserves readability.

### R-LAYOUT-005 Internal Reflow Required
Beautification is incomplete if only outer containers move. When a section is being refactored for readability, the tools inside that section must also be re-laid out so the internal left-to-right story becomes clearer.

### R-LAYOUT-006 Compact Vertical Separation
Adjacent containers should have tight but readable spacing. Prefer small, intentional gaps over large dead zones once labels, tool annotations, and connector curvature have been accounted for.

### R-LAYOUT-007 Symmetry With Purpose
Use symmetry to reinforce comprehension, not decoration. Repeated analytical patterns should share consistent geometry, but symmetry must not override the true logical flow of the workflow.

### R-LAYOUT-008 Tool Visibility
No tool may be visually hidden by any container, ever. This applies to all tools, not only terminal or consolidation tools.

### R-LAYOUT-009 Container Non-Overlap
Containers at the same visual hierarchy must not overlap one another. Stacked sections require explicit clearance for container headers, tool labels, annotations, and connector curvature.

### R-LAYOUT-010 Equal Inter-Container Gaps
When peer containers are arranged in a row or column, the empty space between whole container rectangles should be consistent unless a deliberate narrative reason requires otherwise. Container size may vary, but the gaps between them should read as even.

### R-LAYOUT-011 Cross-Hierarchy Occlusion Prohibited
No container may visually obscure another container's header, body, or internal tools even when the two containers belong to different local groupings. If two sections compete for the same canvas space, reposition them rather than allowing one to sit behind the other.

### R-LAYOUT-012 Overview Note Compaction
Global orientation notes should sit just above the section they introduce, not far above the real working area. Avoid letting a high-level note create large dead space or force a master container to be much taller than the actual content requires.

## Annotation Rules

### R-ANN-001 Border Safety
Annotation labels must not cross comment/section borders.

### R-ANN-002 Readability
Annotation placement must remain readable and non-overlapping with box borders.

### R-ANN-003 Annotation Budget
Use the minimum number of text boxes needed to explain the workflow. Prefer a few strong orientation notes over many editorial comments that compete with the tool flow.

### R-ANN-004 Native Feel
Annotated workflows should still feel like native Alteryx canvases, not posters. Documentation must support the workflow structure rather than visually dominate it.

### R-ANN-005 Prefer Native Tool Annotations
For central or decision-critical tools, prefer native Alteryx tool annotations before adding separate comment boxes. Inline explanation should clarify the logic at the point where the reader encounters it.

### R-ANN-006 Comment Proximity And Gap
When separate comment boxes are used, place them as close as possible to the tools or lane they explain without obstructing tools, labels, annotations, or connectors. Within a container, explanatory comment boxes should sit immediately above or beside the tools they describe with only a small readable gap. Avoid large detached comment boxes and large empty vertical space between a comment and its target tool chain.

### R-ANN-007 Top Note Clearance
When a container begins with an orientation note or explanatory textbox, preserve a clear vertical buffer between the bottom of that note and the first tool footprint below it. The note must never overlap the icon, label, or annotation area of the first tool row.

## Workflow Composition Rules

### R-COMP-001 Preserve Primary Narrative
The primary canvas story should remain easy to read as inputs -> preparation -> branching analysis -> outputs. Refactors must improve that narrative, not obscure it.

### R-COMP-001A Presentation Contract
Beautified or newly created workflows should present a clear visual narrative, not just a chain of tools. When the workflow is intended to be readable by humans on the canvas, include the appropriate combination of:
- a clear top title
- a short description or subtitle
- named sections or acts
- native tool annotations for key logic steps
- explanatory comment boxes where truly helpful
- containers that frame the logical groups

### R-COMP-001B Beautification Is First-Class
Beautification rules are first-class workflow requirements, not optional polish. When creating or editing workflows, apply the same rigor to visual structure, readability, and presentation as to XML correctness and logical construction.

### R-COMP-001C Title-First Header Hierarchy
When a beautified workflow uses top-of-canvas explanatory text boxes, the primary workflow title must sit at the highest header position. Secondary scope, assumption, or read-order notes must sit below the title rather than beside it.

### R-COMP-001D Styled Header Notes
Top-of-canvas explanatory text boxes must use visible, intentional fill colors and readable text contrast. Avoid header comments that read like bare unstyled text on the canvas background.

### R-COMP-002 Prep Lane Discipline
When multiple input branches repeat the same preparation pattern, align them into consistent rows or columns with shared anchor points for input, select, formula, join, and downstream transforms.

### R-COMP-003 Repeated Pattern Consistency
If multiple lanes or analytical sections implement comparable logic, they should use similar internal motifs so a reader can learn one pattern and recognize the others quickly. Apply this within reason; do not create unnecessary container bloat.

### R-COMP-004 Interface Placement
Runtime interface controls should live near the logic they drive and should feel intentionally placed, not floating or detached from the workflow.

### R-COMP-005 Output Anchoring
Rendered outputs, report tables, and final consolidations should be visually anchored at predictable right-side endpoints so the reader can quickly identify where each branch finishes.

### R-COMP-006 Balance Over Decoration
Empty space should be purposeful. Prefer balanced visual weight across left, center, and right zones instead of creating large empty areas simply to achieve separation.

### R-COMP-007 Flow Beats Ornament
When symmetry, decoration, or annotation density conflicts with scanability, prioritize the simpler layout that makes the workflow easier to follow.

### R-COMP-008 Per-Section Grouping
When a workflow uses multiple large outer containers, each outer container should organize its own free-roaming inputs, prep lanes, and utility tools locally. Do not force a cross-container inner grouping scheme that cuts across separate outer sections.

### R-COMP-009 Container Framing Discipline
Use containers only when they make the workflow easier to understand. Repeated lanes should be grouped when that grouping clarifies structure, but avoid creating containers purely for the sake of boxing everything. Logical groups should use explicit, human-readable titles, and containers should use a consistent semantic color system based on the dominant logic or tool family inside them. When a tool or lane is important enough to explain on the canvas, prefer placing it inside a clearly titled and semantically colored container rather than leaving it free-roaming without context.

### R-COMP-009A All Tools Must Belong To A Contextual Container
Every actual Alteryx tool must belong to at least one clearly titled Tool Container that gives contextual meaning to the group it participates in. Free-roaming tools are not allowed in beautified workflows. Text boxes, comment boxes, and Tool Container nodes themselves are not considered "tools" for this rule and do not need to be enclosed by another container.

### R-COMP-010 Hub Centering
When one tool or a short tool chain fans out to multiple downstream branches, or when multiple branches converge into a single tool such as a Union, center the hub relative to the full target/input set so the expansion or merge reads as balanced and intentional. When evaluating fan-in, include all meaningful incoming branches, including title/report-text inputs or other auxiliary contributors, even if one contributor remains outside a local container for readability.

### R-COMP-013 Intermediary Tool Placement
If a tool logically sits between two upstream/downstream lanes, it should be positioned geometrically between them as well. Filters, joins, and other bridging tools should not be offset arbitrarily when their role is to mediate adjacent lanes.

### R-COMP-014 Straight-Through Chains
When tools are part of a simple sequential chain, they should be laid out in a straight horizontal or vertical line unless a branch or containment constraint requires otherwise. Do not introduce unnecessary bends in a linear path.

### R-COMP-015 Container Must Fit Internals
Each container must fully contain its internal tools, annotations, labels, and comment boxes with visible clearance. If internal content approaches or exceeds the container boundary, resize or reposition the container instead of allowing overlap with neighboring sections.

### R-COMP-015A Final-Output Reuse For Reporting
When a workflow produces polished final tables for Browse or delivery, any downstream PDF/report branch should reuse those cleaned final-table outputs whenever practical instead of rebuilding an alternate table shape upstream. The report should reflect the same final presentation logic the canvas already established.

### R-COMP-015B Oversized Detail Appendices May Be Browse-Only
If a long detail table or appendix would force report-tool truncation because a single report section cannot fit on a page, keep that detail output available in Browse or a separate export and exclude it from the main PDF. Prioritize a clean, error-free report for the numbered summary tables over squeezing an oversized appendix into one report snippet.

### R-COMP-016 Symmetric Fork-And-Rejoin
When one lane splits into two or more parallel branches and later reconverges, the branch lanes should be arranged symmetrically around a clear centerline whenever the logic is equivalent. The split origin, branch lanes, and merge target should visually reflect that symmetry so the fork/rejoin pattern is easy to read.

### R-COMP-017 Forward Fork Progression
When a tool branches into parallel downstream lanes, each downstream branch must progress forward on the x-axis relative to the parent. Vertical branching is allowed, but child branches must not begin at the same horizontal start point as the parent or appear to move backward unless a hard layout constraint makes that unavoidable.

### R-COMP-018 Forward Rejoin Progression
When parallel branches reconverge, the receiving tool must sit to the right of the branch tools feeding it. The visual story of split -> branch -> merge should always progress left to right.

### R-COMP-019 Parent-Child X Separation
Downstream child tools should maintain a clear horizontal offset from their parent so the relationship reads as progression rather than overlap, hesitation, or backward motion.

### R-COMP-021 Branch Hub Centering
When a single upstream hub feeds a vertically stacked set of peer sections, the hub should be vertically centered on the middle of that stack whenever possible so the downstream spread reads as balanced.

### R-COMP-022 Paired Hub Alignment
When an upstream branch hub and a downstream merge hub serve the same repeated stack of peer sections, they should share the same visual centerline whenever practical. The split before the stack and the merge after the stack should read as a balanced pair.

### R-COMP-023 Standalone Peer Lane Treatment
When one contributor sits outside a repeated set of peer containers but feeds the same downstream merge, treat it like a real peer lane. Its vertical placement should respect the same fan-in symmetry as the contained contributors, align it to the same x rhythm as the other contributors, and, when helpful, give it its own titled and semantically colored container so it reads as part of the same family.

### R-COMP-024 Multi-Input Hub Midpoint
When many peer inputs feed a single combining tool, place the combining tool on the vertical midpoint of the full input set rather than leaving it biased toward the top or bottom. For an even number of inputs, center the hub between the two middle contributors.

### R-COMP-025 Hub-to-Lane Straightness
When a branch hub or merge hub is visually associated with a repeated stack of peer containers, align that hub to the actual tool row of the governing middle lane whenever practical. Prefer the y-position that produces the straightest readable approach into and out of the middle section, not merely the mathematical center of the container rectangles.

### R-COMP-026 Section Rebalance And Symmetry Preservation
If correcting the position of one important hub or connector-anchor creates a new visual imbalance inside its source section, rebalance the surrounding lane or container instead of leaving the corrected tool isolated. Prefer moving the governing section with its local pattern intact over solving one axis while breaking another. When a central hub is repositioned to improve downstream symmetry, re-check the upstream fan-in and its local section symmetry as well. A layout correction is incomplete if it improves one side of the hub but degrades the other side.

## Connector Rules

### R-CONN-001 No Connector Crossings
Two connection paths should not cross one another. Treat spiderweb reduction as a first-class beautification goal: refactor tool placement, section spacing, hub alignment, source ordering, or branch geometry until the reader can trace the workflow with minimal visual untangling. If a crossing can be removed through layout changes without damaging the narrative, it should be removed.

### R-CONN-002 Forward Visual Flow
Connection routing must reinforce a forward-reading canvas. Major flow should visually progress to the right, and downstream consolidation/output tools should not appear behind or upstream of the tools feeding them.

### R-CONN-003 Clean Branch Separation
Branching paths should separate cleanly enough that a reader can trace each branch without ambiguity, line stacking, crossing-heavy fan-outs, or overlapping connector paths. Prefer layouts where each branch owns visible space instead of competing for the same routing corridor.

### R-CONN-004 Peer Row Alignment
When a repeated set of peer tools feeds a repeated downstream set of peer tools, align the peer rows on matching y-coordinates whenever practical so the connecting paths stay horizontal and visually straight.

## Refactor Guidance

### R-REF-001 Critique Existing Structure
Do not assume the existing grouping is optimal. During beautification, challenge whether containers, interface blocks, prep lanes, and outputs are placed where a first-time reader would expect them.

### R-REF-002 Preserve Logic, Change Geometry
When beautifying a workflow, changing geometry aggressively is allowed as long as tool configuration, connectivity, and runtime behavior remain unchanged.

### R-REF-003 Refactor Toward Readability
If the original workflow is more readable than the beautified version, prefer the original compositional logic. A refactor must earn its complexity by being clearly easier to scan.

## Text Hygiene Rules

### R-TEXT-001 Line-Break Hygiene
Visible text must not contain:
- orphan single-word body lines
- lines ending with: `or`, `and`, `the`, `a`, `an`
- consecutive blank lines

### R-TEXT-002 Forbidden Text
Visible text must not contain:
- token `obj`
- non-printable/replacement characters

## Naming Conventions

### R-NAME-001 Workflow Filename Standard
Workflow filenames must match `^\d{2}_[^\s]+.*\.yxmd$` (no spaces).

### R-NAME-002 Output Naming
For starter-kit and AI-ready feed workflows, output filenames must be deterministic and match one of:
- `customgpt_master_feed.csv`
- `customgpt_feed.csv`
- `NN_*` pattern for stage outputs.

## Configuration Invariants

### R-CONFIG-001 Workflow Version
`yxmdVer` must be `2025.1` unless explicitly waived.

### R-CONFIG-002 Structural Integrity
- Tool IDs must be unique.
- Every connection endpoint must reference an existing Tool ID.
- TOC-family (`01_*`) structures must remain aligned to the golden TOC signature.

## Allowed Changes

- Localized text updates.
- Relative input/output path parameterization.
- Deterministic output file naming updates.
- Minimal coordinate/size changes to satisfy containment.

## Forbidden Changes

- Absolute macro/data paths.
- Cross-kit macro root rewrites.
- Silent validator bypass.
- Unapproved tool insertion/removal/reordering in golden-governed families.

## Assumptions

- Starter-kit slug inference is path-based.
- Layout checks use conservative text-rectangle estimation and prefer false positives.
- Golden structural signature is strictly enforced for `01_*` TOC workflows.
