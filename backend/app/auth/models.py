"""The value routes and services receive for "who is calling"."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CurrentUser:
    """The authenticated caller, reduced to what the application needs.

    Deliberately not the ORM `User`: nothing downstream can lazy-load, mutate,
    or accidentally serialise identity state. Ownership checks use `id` only.
    """

    id: UUID
