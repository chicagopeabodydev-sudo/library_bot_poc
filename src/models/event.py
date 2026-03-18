from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TargetAgeGroup = Literal["adult", "teen", "kids"]
TARGET_AGE_GROUP_VALUES: tuple[TargetAgeGroup, ...] = ("adult", "teen", "kids")


class LibraryEvent(BaseModel):
    """Structured representation of a single event described on the library website."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    event_type: str = Field(
        ...,
        description=(
            "Category of the event, such as storytime, author talk, book club, "
            "craft workshop, or game night."
        ),
    )
    event_title: str = Field(
        ...,
        description="Public-facing title of the library event.",
    )
    date_time: date | datetime = Field(
        ...,
        description=(
            "Date or full date-time for when the event occurs. Prefer an ISO-style "
            "value when the source page provides enough detail."
        ),
    )
    target_age_group: TargetAgeGroup = Field(
        ...,
        description="Intended audience age group. Must normalize to adult, teen, or kids.",
    )
    location: str = Field(
        ...,
        description="Room, branch, or physical location where the event is held.",
    )
    description: str = Field(
        ...,
        description="Short summary of what the event is about.",
    )
    link_to_details: str = Field(
        ...,
        description="URL on the library website with event details or registration information.",
    )

    @field_validator("target_age_group", mode="before")
    @classmethod
    def normalize_target_age_group(cls, value: object) -> object:
        """Normalize common age-group variants into the project's canonical values."""
        if not isinstance(value, str):
            return value

        normalized = value.strip().lower()
        aliases = {
            "adults": "adult",
            "teenagers": "teen",
            "teens": "teen",
            "young adult": "teen",
            "young adults": "teen",
            "child": "kids",
            "children": "kids",
            "kid": "kids",
        }
        return aliases.get(normalized, normalized)


class LibraryEventExtractionResult(BaseModel):
    """Structured extraction payload for a page that may describe one or more events."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    events: list[LibraryEvent] = Field(
        default_factory=list,
        description=(
            "List of event records found on the webpage. Return an empty list when "
            "the page does not contain event information."
        ),
    )
