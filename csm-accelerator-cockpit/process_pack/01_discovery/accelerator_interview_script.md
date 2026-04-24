# Customer Accelerator Interview Script

This interview script is designed to help a consultant run a structured discovery conversation that feeds directly into the accelerator SOP.

Primary outputs of the conversation:
- a clear business problem statement
- a first-pass workflow objective
- candidate source systems and entities
- known versus unknown data facts
- a realistic first-slice scope
- enough material to draft the SOP quickly

Recommended use:
- use this in a live customer conversation
- capture short answers, not polished prose
- separate confirmed facts from assumptions
- flag anything that needs source discovery rather than guessing

## 1. Opening

Suggested opening:

"The goal today is to understand the business problem, the current process, the decisions you want to improve, and where the data probably lives. We are not trying to design the final production solution in one meeting. We are trying to get to a strong first implementation slice quickly."

## 2. Business Problem

Questions:
- What problem are you trying to solve?
- What is frustrating, slow, manual, or unreliable today?
- What happens if this problem is not solved?
- Who feels the pain most directly?
- What decision or action would you like to improve first?

Capture:
- business problem
- operational pain
- impacted roles
- urgency

Maps to SOP:
- `1.1 Business Problem`
- `2.1 Pain Points`

## 3. Current Process

Questions:
- How is this done today, step by step?
- What tools are used today?
- Where do spreadsheets, emails, manual reconciliations, or handoffs happen?
- Which part takes the most time?
- Which part causes the most errors or rework?
- What outputs do people rely on today?

Capture:
- current workflow
- manual steps
- current outputs
- failure points

Maps to SOP:
- `2.2 Current Process`

## 4. Desired Outcome

Questions:
- If we got this working quickly, what would the customer actually receive?
- What would be most useful in the first version: a report, a dashboard feed, an exception queue, a scored dataset, an alert list?
- What would make you say this accelerator has been successful?
- What is the minimum useful output in week 1 or phase 1?

Capture:
- target outputs
- success criteria
- first-slice definition

Maps to SOP:
- `1.2 Desired Outcome`
- `1.3 Accelerator Objective`
- `4.3 Proposed Outputs`

## 5. Business Questions To Answer

Questions:
- What are the top business questions you want the workflow to answer?
- What do you need to see regularly?
- What exceptions, risks, trends, or opportunities matter most?
- Which numbers or signals drive action?
- If we gave you one table tomorrow, what columns would you expect to see?

Capture:
- business questions
- likely KPI outputs
- likely dimensions and measures

Maps to SOP:
- `2.3 Business Questions To Answer`
- `7.1 Core Rules`

## 6. Scope And Priorities

Questions:
- What is definitely in scope for the accelerator?
- What is important but can wait until later?
- Are there business units, geographies, products, or process stages we should exclude for the first slice?
- Is there a preferred pilot area?
- Are we trying to prove technical feasibility, business value, or both?

Capture:
- in-scope items
- out-of-scope items
- pilot boundary

Maps to SOP:
- `3.1 In Scope`
- `3.2 Out Of Scope`

## 7. Source Systems

Questions:
- Where does the data probably live today?
- Which systems, files, teams, or owners are involved?
- Are there warehouses, ERPs, CRMs, spreadsheets, APIs, or shared folders involved?
- Which source feels most important for the first slice?
- Which source is easiest to access quickly?

Capture:
- source system candidates
- source owners
- likely access paths

Maps to SOP:
- `5.1 Expected Source Systems`

## 8. Data Shape And Entities

Questions:
- What are the core business entities involved?
- What are the likely keys?
- What statuses matter?
- What dates matter?
- What measures matter?
- What dimensions matter?
- Are there known joins across the sources?
- Are there known reference tables or master data sources?

Prompts if needed:
- order, customer, product, store, project, invoice, asset, employee, shipment
- created date, due date, delivered date, posting date, effective date
- amount, quantity, cost, revenue, hours, stock, probability

Capture:
- likely grain
- likely keys
- likely join paths
- likely facts and dimensions

Maps to SOP:
- `4.2 Proposed Analytical Grain`
- `5.2 Known Versus Unknown`
- `6. Data Contract`

## 9. Known Unknowns

Questions:
- What do we not know yet about the data?
- Which fields or tables are assumed rather than confirmed?
- Where do you expect data quality problems?
- Are there naming inconsistencies, duplicates, nulls, or missing timestamps?
- Are there cases where business users trust one source more than another?
- What do we need to inspect before we can confidently build?

Capture:
- confirmed facts
- assumptions
- unknowns
- source-discovery tasks

Maps to SOP:
- `5.2 Known Versus Unknown`
- `5.3 Discovery Actions`
- `11. Gaps, Risks, And Open Questions`

## 10. Business Rules

Questions:
- What records should be included?
- What records should be excluded?
- What statuses are considered active, valid, complete, late, risky, or irrelevant?
- What formulas or thresholds are used today?
- Are there exception rules, override rules, or policy rules?
- Are there specific calculations the business already trusts?

Capture:
- filters
- status logic
- KPI definitions
- thresholds
- edge cases

Maps to SOP:
- `7.1 Core Rules`
- `7.3 Edge Cases`

## 11. Output And Action Design

Questions:
- Once the workflow produces an output, who uses it?
- What action should someone take from it?
- What format is easiest for that team to use?
- Does the customer need a review pack, exception queue, dashboard feed, or alert list first?
- Do they need one combined output or multiple outputs for different audiences?

Capture:
- consumer groups
- output formats
- action pathways

Maps to SOP:
- `4.3 Proposed Outputs`
- `8.5 Stage 5: Output`
- `9. Automation And Operationalisation`

## 12. Validation And Trust

Questions:
- How would the customer decide that the first slice is credible?
- What would they want us to reconcile against?
- Are there existing reports or totals we can compare to?
- What row counts, balances, or spot checks would make them trust the output?
- What would count as a failed result?

Capture:
- validation expectations
- baseline reports
- reconciliation targets

Maps to SOP:
- `10. Testing And Validation Plan`

## 13. Operational Constraints

Questions:
- Are there access or security constraints?
- Are there time constraints on the accelerator?
- Are there platform constraints such as on-prem only, cloud only, or desktop-only?
- Are there governance requirements that matter now versus later?
- Is scheduling required in the first slice or can it stay manual?

Capture:
- delivery constraints
- access constraints
- operational assumptions

Maps to SOP:
- `9. Automation And Operationalisation`
- `11. Gaps, Risks, And Open Questions`

## 14. Close

Suggested closing:

"Weâ€™ll turn this conversation into a structured SOP, confirm what is known versus what still needs data discovery, and then use that to build the first runnable slice. Weâ€™ll also make the gaps explicit so you can see what is already buildable and what still needs clarification."

## 15. Consultant Notes Template

Use this lightweight structure during the meeting:

- Business problem:
- Current process:
- Desired outcome:
- Top business questions:
- In scope:
- Out of scope:
- Candidate sources:
- Likely entities:
- Likely keys:
- Likely dates:
- Likely measures:
- Known business rules:
- Known unknowns:
- Validation expectations:
- Constraints:
- First-slice recommendation:

## 16. Interviewing Principles

- Do not ask the customer to design the workflow.
- Ask about decisions, actions, pain, and trust first.
- Separate confirmed facts from assumptions.
- If source structure is unknown, say "we will verify that in discovery" rather than forcing certainty.
- Prefer concrete examples over abstract labels.
- Keep the first slice narrow enough to build quickly.
- End with a crisp statement of what can be built now versus what depends on source discovery.

## 17. Future Extension Note

This script is intentionally human-led.

In future, a live transcript workflow could speed up note capture and SOP drafting, but the structure should remain the same:
- consultant conversation
- structured capture
- SOP draft
- source discovery
- build and validation
