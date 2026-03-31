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

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
