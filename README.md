# Budget Q&A agent in Microsoft Copilot Studio

A Copilot Studio agent that answers a finance manager's questions about budget data, such as "What was the Marketing travel budget?" or "What was the total budget from April to September 2026?". It is a rebuild of my Python agent [variance-qa-agent](https://github.com/vicmeng188/variance-qa-agent) on the Microsoft Power Platform. I built it to learn Copilot Studio and to see where a low-code platform fits in finance work.

**Main rule carried over from the Python version: the model never calculates. Every figure is calculated by Power Fx and sent to the user word for word.**

## How it works

```
User question
   │
   ▼
Copilot Studio agent (generative orchestration)
   │  The model reads the topic description, chooses the "Budget Query" topic
   │  and extracts department, category, month_from and month_to from the question
   ▼
Topic: Budget Query
   1. Calls an agent flow that reads the Excel table from OneDrive
      (flow returns all rows as JSON text, because agent flows cannot return tables)
   2. Parse value turns the JSON text back into a table
   3. Guardrails (Power Fx conditions) check the inputs against the data itself
   4. Power Fx filters and sums the rows
   5. A Message node sends the result. The model does not rewrite it
```

**Agent flow:** When an agent calls the flow → Excel Online (Business) "List rows present in a table" → Select (keeps 5 columns, converts Budget and Actual from text to numbers, shortens dates to YYYY-MM) → Respond to the agent.

**Data:** six monthly CSV files (Jan to Jun 2026, 72 rows) combined with Power Query into one Excel table. The data contains planted problems (two duplicate rows, two missing rows), which were kept on purpose.

## Guardrails

| Situation | What the agent does |
|---|---|
| Department does not exist (e.g. Finance) | Says so and lists the departments that exist |
| Category not found in that department (e.g. Sales / Rent) | Says so and lists that department's categories |
| No data at all for the period (e.g. January 2025) | Says so and lists the months that have data |
| Only part of the period has data (e.g. April to September) | Gives the figure for the months that have data and says which months are covered |
| No department, category or month given | Uses all of them. It does not ask a follow-up question |
| Question needs a figure the topic cannot return (e.g. Marketing and Sales combined) | Gives the separate figures and says it cannot calculate the total |

The list of valid departments, categories and months comes from the data itself (`Distinct`), not from a hard-coded list. When a new department is added to the Excel file, the guardrail updates automatically.

## Testing

Expected answers were calculated independently in Python (`expected.py`) from the original CSV files, not from the Excel table the agent reads. `reconcile.py` first checks that the Power Query merge kept every row and every dollar (row count, rows per month, Budget total, Actual total).

| # | Question | Expected | Result |
|---|---|---|---|
| 1 | What is the total budget? | 1,217,482 | ✅ |
| 2 | What is the total budget for marketing? | 415,882 | ✅ |
| 3 | How much budget does the sales team have? | 474,116 | ✅ |
| 4 | Operations budget total? | 327,484 | ✅ |
| 5 | What is the budget for Finance? | No such department, list of departments | ✅ |
| 6 | Show me the HR department budget | No such department, list of departments | ✅ |
| 7 | What is the Marketing travel budget? | 33,524 | ✅ |
| 8 | What's the total budget for software? | 107,584 | ✅ |
| 9 | What is the Sales rent budget? | No Rent in Sales, list of Sales categories | ✅ |
| 10 | What is the Finance travel budget? | No such department | ✅ |
| 11 | What is the sales salaries total budget? (includes a duplicate row) | 301,438 | ✅ |
| 12 | What is the sales software budget? (clean control for #11) | 35,022 | ✅ |
| 13 | What was the budget for March? | 206,130 | ✅ |
| 14 | What was the total budget from January to March? | 611,431 | ✅ |
| 15 | What was the Marketing budget in February? | 67,142 | ✅ |
| 16 | What was the budget for January 2025? | No data, list of months | ✅ |
| 17 | What was the budget from April to September 2026? | Note on missing months, then 606,051 | ✅ |
| 18 | What was the budget from March onwards? | 812,181, no note | ✅ |
| 19 | What was the Travel budget in March? | 18,468 | ✅ |
| 20 | What is the total budget for marketing and sales? | Separate figures, no combined total | ✅ after fix (see below) |

Each question was run once in the Copilot Studio test pane after each change, and earlier questions were re-run after every change. Repeated runs have not been done yet, so these are first-pass results.

## What I found

- **The model did arithmetic when I did not expect it.** Asked for Marketing and Sales combined, the agent called the topic twice and then added the two figures itself. The answer happened to be right, but it broke the main rule. One instruction ("Never calculate, add, subtract, round or estimate figures yourself...") fixed it. My first re-test still failed because I had not started a new test conversation; the instruction was fine and the test was wrong.
- **When a branch has no output, the model fills the gap.** I forgot a Message node on one branch, and the model wrote a plausible sentence ("The budget query completed successfully, but did not return a budget amount") that hid the missing step. Every branch now ends with an explicit message.
- **Agent flows cannot sum or group.** The flow expression language has no function to add up a list of numbers, so the calculation moved to Power Fx inside the topic. Agent flows also cannot return a table, so the rows are passed as JSON text.
- **Two languages in one platform.** Flows use Power Automate expressions (`float(item()?['Budget'])`); topics use Power Fx (`Sum(Filter(...), Budget)`).
- **Defaults to change.** Topic inputs ask the user a follow-up question by default and hand over to a human if no value is found. For optional inputs both had to be turned off.
- **The Excel connector** returns dates as Excel serial numbers unless the date format is set to ISO 8601, and returns numbers as text.
- **Reading the topic's YAML caught a stale description.** The topic description still said "filtered by department" after category and month filters had been added. The model uses this description to decide when to use the topic.
- **General knowledge was on.** The agent's settings had `useModelKnowledge: true`. The numbers come from the flow and Power Fx, so the impact was limited, but for an agent that should only answer from company data, general knowledge should be off. My later RAG project ([finance-policy-rag](https://github.com/vicmeng188/finance-policy-rag)) turns web search off from the start.
- **Naming.** The agent flow was saved as "Untitled", and the topic shown as "Budget Query" still has the internal name `TotalBudgetTest` from early testing. Neither affects behaviour, but both make the solution harder for someone else to maintain. I now name flows and topics when I create them.

## What I would do differently in a real project

Building the calculation logic as flowchart nodes took far more effort than the same logic in Python. In practice, figures like these would live in a **Power BI semantic model** (DAX measures, and a date table with financial year columns, which removes the need to convert financial quarters in code), and the agent would query the model and report the result. Copilot Studio's strengths are integration, permissions and governance, not calculation.

## Limitations

- Each test was run once; repeated runs are still to do
- Not built: financial year quarters, Actual and variance figures, warnings about duplicate or missing rows, a combined total for several departments
- When a user gives a month without a year, the model fills in the year (it chose 2026 in testing)
- A gap in the middle of a period is detected by design, but could not be tested because the data has no missing month
- After a topic ends, the model sometimes restates the result in its own words
- Built on mock data in a developer environment

## Files

- `budget_query_topic.yaml`: the topic, exported from Copilot Studio's code editor
- `agent_instructions.txt`: the agent's instructions
- `reconcile.py`: checks the Power Query merge against the original CSV files
- `expected.py`: calculates the expected answers from the original CSV files
- `BudgetActual.xlsx`: the merged data table
- The two Python scripts read the original monthly CSV files from the [variance-qa-agent](https://github.com/vicmeng188/variance-qa-agent) repository. Clone both repositories into the same folder to run them.
## Agent flow definition

`agent_flow_redacted.json` is the agent flow that reads the budget data, exported from Copilot Studio as part of a solution (Nov 2026). Flow: manual trigger (called by the agent) → **List rows present in a table** (Excel Online for Business, OneDrive) → **Select** (keeps the needed columns) → **Respond to the agent** (returns the rows as JSON text). The OneDrive drive, file and table IDs were replaced with placeholders before publishing. The full solution export is kept privately, because it is only useful for re-importing into the original tenant.

This agent was built in Copilot Studio's classic experience (topics, Power Fx, agent flows).

## How this was built

I built this with Claude (Anthropic) as a mentor. We discussed the design together; Claude wrote the Python scripts and the Power Fx formulas, and I built the agent, flow and topic in Copilot Studio, ran the tests and checked every figure against the Python results. Several design decisions were mine, including how the category guardrail works, detecting missing months when only a start month is given, checking for missing months even when no period is given, and the paired test (#11 and #12) that compares a combination with a duplicate row against a clean one.
