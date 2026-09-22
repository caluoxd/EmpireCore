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

from pydantic import ConfigDict, Field, model_validator

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
    Payload: {} (empty)
    """

    command = "gcl"


class CastleInfo(BasePayload):
    """One of the player's locations, from a gcl row."""

    castle_id: int = 0
    castle_name: str = ""
    x: int = 0
    y: int = 0
    kingdom_id: int = 0
    castle_type: int = 0  # 1=castle, 3=capital, 4=outpost, 12=kingdom castle, 22=metro
    owner_id: int = 0

    @property
    def position(self) -> Position:
        """Get castle position as Position object."""
        return Position(X=self.x, Y=self.y, KID=self.kingdom_id)

    @classmethod
    def from_row(cls, row: list, kingdom: int = 0) -> CastleInfo:
        """Parse a ``gcl.C[].AI[].AI`` row; the layout is the gdi one."""
        parsed = PlayerCastle.from_list(row, kingdom)
        return cls(
            castle_id=parsed.location_id,
            castle_name=parsed.name,
            x=parsed.x,
            y=parsed.y,
            kingdom_id=parsed.kingdom,
            castle_type=parsed.castle_type,
            owner_id=parsed.owner_id,
        )


class GetCastlesResponse(BaseResponse):
    """
    The player's castle list.

    Command: gcl
    Payload: {"PID": player_id, "C": [{"KID": kingdom, "AI": [{"AI": [row...]}, ...]}, ...]}

    Rows are flattened across kingdoms into ``castles``.
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
            castles.append(CastleInfo.from_row(row, kid))
        data["castles"] = castles
        return data


# =============================================================================
# DCL - Get Detailed Castle Info
# =============================================================================


class GetDetailedCastleRequest(BaseRequest):
    """
    Get resources and units for every castle the player owns.

    Command: dcl
    Payload: {} (the server ignores any castle id and lists them all)
    """

    command = "dcl"


class DetailedCastleInfo(BasePayload):
    """Per-castle detail from a dcl row.

    Only wood, stone and food are typed. The other amounts (``C``, ``O``,
    ``G``, ``A``, ``I``, ``HONEY``, ...) and the ``gpa`` block are kept raw
    because their meaning is not confirmed.
    """

    castle_id: int = Field(alias="AID")
    kingdom_id: int = Field(alias="KID", default=0)
    resources: ResourceAmount = Field(default_factory=ResourceAmount)
    raw_units: list[list[int]] = Field(alias="AC", default_factory=list)
    raw_production: dict[str, Any] = Field(alias="gpa", default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _typed_resources(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "resources" in data:
            return data
        data = dict(data)
        # Amounts arrive as floats ("W": 7000.0) and tick fractionally.
        amounts = {}
        for key in ("W", "S", "F"):
            value = data.get(key)
            if value is not None:
                amounts[key] = int(value) if isinstance(value, float) else value
        data["resources"] = ResourceAmount(**amounts)
        return data

    @property
    def units(self) -> dict[int, int]:
        """Unit stacks stationed here as {unit_id: count}, from the ``AC`` pairs."""
        return {row[0]: row[1] for row in self.raw_units if len(row) >= 2}


class GetDetailedCastleResponse(BaseResponse):
    """
    Detail for every castle the player owns.

    Command: dcl
    Payload: {"PID": player_id, "C": [{"KID": kingdom, "AI": [{"AID": castle_id, "W": ..., "AC": [...]}, ...]}]}
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
