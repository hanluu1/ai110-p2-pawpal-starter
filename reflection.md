# PawPal+ Project Reflection

## 1. System Design
3 core actions a user should be able to perform:
- add pets
- add task
- schedule tasks
**a. Initial design**
- Briefly describe your initial UML design. 
- What classes did you include, and what responsibilities did you assign to each?
My initial UML design used four core classes that matched the main user actions: add pets, add tasks, and generate a schedule.
1. Owner
Responsibility: store owner-level constraints and preferences, such as available time per day and preferred care windows. This class acts as the source of scheduling limits and manages the pet list.
2. Pet
Responsibility: represent each pet’s profile (name, species, age, notes) and hold the set of tasks associated with that pet. This class organizes care needs per pet.
3. Task
Responsibility: represent an individual care activity (for example walk, feeding, meds) with key scheduling data like duration, priority, recurrence, and required status. This is the atomic unit the scheduler evaluates.
4. Scheduler
Responsibility: take owner constraints and pet tasks, filter/rank tasks, and build a feasible daily plan. This class contains the decision logic for what gets scheduled and why.


**b. Design changes**

- Did your design change during implementation?
yes
- If yes, describe at least one change and why you made it.
One design change I made was enforcing a strict one-owner-to-many-pets relationship. Initially, my model could allow inconsistent ownership data, but I updated the Owner.add_pet and Owner.remove_pet behavior so each pet can only belong to one owner at a time. I made this change to prevent data integrity issues like the same pet being shared across multiple owners and to keep scheduling logic simpler and more reliable.

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

The scheduler considers four main constraints: (1) available minutes per day set by the owner, (2) a max tasks per day cap, (3) task priority (low/medium/high), and (4) whether a task is marked required. It also factors in the due window — tasks are given a higher urgency score if their time window is currently active or has already passed.

I decided that required status and priority mattered most because those directly reflect a pet's health needs. Time budget comes next since it is the hard physical limit. Due windows influence ranking but do not block scheduling outright, because a task is still better done late than skipped entirely.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

The scheduler uses a greedy first-fit algorithm: it ranks tasks by required status and urgency, then fills the time budget by taking each task in order until no more fit. This means it could miss a globally optimal combination. For example, two medium-priority 20-minute tasks might provide more value than one high-priority 45-minute task when only 40 minutes remain, but the greedy approach picks the high-priority one.

This tradeoff is reasonable because the scenario involves a single daily pet-care schedule, not a complex optimization problem. The greedy approach is fast, easy to understand, and gives the user predictable results they can reason about. Required tasks always get picked first anyway, so the scheduling logic never skips something critical.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

I asked AI to help think through the class structure and what responsibilities belonged where. During implementation, I used it to help write method bodies once the interfaces were clear. For example, giving it the exact method signature and docstring and asking it to implement the logic. For testing, I used it to generate edge-case scenarios I might not have thought of on my own, such as overnight due windows, negative duration tasks, and chained recurring completions.

The most helpful kinds of prompts were specific ones that included the method signature, the expected behavior, and the constraints. 

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

When generating tests for the conflict detection logic, the AI initially wrote tests that assumed overlapping windows would prevent tasks from being scheduled. I did not accept this because I had intentionally designed `warn_conflicts` to only produce warnings, not block scheduling — conflicts are reported so the user can decide what to do. I corrected the tests to assert on warning messages rather than on which tasks were selected, and I verified this by tracing through the `generate_plan` and `warn_conflicts` methods manually to confirm the separation of concerns was intentional and consistent.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

I tested five main behavior groups: (1) `next_occurrence` — verifying that daily tasks produce a next task one day later, weekly tasks produce one seven days later, and one-time tasks return None; (2) `complete_task` — confirming it marks the task done, appends the next occurrence for recurring tasks, and does not modify anything for an unknown ID; (3) `filter_tasks` — checking filtering by pet name, completion status, and target date with per-day completion semantics for recurring tasks; (4) `warn_conflicts` — verifying overlapping windows produce warnings and adjacent/non-overlapping windows do not; and (5) `sort_tasks_by_time` — confirming tasks are ordered by window start time with windowless tasks sorted last.

These tests were important because the recurrence and per-day completion logic is subtle — a daily task should appear again tomorrow even though it is marked completed today, and the is_completed_on method uses last_completed_date rather than the completed flag to handle this correctly. Getting this wrong would cause tasks to silently disappear from the schedule.

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

I am confident the core scheduling logic is correct for typical use cases. The greedy selection, ranking, conflict detection, and recurring task chain are all covered by tests. But for the edge cases around the time budget such as  tasks with zero duration fit even into a zero-minute budget, and tasks with negative duration corrupt the used-minutes counter — both are known limitations not yet fixed.

If I had more time I would test: (1) generating a schedule when required tasks alone exceed the time budget, (2) the interaction between max_tasks_per_day and required tasks, and (3) weekly recurrence across day-of-week boundaries when start_date falls on a different weekday than today.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

I am most satisfied with the separation between the data model and the scheduling logic. The Owner, Pet, and Task classes are responsible only for managing state, while Scheduler is responsible for decisions. This made it straightforward to test each layer in isolation — I could write tests for `complete_task` without involving the scheduler at all, and test `generate_plan` with simple hand-built owners without worrying about UI. The conflict detection also turned out well: keeping `detect_conflicts` as the raw logic and `warn_conflicts` as the human-readable wrapper made both easy to reuse in the UI and in tests.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

The main thing I would redesign is the scheduling algorithm. The current greedy first-fit is simple but it can produce suboptimal plans when tasks have varying durations. I would replace it with a proper 0-1 knapsack solver weighted by urgency score so that the scheduler maximizes total value within the time budget rather than just filling linearly. I would also add validation on Task construction to reject negative durations and malformed due windows upfront rather than silently degrading at runtime.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

The most valuable lesson was that the quality of AI output is almost entirely determined by how precisely you specify what you want. When I gave the AI vague goals, I got generic code that needed significant rework. When I gave it a clear interface: method name, parameters, return type, and the exact behavior to implement — the output was accurate and required minimal editing. 
