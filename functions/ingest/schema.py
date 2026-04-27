from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, field_validator, model_validator


class DamageLevel(str, Enum):
    MINIMAL  = "minimal"   # Structurally sound, cosmetic damage only, still functional
    PARTIAL  = "partial"   # Repairable, remains usable with caution
    COMPLETE = "complete"  # Structurally unsafe or destroyed


# Kept for backward compatibility with old payloads that still send enum values.
# Not used for validation of new submissions — infrastructure_types is now open-ended.
class InfrastructureType(str, Enum):
    RESIDENTIAL  = "residential"
    COMMERCIAL   = "commercial"
    GOVERNMENT   = "government"
    UTILITY      = "utility"
    TRANSPORT    = "transport"
    COMMUNITY    = "community"
    PUBLIC_SPACE = "public_space"
    OTHER        = "other"


# Kept for backward compatibility only — crisis_nature moves to the responses dict
# in the dynamic schema model. Old clients (bot/PWA before Phase 3/4) still send
# crisis_nature as a top-level form field and it is accepted as-is.
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
    # ── Mandatory system fields ────────────────────────────────────────────────
    # damage_level values are locked (minimal/partial/complete) — see DamageLevel enum.
    damage_level: DamageLevel

    # infrastructure_types is now open-ended (coordinator-configured options);
    # at least one value is still required.
    infrastructure_types: List[str]

    crisis_event_id: str
    channel: str  # telegram | pwa

    # ── Dynamic schema support (new clients) ──────────────────────────────────
    # schema_version ties this report to the exact form schema used at submission.
    schema_version: Optional[int] = None

    # responses holds all custom field answers (crisis_nature, requires_debris_clearing,
    # water_level, electricity_status, etc.). Replaces modular_fields.
    responses: Optional[dict] = None

    # ── Legacy fields (old clients — still accepted for backward compat) ───────
    # These moved into responses in the dynamic schema model. Old bot/PWA builds
    # that still send them as top-level form fields are accepted transparently.
    crisis_nature: Optional[str] = None
    requires_debris_clearing: Optional[bool] = None

    # ── Location — at least one required ─────────────────────────────────────
    gps_lat: Optional[float] = None
    gps_lon: Optional[float] = None
    what3words_address: Optional[str] = None
    location_description: Optional[str] = None

    # ── Optional extras ───────────────────────────────────────────────────────
    description: Optional[str] = None
    infrastructure_name: Optional[str] = None
    other_infra_description: Optional[str] = None

    # Deprecated — use responses instead. Accepted for old clients, ignored when
    # responses is also present.
    modular_fields: Optional[dict] = None

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("infrastructure_types")
    @classmethod
    def must_have_at_least_one(cls, v: List[str]) -> List[str]:
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

    # ── Convenience helpers ───────────────────────────────────────────────────

    def get_crisis_nature(self) -> str | None:
        """Read crisis_nature from responses (new) then legacy field (old)."""
        if self.responses:
            val = self.responses.get("crisis_nature")
            if val:
                return str(val)
        return self.crisis_nature

    def get_requires_debris_clearing(self) -> bool:
        """Read requires_debris_clearing from responses (new) then legacy field (old)."""
        if self.responses:
            val = self.responses.get("requires_debris_clearing")
            if val is not None:
                if isinstance(val, bool):
                    return val
                return str(val).lower() in ("true", "1", "yes")
        return self.requires_debris_clearing or False

    def get_effective_responses(self) -> dict:
        """
        Return a unified responses dict for storage.
        Merges legacy top-level fields into responses so all custom field answers
        are stored in one place regardless of which client format was used.
        """
        merged: dict = {}

        # Start with legacy modular_fields (lowest priority)
        if self.modular_fields:
            merged.update(self.modular_fields)

        # Then legacy top-level fields
        if self.crisis_nature and "crisis_nature" not in merged:
            merged["crisis_nature"] = self.crisis_nature
        if self.requires_debris_clearing is not None and "requires_debris_clearing" not in merged:
            merged["requires_debris_clearing"] = self.requires_debris_clearing

        # Finally, new responses dict (highest priority — overwrites legacy)
        if self.responses:
            merged.update(self.responses)

        return merged
