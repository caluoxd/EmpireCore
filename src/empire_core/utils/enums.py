"""Game enumerations.

One enum per server ID space, and the enum lives next to the packets that
describe it:

- kingdom IDs: :class:`empire_core.protocol.models.base.Kingdom` (re-exported
  here as ``KingdomType`` for backwards compatibility),
- map-scan item types (the ``AI`` array of a ``gaa`` response):
  :class:`empire_core.protocol.models.map.MapItemType`,
- movement area types (``TA``/``SA`` arrays of a ``gam``/``mrm`` movement):
  :class:`MapObjectType` below.
"""

from enum import IntEnum

from empire_core.protocol.models.base import Kingdom

# ``KingdomType`` used to be a second, shorter copy of the kingdom ID table (it
# was missing BERIMOND = 10). It is now an alias of the authoritative enum, so
# ``KingdomType`` and ``Kingdom`` are the same object and compare equal
# everywhere. Deprecated: new code should use ``Kingdom`` (exported from
# ``empire_core``); the alias is kept because it is part of the published API.
KingdomType = Kingdom


class MapObjectType(IntEnum):
    """Object types found in a movement's target/source area array.

    This is the type stored in :attr:`Movement.target_type
    <empire_core.state.world_models.Movement.target_type>` (``TA[0]``), i.e. the
    thing an army is marching at.

    Both this and :class:`empire_core.protocol.models.map.MapItemType` (the
    ``AI`` array of a map scan) mirror the client's ``WorldConst.AREA_TYPE_*``
    constants, so the two tables now agree wherever they overlap. Prefer
    ``MapItemType``: it covers the full table.
    """

    EMPTY = 0
    CASTLE = 1
    DUNGEON = 2
    CAPITAL = 3
    OUTPOST = 4
    TREASURE_DUNGEON = 7
    TREASURE_CAMP = 8
    SHADOW_AREA = 9
    VILLAGE = 10
    BOSS_DUNGEON = 11
    KINGDOM_CASTLE = 12
    EVENT_DUNGEON = 13
    NO_LANDMARK = 14
    FACTION_CAMP = 15
    FACTION_VILLAGE = 16
    FACTION_TOWER = 17
    FACTION_CAPITAL = 18
    PLAGUE_AREA = 19
    TROOP_HOSTEL = 20
    ALIEN_CAMP = 21
    METRO = 22
    KINGS_TOWER = 23
    ISLE_RESOURCE = 24
    ISLE_DUNGEON = 25
    MONUMENT = 26
    NOMAD_CAMP = 27
    LABORATORY = 28
    SAMURAI_CAMP = 29
    FACTION_INVASION_CAMP = 30
    DYNAMIC = 31
    ROBBER_BARON_CASTLE = 32  # Added explicitly
    SAMURAI_ALIEN_CAMP = 33
    RED_ALIEN_CAMP = 34
    ALLIANCE_NOMAD_CAMP = 35
    DAIMYO_CASTLE = 37
    DAIMYO_TOWNSHIP = 38
    ABG_RESOURCE_TOWER = 40
    ABG_TOWER = 41
    WOLF_KING = 42
    NO_OUTPOST = 99
    UNKNOWN = -1

    @property
    def is_player(self) -> bool:
        """Is this object a player-owned entity?"""
        return self in (
            MapObjectType.CASTLE,
            MapObjectType.OUTPOST,
            MapObjectType.CAPITAL,
            MapObjectType.METRO,
        )

    @property
    def is_npc(self) -> bool:
        """Is this a permanent NPC/Robber Baron target?"""
        return self in (
            MapObjectType.DUNGEON,
            MapObjectType.ROBBER_BARON_CASTLE,
            MapObjectType.BOSS_DUNGEON,
        )

    @property
    def is_event(self) -> bool:
        """Is this a temporary event target (Nomad, Samurai, Alien)?"""
        return self in (
            MapObjectType.NOMAD_CAMP,
            MapObjectType.SAMURAI_CAMP,
            MapObjectType.ALIEN_CAMP,
            MapObjectType.SAMURAI_ALIEN_CAMP,
            MapObjectType.RED_ALIEN_CAMP,
            MapObjectType.ALLIANCE_NOMAD_CAMP,
            MapObjectType.EVENT_DUNGEON,
        )

    @property
    def is_resource(self) -> bool:
        """Is this a resource village or island?"""
        return self in (
            MapObjectType.VILLAGE,
            MapObjectType.ISLE_RESOURCE,
            MapObjectType.FACTION_VILLAGE,
        )


class MovementType(IntEnum):
    """Army movement type, the ``T`` of a movement record.

    A returning army is not a type: any type can be on its way home, which is
    the movement's ``D`` flag.

    Client: ``ClientConstCastle`` MOVEMENTTYPE_* constants.
    """

    ATTACK = 0
    DEFENCE = 1
    TRAVEL = 2
    SPY = 3
    MARKET = 4
    SIEGE = 5
    TREASUREHUNT = 6
    NPC_ATTACK = 11
    PLAGUEMONK = 14
    OCCUPY_FACTION = 15
    ALIEN_ATTACK = 17
    FACTION_ATTACK = 18
    ALLIANCE_CITY_ATTACK = 19
    ALLIANCE_CAMP_TAUNT_ATTACK = 20
    ALLIANCE_CAMP_ATTACK = 21
    COLLECTOR = 23
    COLLECTOR_TEMP_SERVER = 24
    RANKSWAP_TEMP_SERVER = 25
    DAIMYO_TOWNSHIP_DEFENSE = 26
    DAIMYO_TAUNT_ATTACK = 27
    DAIMYO_CASTLE_ATTACK = 28
    ALLIANCE_BATTLE_GROUND_COLLECTOR_ATTACK = 29
    TEMPSERVER_PVE_CHARGE = 30
    TEMPSERVER_PVP_CHARGE = 31
    ABG_ALLIANCE_TOWER_SUPPORT = 32
    ABG_ALLIANCE_TOWER_ATTACK = 33
    WOLFKING_TAUNT_ATTACK = 34
    UNKNOWN = -1

    @property
    def is_attack(self) -> bool:
        """Types the client parses as an attack army (``ArmyAttackMapmovementVO`` or a subclass)."""
        return self in _ATTACK_MOVEMENT_TYPES

    @property
    def is_support(self) -> bool:
        """Types the client parses as a support army (``SupportDefenceMapmovementVO``)."""
        return self in (
            MovementType.DEFENCE,
            MovementType.DAIMYO_TOWNSHIP_DEFENSE,
            MovementType.ABG_ALLIANCE_TOWER_SUPPORT,
        )

    @property
    def is_siege(self) -> bool:
        """Types the client parses as a siege (``SiegeMapmovementVO``)."""
        return self in (MovementType.SIEGE, MovementType.OCCUPY_FACTION)


_ATTACK_MOVEMENT_TYPES = frozenset(
    {
        MovementType.ATTACK,
        MovementType.NPC_ATTACK,
        MovementType.ALIEN_ATTACK,
        MovementType.FACTION_ATTACK,
        MovementType.ALLIANCE_CITY_ATTACK,
        MovementType.ALLIANCE_CAMP_TAUNT_ATTACK,
        MovementType.ALLIANCE_CAMP_ATTACK,
        MovementType.COLLECTOR,
        MovementType.COLLECTOR_TEMP_SERVER,
        MovementType.RANKSWAP_TEMP_SERVER,
        MovementType.DAIMYO_TAUNT_ATTACK,
        MovementType.DAIMYO_CASTLE_ATTACK,
        MovementType.ALLIANCE_BATTLE_GROUND_COLLECTOR_ATTACK,
        MovementType.TEMPSERVER_PVE_CHARGE,
        MovementType.TEMPSERVER_PVP_CHARGE,
        MovementType.ABG_ALLIANCE_TOWER_ATTACK,
        MovementType.WOLFKING_TAUNT_ATTACK,
    }
)


class AllianceNotificationType(IntEnum):
    """Notification types in the alliance activity list (field ``A``)."""

    MEMBER_JOIN = 0
    MEMBER_LEFT = 1
    MEMBER_KICKED = 2
    MEMBER_NEW_LEADER = 3
    MEMBER_DEMOTE = 4
    MEMBER_PROMOTE = 5
    MEMBER_DONATE_C1 = 6
    MEMBER_DONATE_C2 = 7
    MEMBER_DONATE_RES = 8
    CHANGE_NAME = 9
    CHANGE_ANNOUNCEMENT = 10
    CHANGE_DESCRIPTION = 11
    UPGRADE = 12
    CHANGE_DIPLOMACY = 13
    GET_REQUEST_DIPLOMACY = 14
    SEND_REQUEST_DIPLOMACY = 15
    REFUSE_DIPLOMACY = 16
    LEVEL_UP = 17
    LEVEL_DOWN = 18
    DONATE_C1_BY_LEVELUP = 19
    DONATE_C2_BY_LEVELUP = 20
    DONATE_RES_BY_LEVELUP = 21
    MEMBER_EARN_FAME = 22
    CONQUERED_CAPITAL = 23
    LOST_CAPITAL = 24
    LOOSING_CAPITAL = 25
    TOURNAMENTREWARD = 26
    TOURNAMENTRANK = 27
    CONQUERED_METROPOL = 28
    LOST_METROPOL = 29
    LOOSING_METROPOL = 30
    MEMBER_INACTIVE_KICK = 31
    ALLIANCE_RANK_OF_LAST_ROUND = 32
    NEW_KINGS_NAME = 33
    PRIZE_C1_OF_LAST_ROUND = 35
    PRIZE_C2_OF_LAST_ROUND = 36
    STORM_ISLAND_ENDED = 37
    TRIBUT_PAY_C1 = 38
    TRIBUT_PAY_C2 = 39
    TRIBUT_PAY_RES = 40
    TRIBUT_GET_C1 = 41
    TRIBUT_GET_C2 = 42
    TRIBUT_GET_RES = 43
    ACTIVATE_TEMP_BUFF = 44
    EXTEND_TEMP_BUFF = 45
    ABANDONED_CAPITAL = 46
    ABANDONED_METROPOL = 47
    ALLIANCE_FOUNDED = 48
    FOUNDED_NOBLE_HOUSE = 49
    SET_EMBLEM = 50
    KING_CONFERED_ISLAND_TITLE = 56
    CAPITAL_OWNER_JOINED = 57
    METROPOLIS_OWNER_JOINED = 58
    REWARD_C1 = 59
    REWARD_C2 = 60
    ALLIANCE_BATTLE_GROUND_OWNED_TOWER_DEFEATED = 61
    ALLIANCE_BATTLE_GROUND_MALUS_INCREASED = 62
    ALLIANCE_BATTLE_GROUND_POINTS_GAINED = 63
    ALLIANCE_BATTLE_GROUND_MALUS_RESET = 64
    DAIMYO_ALLIANCE_CASTLE_CONTRACT_COMPLETED = 65
    DAIMYO_ALLIANCE_TOWNSHIP_CONTRACT_COMPLETED = 66