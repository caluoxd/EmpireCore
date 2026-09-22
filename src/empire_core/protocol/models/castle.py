"""
Castle protocol models.

Commands:
- gcl: Get castles list
- dcl: Get detailed castle info
- jca: Jump to / select castle
- arc: Rename castle
- rst: Relocate castle
- grc: Get resources
- gpa: Get production rates
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ConfigDict, Field, field_validator, model_validator

from .base import BasePayload, BaseRequest, BaseResponse, Position, ResourceAmount
from .player import PlayerCastle

logger = logging.getLogger(__name__)

# =============================================================================
# GCL - Get Castles List
# =============================================================================


def _kingdom_entries(section: Any) -> list[tuple[int, dict[str, Any]]]:
    """(kingdom id, entry) pairs from a ``C: [{KID, AI: [...]}]`` section."""
    pairs: list[tuple[int, dict[str, Any]]] = []
    if not isinstance(section, list):
        return pairs
    for kingdom in section:
        if not isinstance(kingdom, dict) or not isinstance(kingdom.get("AI"), list):
            continue
        kid = kingdom.get("KID", 0)
        pairs.extend((kid, entry) for entry in kingdom["AI"] if isinstance(entry, dict))
    return pairs


class GetCastlesRequest(BaseRequest):
    """
    Get list of player's castles.

    Command: gcl
    Payload: {} (the game client sends {"PID": own_player_id})
    """

    command = "gcl"


class CastleInfo(BasePayload):
    """One of the player's locations: a gcl entry plus its positional row.

    The row layout is InteractiveMapobjectVO.parseAreaInfo's; the entry
    keys around it carry the gate and abandon timers.
    """

    castle_id: int = Field(default=0)
    castle_name: str = Field(default="")
    x: int = Field(default=0)
    y: int = Field(default=0)
    kingdom_id: int = Field(default=0)
    castle_type: int = Field(default=0)  # 1=castle, 3=capital, 4=outpost, 12=kingdom castle, 22=metro
    owner_id: int = Field(default=0)
    occupier_id: int = Field(default=-1)
    keep_level: int = Field(default=0)
    wall_level: int = Field(default=0)
    gate_level: int = Field(default=0)
    tower_level: int = Field(default=0)
    moat_level: int = Field(default=0)
    open_gate_seconds: int = Field(alias="OGT", default=0)
    open_gate_counter: int = Field(alias="OGC", default=0)
    abandon_outpost_seconds: int = Field(alias="AOT", default=-1)
    cancel_abandon_seconds: int = Field(alias="CAT", default=-1)
    no_abandon_seconds: int = Field(alias="TA", default=-1)

    @property
    def position(self) -> Position:
        """Get castle position as Position object."""
        return Position(X=self.x, Y=self.y, KID=self.kingdom_id)

    @classmethod
    def from_entry(cls, entry: dict[str, Any], kingdom: int = 0) -> CastleInfo:
        """Parse a ``gcl.C[].AI[]`` entry; its ``AI`` row shares the gdi layout."""
        row = entry["AI"]
        parsed = PlayerCastle.from_list(row, kingdom)
        timers = {key: entry[key] for key in ("OGT", "OGC", "AOT", "CAT", "TA") if key in entry}
        return cls(
            castle_id=parsed.location_id,
            castle_name=parsed.name,
            x=parsed.x,
            y=parsed.y,
            kingdom_id=kingdom,
            castle_type=parsed.castle_type,
            owner_id=parsed.owner_id,
            occupier_id=parsed.capturer_id,
            keep_level=row[5],
            wall_level=row[6],
            gate_level=row[7],
            tower_level=row[8],
            moat_level=row[9],
            **timers,
        )


class GetCastlesResponse(BaseResponse):
    """
    The player's castle list.

    Command: gcl
    Payload: {"PID": player_id, "C": [{"KID": kingdom, "AI": [{"AI": [row...], "AOT": .., "TA": ..}, ...]}, ...]}

    Entries are flattened across kingdoms into ``castles``.
    """

    command = "gcl"

    player_id: int = Field(alias="PID", default=0)
    castles: list[CastleInfo] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _flatten_kingdoms(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "C" not in data:
            return data
        data = dict(data)
        castles = []
        for kid, entry in _kingdom_entries(data.pop("C")):
            row = entry.get("AI")
            if not (isinstance(row, list) and len(row) > 10):
                logger.debug(f"Skipping malformed gcl row: {entry!r}")
                continue
            castles.append(CastleInfo.from_entry(entry, kid))
        data["castles"] = castles
        return data


# =============================================================================
# DCL - Get Detailed Castle Info
# =============================================================================


class GetDetailedCastleRequest(BaseRequest):
    """
    Get resources, units and production data for every castle the player owns.

    Command: dcl
    Payload: {} (the game client sends {"CD": 0}; the server lists every castle either way)
    """

    command = "dcl"


# Server keys of ClientConstCollectable.GROUP_LIST_RESOURCES, by field name.
_RESOURCE_KEYS = {
    "wood": "W",
    "stone": "S",
    "food": "F",
    "coal": "C",
    "oil": "O",
    "glass": "G",
    "iron": "I",
    "aquamarine": "A",
    "honey": "HONEY",
    "mead": "MEAD",
    "beef": "BEEF",
}


def _truncate(value: Any) -> Any:
    """Amounts arrive as floats ("W": 7000.0) and tick fractionally."""
    return int(value) if isinstance(value, float) else value


class ResourceSet(BasePayload):
    """One number per resource the client tracks per castle."""

    wood: float = Field(alias="W", default=0.0)
    stone: float = Field(alias="S", default=0.0)
    food: float = Field(alias="F", default=0.0)
    coal: float = Field(alias="C", default=0.0)
    oil: float = Field(alias="O", default=0.0)
    glass: float = Field(alias="G", default=0.0)
    iron: float = Field(alias="I", default=0.0)
    aquamarine: float = Field(alias="A", default=0.0)
    honey: float = Field(alias="HONEY", default=0.0)
    mead: float = Field(alias="MEAD", default=0.0)
    beef: float = Field(alias="BEEF", default=0.0)


class CastleProductionArea(BasePayload):
    """The ``gpa`` block of a dcl entry, as AreaDataCommonInfo, AreaDataStorageItem,
    AreaDataMorality and AreaDataUpdater read it.

    Per-resource values follow the client's key pattern and are exposed as
    :class:`ResourceSet` properties: ``D<key>`` / 10 is the hourly production,
    ``MR<key>`` the storage capacity, ``<key>M`` the production bonus in
    percent and ``SAFE_<key>`` the amount safe from plunder.
    """

    population: int = Field(alias="P", default=0)
    neutral_deco_points: int = Field(alias="NDP", default=0)
    sickness: int = Field(alias="S", default=0)
    riot: int = Field(alias="R", default=0)
    guards: int = Field(alias="GRD", default=0)
    build_speed_percent: int = Field(alias="BDB", default=100)
    metropolis_food_bonus: float = Field(alias="MP", default=0.0)
    unit_capacity: int = Field(alias="US", default=0)
    auxiliary_capacity: int = Field(alias="AUS", default=0)
    morale: int = Field(alias="M", default=0)
    food_consumption_delta: float = Field(alias="DFC", default=0.0)
    food_consumption_reduction_percent: int = Field(alias="FCR", default=100)
    mead_consumption_delta: float = Field(alias="DMEADC", default=0.0)
    mead_consumption_reduction_percent: int = Field(alias="MEADCR", default=100)
    beef_consumption_delta: float = Field(alias="DBEEFC", default=0.0)
    beef_consumption_reduction_percent: int = Field(alias="BEEFCR", default=100)
    barracks_speed: float = Field(alias="RS1", default=0.0)
    workshop_speed: float = Field(alias="RS2", default=0.0)
    defense_workshop_speed: float = Field(alias="RS3", default=0.0)
    hospital_speed: float = Field(alias="RSH", default=0.0)

    def _resource_set(self, prefix: str, suffix: str, divisor: int = 1) -> ResourceSet:
        extra = self.model_extra or {}
        values = {}
        for name, key in _RESOURCE_KEYS.items():
            raw = extra.get(f"{prefix}{key}{suffix}")
            if isinstance(raw, (int, float)) and not isinstance(raw, bool):
                values[name] = raw / divisor
        return ResourceSet(**values)

    @property
    def production(self) -> ResourceSet:
        """Hourly production per resource (``D<key>`` / 10)."""
        return self._resource_set("D", "", 10)

    @property
    def storage_capacity(self) -> ResourceSet:
        """Storage capacity per resource (``MR<key>``)."""
        return self._resource_set("MR", "")

    @property
    def production_bonus_percent(self) -> ResourceSet:
        """Production bonus per resource in percent (``<key>M``); 100 means no bonus."""
        return self._resource_set("", "M")

    @property
    def safe_amount(self) -> ResourceSet:
        """Amount per resource safe from plunder (``SAFE_<key>``)."""
        return self._resource_set("SAFE_", "")

    @property
    def food_consumption_per_hour(self) -> float:
        """Hourly food consumption (``DFC`` / 10)."""
        return self.food_consumption_delta / 10


class DetailedCastleInfo(BasePayload):
    """Per-castle detail from a dcl entry, as the client's DetailedCastleVO reads it."""

    castle_id: int = Field(alias="AID")
    kingdom_id: int = Field(alias="KID", default=0)
    wood: int = Field(alias="W", default=0)
    stone: int = Field(alias="S", default=0)
    food: int = Field(alias="F", default=0)
    coal: int = Field(alias="C", default=0)
    oil: int = Field(alias="O", default=0)
    glass: int = Field(alias="G", default=0)
    iron: int = Field(alias="I", default=0)
    aquamarine: int = Field(alias="A", default=0)
    honey: int = Field(alias="HONEY", default=0)
    mead: int = Field(alias="MEAD", default=0)
    beef: int = Field(alias="BEEF", default=0)
    defense_value: int = Field(alias="D", default=0)
    has_barracks: bool = Field(alias="B", default=False)
    has_siege_workshop: bool = Field(alias="WS", default=False)
    has_defense_workshop: bool = Field(alias="DW", default=False)
    has_hospital: bool = Field(alias="H", default=False)
    market_carriages: int = Field(alias="MC", default=0)
    open_gate_seconds: int = Field(alias="OGT", default=0)
    abandon_outpost_seconds: int = Field(alias="AOT", default=-1)
    raw_units: list[list[int]] = Field(alias="AC", default_factory=list)
    raw_stronghold_units: list[list[int]] = Field(alias="SHI", default_factory=list)
    raw_hospital_units: list[list[int]] = Field(alias="HI", default_factory=list)
    raw_travelling_units: list[list[int]] = Field(alias="TU", default_factory=list)
    production_area: CastleProductionArea | None = Field(alias="gpa", default=None)

    _truncate_amounts = field_validator(*_RESOURCE_KEYS, mode="before")(_truncate)

    @staticmethod
    def _pairs(rows: list[list[int]]) -> dict[int, int]:
        return {row[0]: row[1] for row in rows if len(row) >= 2}

    @property
    def units(self) -> dict[int, int]:
        """Units stationed here as {unit_id: count}, from the ``AC`` pairs."""
        return self._pairs(self.raw_units)

    @property
    def stronghold_units(self) -> dict[int, int]:
        """Units in the safe house / stronghold (``SHI``)."""
        return self._pairs(self.raw_stronghold_units)

    @property
    def hospital_units(self) -> dict[int, int]:
        """Wounded units in the hospital (``HI``)."""
        return self._pairs(self.raw_hospital_units)

    @property
    def travelling_units(self) -> dict[int, int]:
        """Units currently travelling (``TU``)."""
        return self._pairs(self.raw_travelling_units)


class GetDetailedCastleResponse(BaseResponse):
    """
    Detail for every castle the player owns.

    Command: dcl
    Payload: {"PID": player_id, "C": [{"KID": kingdom, "AI": [{"AID": castle_id, "W": .., "AC": [..], "gpa": {..}}]}]}
    """

    command = "dcl"

    player_id: int = Field(alias="PID", default=0)
    castles: list[DetailedCastleInfo] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _flatten_kingdoms(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "C" not in data:
            return data
        data = dict(data)
        data["castles"] = [{**entry, "KID": kid} for kid, entry in _kingdom_entries(data.pop("C"))]
        return data

    def castle(self, castle_id: int) -> DetailedCastleInfo | None:
        """The listed castle with this id, or None."""
        return next((c for c in self.castles if c.castle_id == castle_id), None)


# =============================================================================
# JCA - Jump to Castle / Select Castle
# =============================================================================


class SelectCastleRequest(BaseRequest):
    """
    Select/jump to a castle (makes it the active castle).

    Command: jca (acknowledged by the server as 'jaa')
    Payload: {"CID": castle_id, "KID": kingdom_id}
    """

    command = "jca"
    response_command = "jaa"

    castle_id: int = Field(alias="CID")
    kingdom_id: int = Field(alias="KID", default=0)


class SelectCastleResponse(BaseResponse):
    """
    Response to castle selection.

    Command: jaa
    """

    command = "jaa"


# =============================================================================
# ARC - Rename Castle
# =============================================================================


class RenameCastleRequest(BaseRequest):
    """
    Rename a castle.

    Command: arc
    Payload: {"CID": castle_id, "CN": "new_name"}
    """

    command = "arc"

    castle_id: int = Field(alias="CID")
    castle_name: str = Field(alias="CN")


class RenameCastleResponse(BaseResponse):
    """
    Response to castle rename.

    Command: arc
    """

    command = "arc"


# =============================================================================
# RST - Relocate Castle
# =============================================================================


class RelocateCastleRequest(BaseRequest):
    """
    Relocate a castle to new coordinates.

    Command: rst
    Payload: {"CID": castle_id, "X": x, "Y": y, "KID": kingdom_id}
    """

    command = "rst"

    castle_id: int = Field(alias="CID")
    x: int = Field(alias="X")
    y: int = Field(alias="Y")
    kingdom_id: int = Field(alias="KID", default=0)


class RelocateCastleResponse(BaseResponse):
    """
    Response to castle relocation.

    Command: rst
    """

    command = "rst"


# =============================================================================
# GRC - Get Resources
# =============================================================================


class GetResourcesRequest(BaseRequest):
    """
    Get current resources for a castle.

    Command: grc
    Payload: {"CID": castle_id}
    """

    command = "grc"

    castle_id: int = Field(alias="CID")


class GetResourcesResponse(BaseResponse):
    """
    Response containing castle resources.

    Command: grc
    """

    command = "grc"

    resources: ResourceAmount | None = Field(alias="R", default=None)
    storage_capacity: ResourceAmount | None = Field(alias="SC", default=None)


# =============================================================================
# GPA - Get Production
# =============================================================================


class GetProductionRequest(BaseRequest):
    """
    Get production rates for a castle.

    Command: gpa
    Payload: {"CID": castle_id}
    """

    command = "gpa"

    castle_id: int = Field(alias="CID")


class ProductionRates(BaseResponse):
    """Production rates per hour."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    wood: float = Field(alias="W", default=0.0)
    stone: float = Field(alias="S", default=0.0)
    food: float = Field(alias="F", default=0.0)
    coins: float = Field(alias="C", default=0.0)


class GetProductionResponse(BaseResponse):
    """
    Response containing production rates.

    Command: gpa
    """

    command = "gpa"

    production: ProductionRates | None = Field(alias="P", default=None)
    consumption: ProductionRates | None = Field(alias="CO", default=None)


__all__ = [
    # GCL - Get Castles
    "GetCastlesRequest",
    "GetCastlesResponse",
    "CastleInfo",
    # DCL - Detailed Castle
    "GetDetailedCastleRequest",
    "GetDetailedCastleResponse",
    "DetailedCastleInfo",
    "CastleProductionArea",
    "ResourceSet",
    # JCA - Select Castle
    "SelectCastleRequest",
    "SelectCastleResponse",
    # ARC - Rename Castle
    "RenameCastleRequest",
    "RenameCastleResponse",
    # RST - Relocate Castle
    "RelocateCastleRequest",
    "RelocateCastleResponse",
    # GRC - Get Resources
    "GetResourcesRequest",
    "GetResourcesResponse",
    # GPA - Get Production
    "GetProductionRequest",
    "GetProductionResponse",
    "ProductionRates",
]
