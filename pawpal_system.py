from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Task:
	task_id: str
	pet_id: str
	title: str
	category: str
	duration_minutes: int
	priority: str
	due_window: Optional[str] = None
	recurrence: str = "daily"
	is_required: bool = False
	start_date: Optional[date] = None
	completed: bool = False

	def is_due_on(self, target_date: date) -> bool:
		"""Check if the task is due on the given date based on recurrence pattern."""
		recurrence_value = self.recurrence.strip().lower()

		if recurrence_value == "daily":
			return True

		if recurrence_value == "weekly":
			anchor_date = self.start_date or target_date
			return target_date.weekday() == anchor_date.weekday()

		if recurrence_value in {"once", "one-time", "onetime"}:
			if self.start_date is None:
				return True
			return target_date == self.start_date

		return True

	def estimate_urgency(self, current_time: datetime) -> int:
		"""Calculate urgency score based on priority, required status, and due window."""
		priority_score = {
			"low": 1,
			"medium": 2,
			"high": 3,
		}.get(self.priority.strip().lower(), 1)

		score = priority_score * 10
		if self.is_required:
			score += 20

		window = self._parse_due_window()
		if window is None:
			return score

		start_minutes, end_minutes = window
		now_minutes = current_time.hour * 60 + current_time.minute

		if now_minutes > end_minutes:
			score += 25
		elif start_minutes <= now_minutes <= end_minutes:
			score += 15
		else:
			distance = abs(start_minutes - now_minutes)
			score += max(0, 10 - distance // 30)

		return score

	def mark_completed(self) -> None:
		"""Mark the task as completed."""
		self.completed = True

	def update_priority(self, new_priority: str) -> None:
		"""Update task priority; must be 'low', 'medium', or 'high'."""
		normalized_priority = new_priority.strip().lower()
		if normalized_priority not in {"low", "medium", "high"}:
			raise ValueError("Priority must be one of: low, medium, high.")
		self.priority = normalized_priority

	def _parse_due_window(self) -> Optional[Tuple[int, int]]:
		"""Parse due_window string (HH:MM-HH:MM) to start and end minutes tuple."""
		if not self.due_window:
			return None

		parts = self.due_window.split("-")
		if len(parts) != 2:
			return None

		try:
			start_hour, start_minute = [int(p) for p in parts[0].split(":")]
			end_hour, end_minute = [int(p) for p in parts[1].split(":")]
		except ValueError:
			return None

		start_minutes = start_hour * 60 + start_minute
		end_minutes = end_hour * 60 + end_minute
		if end_minutes < start_minutes:
			return None

		return start_minutes, end_minutes


@dataclass
class Pet:
	pet_id: str
	name: str
	species: str
	age: int
	health_notes: str
	owner_id: Optional[str] = None
	task_list: List[Task] = field(default_factory=list)

	def add_task(self, task: Task) -> None:
		"""Add a task to the pet's task list if not already present."""
		if task.pet_id and task.pet_id != self.pet_id:
			raise ValueError("Task pet_id does not match this pet.")

		for existing_task in self.task_list:
			if existing_task.task_id == task.task_id:
				return

		task.pet_id = self.pet_id
		self.task_list.append(task)

	def remove_task(self, task_id: str) -> None:
		"""Remove a task by ID from the pet's task list."""
		for index, task in enumerate(self.task_list):
			if task.task_id == task_id:
				del self.task_list[index]
				return

	def get_tasks_for_day(self, target_date: date) -> List[Task]:
		"""Get all uncompleted tasks due on a specific date."""
		return [task for task in self.task_list if task.is_due_on(target_date) and not task.completed]

	def get_required_tasks(self) -> List[Task]:
		"""Get all uncompleted required tasks."""
		return [task for task in self.task_list if task.is_required and not task.completed]


@dataclass
class Owner:
	owner_id: str
	name: str
	available_minutes_per_day: int
	preferred_time_blocks: List[str] = field(default_factory=list)
	max_tasks_per_day: int = 0
	pets: List[Pet] = field(default_factory=list)

	def update_preferences(self, preferred_time_blocks: List[str], max_tasks_per_day: int) -> None:
		"""Update owner's preferred time blocks and maximum tasks per day."""
		self.preferred_time_blocks = [block.strip() for block in preferred_time_blocks if block.strip()]
		if max_tasks_per_day < 0:
			raise ValueError("max_tasks_per_day cannot be negative.")
		self.max_tasks_per_day = max_tasks_per_day

	def set_daily_availability(self, minutes: int) -> None:
		"""Set the owner's daily available minutes."""
		if minutes < 0:
			raise ValueError("available minutes cannot be negative.")
		self.available_minutes_per_day = minutes

	def add_pet(self, pet: Pet) -> None:
		"""Add a pet to the owner's pet list if not already present."""
		if pet.owner_id is not None and pet.owner_id != self.owner_id:
			raise ValueError("Pet is already assigned to a different owner.")

		for existing_pet in self.pets:
			if existing_pet.pet_id == pet.pet_id:
				return

		pet.owner_id = self.owner_id
		self.pets.append(pet)

	def remove_pet(self, pet_id: str) -> None:
		"""Remove a pet by ID from the owner's pet list."""
		for index, pet in enumerate(self.pets):
			if pet.pet_id == pet_id:
				pet.owner_id = None
				del self.pets[index]
				return

	def get_all_tasks(self, target_date: Optional[date] = None) -> List[Task]:
		"""Get all uncompleted tasks for the owner's pets, optionally filtered by date."""
		all_tasks: List[Task] = []
		for pet in self.pets:
			if target_date is None:
				all_tasks.extend([task for task in pet.task_list if not task.completed])
			else:
				all_tasks.extend(pet.get_tasks_for_day(target_date))
		return all_tasks


@dataclass
class Scheduler:
	max_daily_minutes: int = 0
	last_plan: Dict[str, Any] = field(default_factory=dict, repr=False)

	def generate_plan(self, owner: Owner, target_date: date):
		"""Generate a daily task plan for an owner on the target date."""
		available_minutes = owner.available_minutes_per_day
		if self.max_daily_minutes > 0:
			available_minutes = min(available_minutes, self.max_daily_minutes)

		due_tasks = owner.get_all_tasks(target_date)
		ranked_tasks = self.rank_tasks(due_tasks)

		if owner.max_tasks_per_day > 0:
			ranked_tasks = ranked_tasks[: owner.max_tasks_per_day]

		selected_tasks = self.fit_tasks_into_time(ranked_tasks, available_minutes)
		selected_ids = {task.task_id for task in selected_tasks}
		unscheduled_tasks = [task for task in ranked_tasks if task.task_id not in selected_ids]

		total_minutes = sum(task.duration_minutes for task in selected_tasks)
		explanation = self._build_explanation(selected_tasks, unscheduled_tasks, available_minutes, total_minutes)

		self.last_plan = {
			"date": target_date.isoformat(),
			"selected_tasks": selected_tasks,
			"unscheduled_tasks": unscheduled_tasks,
			"available_minutes": available_minutes,
			"used_minutes": total_minutes,
			"explanation": explanation,
		}

		return self.last_plan

	def rank_tasks(self, tasks: List[Task]) -> List[Task]:
		"""Sort tasks by required status, urgency, duration, and title."""
		now = datetime.now()
		return sorted(
			tasks,
			key=lambda task: (
				not task.is_required,
				-task.estimate_urgency(now),
				task.duration_minutes,
				task.title.lower(),
			),
		)

	def fit_tasks_into_time(self, tasks: List[Task], available_minutes: int) -> List[Task]:
		"""Select tasks that fit within the available minutes."""
		selected: List[Task] = []
		used_minutes = 0

		for task in tasks:
			if used_minutes + task.duration_minutes <= available_minutes:
				selected.append(task)
				used_minutes += task.duration_minutes

		return selected

	def explain_selection(self) -> str:
		"""Return explanation of the last generated plan."""
		if not self.last_plan:
			return "No plan has been generated yet."

		return self.last_plan["explanation"]

	def _build_explanation(
		self,
		selected_tasks: List[Task],
		unscheduled_tasks: List[Task],
		available_minutes: int,
		used_minutes: int,
	) -> str:
		"""Build an explanation string for the task selection."""
		selected_titles = ", ".join(task.title for task in selected_tasks) or "none"
		unscheduled_titles = ", ".join(task.title for task in unscheduled_tasks) or "none"

		return (
			f"Selected tasks by required/priority/urgency within {available_minutes} minutes. "
			f"Used {used_minutes} minutes. "
			f"Scheduled: {selected_titles}. "
			f"Deferred: {unscheduled_titles}."
		)
