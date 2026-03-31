from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional


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
	completed: bool = False

	def is_due_on(self, target_date: date) -> bool:
		raise NotImplementedError

	def estimate_urgency(self, current_time: datetime) -> int:
		raise NotImplementedError

	def mark_completed(self) -> None:
		raise NotImplementedError

	def update_priority(self, new_priority: str) -> None:
		raise NotImplementedError


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
		raise NotImplementedError

	def remove_task(self, task_id: str) -> None:
		raise NotImplementedError

	def get_tasks_for_day(self, target_date: date) -> List[Task]:
		raise NotImplementedError

	def get_required_tasks(self) -> List[Task]:
		raise NotImplementedError


@dataclass
class Owner:
	owner_id: str
	name: str
	available_minutes_per_day: int
	preferred_time_blocks: List[str] = field(default_factory=list)
	max_tasks_per_day: int = 0
	pets: List[Pet] = field(default_factory=list)

	def update_preferences(self, preferred_time_blocks: List[str], max_tasks_per_day: int) -> None:
		raise NotImplementedError

	def set_daily_availability(self, minutes: int) -> None:
		raise NotImplementedError

	def add_pet(self, pet: Pet) -> None:
		if pet.owner_id is not None and pet.owner_id != self.owner_id:
			raise ValueError("Pet is already assigned to a different owner.")

		for existing_pet in self.pets:
			if existing_pet.pet_id == pet.pet_id:
				return

		pet.owner_id = self.owner_id
		self.pets.append(pet)

	def remove_pet(self, pet_id: str) -> None:
		for index, pet in enumerate(self.pets):
			if pet.pet_id == pet_id:
				pet.owner_id = None
				del self.pets[index]
				return


@dataclass
class Scheduler:
	scheduling_strategy: str = "priority-first"
	max_daily_minutes: int = 0
	rules: List[str] = field(default_factory=list)

	def generate_plan(self, owner: Owner, pets: List[Pet], target_date: date):
		raise NotImplementedError

	def filter_due_tasks(self, tasks: List[Task], target_date: date) -> List[Task]:
		raise NotImplementedError

	def rank_tasks(self, tasks: List[Task]) -> List[Task]:
		raise NotImplementedError

	def fit_tasks_into_time(self, tasks: List[Task], available_minutes: int) -> List[Task]:
		raise NotImplementedError

	def explain_selection(self) -> str:
		raise NotImplementedError
