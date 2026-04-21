from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, field_validator, model_validator


class DamageLevel(str, Enum):
    MINIMAL  = "minimal"   # Structurally sound, cosmetic damage only, still functional
    PARTIAL  = "partial"   # Repairable, remains usable with caution
    COMPLETE = "complete"  # Structurally unsafe or destroyed


class InfrastructureType(str, Enum):
    RESIDENTIAL  = "residential"
    COMMERCIAL   = "commercial"
    GOVERNMENT   = "government"
    UTILITY      = "utility"
    TRANSPORT    = "transport"
    COMMUNITY    = "community"
    PUBLIC_SPACE = "public_space"
    OTHER        = "other"


class CrisisNature(str, Enum):
    EARTHQUAKE   = "earthquake"
    FLOOD        = "flood"
    TSUNAMI      = "tsunami"
    HURRICANE    = "hurricane"
    WILDFIRE     = "wildfire"
    EXPLOSION    = "explosion"
    CHEMICAL     = "chemical"
    CONFLICT     = "conflict"
    CIVIL_UNREST = "civil_unrest"


class DamageReportSubmission(BaseModel):
    # Mandatory fields — values are specified by UNDP RAPIDA; do not rename
    damage_level: DamageLevel
    infrastructure_types: List[InfrastructureType]
    crisis_nature: CrisisNature
    requires_debris_clearing: bool
    crisis_event_id: str
    channel: str  # telegram | pwa

    # Location — at least one required
    gps_lat: Optional[float] = None
    gps_lon: Optional[float] = None
    what3words_address: Optional[str] = None
    location_description: Optional[str] = None

    # Optional
    description: Optional[str] = None
    infrastructure_name: Optional[str] = None
    other_infra_description: Optional[str] = None
    modular_fields: Optional[dict] = None

    @field_validator("infrastructure_types")
    @classmethod
    def must_have_at_least_one(cls, v: List[InfrastructureType]) -> List[InfrastructureType]:
        if not v:
            raise ValueError("At least one infrastructure type is required")
        return v

    @field_validator("channel")
    @classmethod
    def valid_channel(cls, v: str) -> str:
        allowed = {"telegram", "pwa"}
        if v not in allowed:
            raise ValueError(f"channel must be one of {allowed}")
        return v

    @model_validator(mode="after")
    def must_have_some_location(self) -> "DamageReportSubmission":
        has_gps = self.gps_lat is not None and self.gps_lon is not None
        if not has_gps and not self.what3words_address and not self.location_description:
            raise ValueError(
                "At least one location method required: GPS coordinates, "
                "what3words address, or location description"
            )
        return self

    @model_validator(mode="after")
    def other_requires_description(self) -> "DamageReportSubmission":
        if InfrastructureType.OTHER in self.infrastructure_types and not self.other_infra_description:
            raise ValueError("other_infra_description is required when infrastructure type is 'other'")
        return self
