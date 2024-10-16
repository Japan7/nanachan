from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import Field
from pydantic.dataclasses import dataclass


class AnilistCharacterRole(str, Enum):
    MAIN = 'MAIN'
    SUPPORTING = 'SUPPORTING'
    BACKGROUND = 'BACKGROUND'


class AnilistEntryStatus(str, Enum):
    CURRENT = 'CURRENT'
    COMPLETED = 'COMPLETED'
    PAUSED = 'PAUSED'
    DROPPED = 'DROPPED'
    PLANNING = 'PLANNING'
    REPEATING = 'REPEATING'


class AnilistMediaSeason(str, Enum):
    WINTER = 'WINTER'
    SPRING = 'SPRING'
    SUMMER = 'SUMMER'
    FALL = 'FALL'


class AnilistMediaStatus(str, Enum):
    FINISHED = 'FINISHED'
    RELEASING = 'RELEASING'
    NOT_YET_RELEASED = 'NOT_YET_RELEASED'
    CANCELLED = 'CANCELLED'
    HIATUS = 'HIATUS'


class AnilistMediaType(str, Enum):
    ANIME = 'ANIME'
    MANGA = 'MANGA'


class AnilistService(str, Enum):
    ANILIST = 'ANILIST'
    MYANIMELIST = 'MYANIMELIST'


class MediaType(str, Enum):
    ANIME = 'ANIME'
    MANGA = 'MANGA'


class PresencePresenceType(str, Enum):
    PLAYING = 'PLAYING'
    LISTENING = 'LISTENING'
    WATCHING = 'WATCHING'


class ProjectionStatus(str, Enum):
    ONGOING = 'ONGOING'
    COMPLETED = 'COMPLETED'


class QuizzStatus(str, Enum):
    STARTED = 'STARTED'
    ENDED = 'ENDED'


class WaicolleCollagePosition(str, Enum):
    DEFAULT = 'DEFAULT'
    LEFT_OF = 'LEFT_OF'
    RIGHT_OF = 'RIGHT_OF'


class WaicolleGameMode(str, Enum):
    WAIFU = 'WAIFU'
    HUSBANDO = 'HUSBANDO'
    ALL = 'ALL'


class WaicolleRank(str, Enum):
    S = 'S'
    A = 'A'
    B = 'B'
    C = 'C'
    D = 'D'
    E = 'E'


@dataclass
class AccountMergeResult:
    id: UUID


@dataclass
class AccountSelectAllResult:
    service: 'AnilistService'
    username: str
    user: 'AccountSelectAllResultUser'


@dataclass
class AccountSelectAllResultUser:
    discord_id: int
    discord_id_str: str


@dataclass
class AccountSelectResult:
    username: str
    user: 'AccountSelectResultUser'


@dataclass
class AccountSelectResultUser:
    discord_id: int
    discord_id_str: str


@dataclass
class AddPlayerCoinsBody:
    moecoins: int | None = None
    blood_shards: int | None = None


@dataclass
class Body_client_login:
    username: str
    password: str
    grant_type: str | None = None
    scope: str | None = None
    client_id: str | None = None
    client_secret: str | None = None


@dataclass
class BulkUpdateWaifusBody:
    locked: bool | None = None
    blooded: bool | None = None
    nanaed: bool | None = None
    custom_collage: bool | None = None


@dataclass
class CEdgeSelectFilterCharaResult:
    character_role: 'AnilistCharacterRole'
    media: 'CEdgeSelectFilterCharaResultMedia'
    voice_actors: list['CEdgeSelectFilterCharaResultVoiceActors']


@dataclass
class CEdgeSelectFilterCharaResultMedia:
    id_al: int
    favourites: int
    site_url: str
    type: 'AnilistMediaType'
    id_mal: int | None
    title_user_preferred: str
    title_native: str | None
    title_english: str | None
    synonyms: list[str]
    description: str | None
    status: 'AnilistMediaStatus | None'
    season: 'AnilistMediaSeason | None'
    season_year: int | None
    episodes: int | None
    duration: int | None
    chapters: int | None
    cover_image_extra_large: str
    cover_image_color: str | None
    popularity: int
    is_adult: bool
    genres: list[str]


@dataclass
class CEdgeSelectFilterCharaResultVoiceActors:
    id_al: int
    favourites: int
    site_url: str
    name_user_preferred: str
    name_native: str | None
    name_alternative: list[str]
    description: str | None
    image_large: str
    gender: str | None
    age: int | None
    date_of_birth_year: int | None
    date_of_birth_month: int | None
    date_of_birth_day: int | None
    date_of_death_year: int | None
    date_of_death_month: int | None
    date_of_death_day: int | None


@dataclass
class CEdgeSelectFilterMediaResult:
    character_role: 'AnilistCharacterRole'
    character: 'CEdgeSelectFilterMediaResultCharacter'
    voice_actors: list['CEdgeSelectFilterMediaResultVoiceActors']


@dataclass
class CEdgeSelectFilterMediaResultCharacter:
    id_al: int
    favourites: int
    site_url: str
    name_user_preferred: str
    name_alternative: list[str]
    name_alternative_spoiler: list[str]
    name_native: str | None
    description: str | None
    image_large: str
    gender: str | None
    age: str | None
    date_of_birth_year: int | None
    date_of_birth_month: int | None
    date_of_birth_day: int | None
    rank: 'WaicolleRank'
    fuzzy_gender: str | None


@dataclass
class CEdgeSelectFilterMediaResultVoiceActors:
    id_al: int
    favourites: int
    site_url: str
    name_user_preferred: str
    name_native: str | None
    name_alternative: list[str]
    description: str | None
    image_large: str
    gender: str | None
    age: int | None
    date_of_birth_year: int | None
    date_of_birth_month: int | None
    date_of_birth_day: int | None
    date_of_death_year: int | None
    date_of_death_month: int | None
    date_of_death_day: int | None


@dataclass
class CEdgeSelectFilterStaffResult:
    character_role: 'AnilistCharacterRole'
    media: 'CEdgeSelectFilterStaffResultMedia'
    character: 'CEdgeSelectFilterStaffResultCharacter'


@dataclass
class CEdgeSelectFilterStaffResultCharacter:
    id_al: int
    favourites: int
    site_url: str
    name_user_preferred: str
    name_alternative: list[str]
    name_alternative_spoiler: list[str]
    name_native: str | None
    description: str | None
    image_large: str
    gender: str | None
    age: str | None
    date_of_birth_year: int | None
    date_of_birth_month: int | None
    date_of_birth_day: int | None
    rank: 'WaicolleRank'
    fuzzy_gender: str | None


@dataclass
class CEdgeSelectFilterStaffResultMedia:
    id_al: int
    favourites: int
    site_url: str
    type: 'AnilistMediaType'
    id_mal: int | None
    title_user_preferred: str
    title_native: str | None
    title_english: str | None
    synonyms: list[str]
    description: str | None
    status: 'AnilistMediaStatus | None'
    season: 'AnilistMediaSeason | None'
    season_year: int | None
    episodes: int | None
    duration: int | None
    chapters: int | None
    cover_image_extra_large: str
    cover_image_color: str | None
    popularity: int
    is_adult: bool
    genres: list[str]


@dataclass
class CharaNameAutocompleteResult:
    id_al: int
    name_user_preferred: str
    name_native: str | None = None


@dataclass
class CharaSelectResult:
    id_al: int
    favourites: int
    site_url: str
    name_user_preferred: str
    name_alternative: list[str]
    name_alternative_spoiler: list[str]
    name_native: str | None
    description: str | None
    image_large: str
    gender: str | None
    age: str | None
    date_of_birth_year: int | None
    date_of_birth_month: int | None
    date_of_birth_day: int | None
    rank: 'WaicolleRank'
    fuzzy_gender: str | None


@dataclass
class ClientInsertResult:
    id: UUID


@dataclass
class CollageResult:
    total: int
    url: str | None = None


@dataclass
class CollectPotBody:
    discord_username: str
    amount: float


@dataclass
class CollectionAddMediaResult:
    collection: 'CollectionAddMediaResultCollection'
    media: 'CollectionAddMediaResultMedia'


@dataclass
class CollectionAddMediaResultCollection:
    id: UUID
    name: str


@dataclass
class CollectionAddMediaResultMedia:
    id_al: int
    type: 'AnilistMediaType'
    title_user_preferred: str


@dataclass
class CollectionAddStaffResult:
    collection: 'CollectionAddStaffResultCollection'
    staff: 'CollectionAddStaffResultStaff'


@dataclass
class CollectionAddStaffResultCollection:
    id: UUID
    name: str


@dataclass
class CollectionAddStaffResultStaff:
    id_al: int
    name_user_preferred: str
    name_native: str | None


@dataclass
class CollectionAlbumResult:
    total: int
    owned: int
    collection: 'CollectionGetByIdResult'
    url: str | None = None


@dataclass
class CollectionDeleteResult:
    id: UUID


@dataclass
class CollectionGetByIdResult:
    id: UUID
    name: str
    author: 'CollectionGetByIdResultAuthor'
    medias_ids_al: list[int]
    staffs_ids_al: list[int]
    characters_ids_al: list[int]


@dataclass
class CollectionGetByIdResultAuthor:
    user: 'CollectionGetByIdResultAuthorUser'


@dataclass
class CollectionGetByIdResultAuthorUser:
    discord_id: int
    discord_id_str: str


@dataclass
class CollectionInsertResult:
    id: UUID
    name: str
    author: 'CollectionInsertResultAuthor'


@dataclass
class CollectionInsertResultAuthor:
    user: 'CollectionInsertResultAuthorUser'


@dataclass
class CollectionInsertResultAuthorUser:
    discord_id: int
    discord_id_str: str


@dataclass
class CollectionNameAutocompleteResult:
    id: UUID
    name: str
    author_discord_id: int


@dataclass
class CollectionRemoveMediaResult:
    id: UUID


@dataclass
class CollectionRemoveStaffResult:
    id: UUID


@dataclass
class CommitTradeResponse:
    waifus_a: list['WaifuSelectResult']
    waifus_b: list['WaifuSelectResult']


@dataclass
class CouponDeleteResult:
    id: UUID


@dataclass
class CouponInsertResult:
    code: str


@dataclass
class CouponSelectAllResult:
    code: str
    claimed_by: list['CouponSelectAllResultClaimedBy']


@dataclass
class CouponSelectAllResultClaimedBy:
    user: 'CouponSelectAllResultClaimedByUser'


@dataclass
class CouponSelectAllResultClaimedByUser:
    discord_id: int
    discord_id_str: str


@dataclass
class CustomizeWaifuBody:
    custom_image: str | None = None
    custom_name: str | None = None


@dataclass
class DonatePlayerCoinsBody:
    moecoins: int


@dataclass
class EndGameBody:
    winner_discord_id: int
    winner_discord_username: str


@dataclass
class EntrySelectAllResult:
    status: 'AnilistEntryStatus'
    progress: int
    score: float
    media: 'EntrySelectAllResultMedia'
    account: 'EntrySelectAllResultAccount'


@dataclass
class EntrySelectAllResultAccount:
    user: 'EntrySelectAllResultAccountUser'


@dataclass
class EntrySelectAllResultAccountUser:
    discord_id: int
    discord_id_str: str


@dataclass
class EntrySelectAllResultMedia:
    id_al: int


@dataclass
class EntrySelectFilterMediaResult:
    status: 'AnilistEntryStatus'
    progress: int
    score: float
    account: 'EntrySelectFilterMediaResultAccount'


@dataclass
class EntrySelectFilterMediaResultAccount:
    user: 'EntrySelectFilterMediaResultAccountUser'


@dataclass
class EntrySelectFilterMediaResultAccountUser:
    discord_id: int
    discord_id_str: str


@dataclass
class GameDeleteByMessageIdResult:
    id: UUID


@dataclass
class GameEndResult:
    id: UUID
    status: 'QuizzStatus'
    message_id: int
    message_id_str: str
    answer_bananed: str | None
    started_at: datetime
    ended_at: datetime | None
    winner: 'GameEndResultWinner | None'
    quizz: 'GameEndResultQuizz'


@dataclass
class GameEndResultQuizz:
    id: UUID
    channel_id: int
    channel_id_str: str
    description: str | None
    url: str | None
    is_image: bool
    answer: str | None
    answer_source: str | None
    submitted_at: datetime
    hikaried: bool | None
    author: 'GameEndResultQuizzAuthor'


@dataclass
class GameEndResultQuizzAuthor:
    discord_id: int
    discord_id_str: str


@dataclass
class GameEndResultWinner:
    discord_id: int
    discord_id_str: str


@dataclass
class GameGetByIdResult:
    id: UUID
    status: 'QuizzStatus'
    message_id: int
    message_id_str: str
    answer_bananed: str | None
    started_at: datetime
    ended_at: datetime | None
    winner: 'GameGetByIdResultWinner | None'
    quizz: 'GameGetByIdResultQuizz'


@dataclass
class GameGetByIdResultQuizz:
    id: UUID
    channel_id: int
    channel_id_str: str
    description: str | None
    url: str | None
    is_image: bool
    answer: str | None
    answer_source: str | None
    submitted_at: datetime
    hikaried: bool | None
    author: 'GameGetByIdResultQuizzAuthor'


@dataclass
class GameGetByIdResultQuizzAuthor:
    discord_id: int
    discord_id_str: str


@dataclass
class GameGetByIdResultWinner:
    discord_id: int
    discord_id_str: str


@dataclass
class GameGetCurrentResult:
    id: UUID
    status: 'QuizzStatus'
    message_id: int
    message_id_str: str
    answer_bananed: str | None
    started_at: datetime
    ended_at: datetime | None
    winner: 'GameGetCurrentResultWinner | None'
    quizz: 'GameGetCurrentResultQuizz'


@dataclass
class GameGetCurrentResultQuizz:
    id: UUID
    channel_id: int
    channel_id_str: str
    description: str | None
    url: str | None
    is_image: bool
    answer: str | None
    answer_source: str | None
    submitted_at: datetime
    hikaried: bool | None
    author: 'GameGetCurrentResultQuizzAuthor'


@dataclass
class GameGetCurrentResultQuizzAuthor:
    discord_id: int
    discord_id_str: str


@dataclass
class GameGetCurrentResultWinner:
    discord_id: int
    discord_id_str: str


@dataclass
class GameGetLastResult:
    id: UUID
    status: 'QuizzStatus'
    message_id: int
    message_id_str: str
    answer_bananed: str | None
    started_at: datetime
    ended_at: datetime | None
    winner: 'GameGetLastResultWinner | None'
    quizz: 'GameGetLastResultQuizz'


@dataclass
class GameGetLastResultQuizz:
    id: UUID
    channel_id: int
    channel_id_str: str
    description: str | None
    url: str | None
    is_image: bool
    answer: str | None
    answer_source: str | None
    submitted_at: datetime
    hikaried: bool | None
    author: 'GameGetLastResultQuizzAuthor'


@dataclass
class GameGetLastResultQuizzAuthor:
    discord_id: int
    discord_id_str: str


@dataclass
class GameGetLastResultWinner:
    discord_id: int
    discord_id_str: str


@dataclass
class GameNewResult:
    id: UUID


@dataclass
class GameSelectResult:
    id: UUID
    status: 'QuizzStatus'
    message_id: int
    message_id_str: str
    answer_bananed: str | None
    started_at: datetime
    ended_at: datetime | None
    winner: 'GameSelectResultWinner | None'
    quizz: 'GameSelectResultQuizz'


@dataclass
class GameSelectResultQuizz:
    id: UUID
    channel_id: int
    channel_id_str: str
    description: str | None
    url: str | None
    is_image: bool
    answer: str | None
    answer_source: str | None
    submitted_at: datetime
    hikaried: bool | None
    author: 'GameSelectResultQuizzAuthor'


@dataclass
class GameSelectResultQuizzAuthor:
    discord_id: int
    discord_id_str: str


@dataclass
class GameSelectResultWinner:
    discord_id: int
    discord_id_str: str


@dataclass
class GameUpdateBananedResult:
    id: UUID


@dataclass
class GuildEventDeleteResult:
    url: str | None
    start_time: datetime
    name: str
    location: str | None
    image: str | None
    end_time: datetime
    discord_id_str: str
    description: str | None
    discord_id: int
    id: UUID
    projection: 'GuildEventDeleteResultProjection | None'
    organizer: 'GuildEventDeleteResultOrganizer'
    participants: list['GuildEventDeleteResultParticipants']
    client: 'GuildEventDeleteResultClient'


@dataclass
class GuildEventDeleteResultClient:
    id: UUID
    password_hash: str
    username: str


@dataclass
class GuildEventDeleteResultOrganizer:
    id: UUID
    discord_id: int
    discord_id_str: str
    discord_username: str


@dataclass
class GuildEventDeleteResultParticipants:
    id: UUID
    discord_id: int
    discord_id_str: str
    discord_username: str


@dataclass
class GuildEventDeleteResultProjection:
    id: UUID
    channel_id: int
    channel_id_str: str
    message_id: int | None
    message_id_str: str | None
    name: str
    status: 'ProjectionStatus'


@dataclass
class GuildEventMergeResult:
    id: UUID
    discord_id: int
    description: str | None
    discord_id_str: str
    end_time: datetime
    image: str | None
    location: str | None
    name: str
    start_time: datetime
    url: str | None
    client: 'GuildEventMergeResultClient'
    participants: list['GuildEventMergeResultParticipants']
    organizer: 'GuildEventMergeResultOrganizer'
    projection: 'GuildEventMergeResultProjection | None'


@dataclass
class GuildEventMergeResultClient:
    id: UUID
    password_hash: str
    username: str


@dataclass
class GuildEventMergeResultOrganizer:
    id: UUID
    discord_id: int
    discord_id_str: str
    discord_username: str


@dataclass
class GuildEventMergeResultParticipants:
    id: UUID
    discord_id: int
    discord_id_str: str
    discord_username: str


@dataclass
class GuildEventMergeResultProjection:
    id: UUID
    channel_id: int
    channel_id_str: str
    message_id: int | None
    message_id_str: str | None
    name: str
    status: 'ProjectionStatus'


@dataclass
class GuildEventParticipantAddResult:
    id: UUID


@dataclass
class GuildEventParticipantRemoveResult:
    id: UUID


@dataclass
class GuildEventSelectResult:
    id: UUID
    discord_id: int
    description: str | None
    discord_id_str: str
    end_time: datetime
    image: str | None
    location: str | None
    name: str
    start_time: datetime
    url: str | None
    client: 'GuildEventSelectResultClient'
    participants: list['GuildEventSelectResultParticipants']
    organizer: 'GuildEventSelectResultOrganizer'
    projection: 'GuildEventSelectResultProjection | None'


@dataclass
class GuildEventSelectResultClient:
    id: UUID
    password_hash: str
    username: str


@dataclass
class GuildEventSelectResultOrganizer:
    id: UUID
    discord_id: int
    discord_id_str: str
    discord_username: str


@dataclass
class GuildEventSelectResultParticipants:
    id: UUID
    discord_id: int
    discord_id_str: str
    discord_username: str


@dataclass
class GuildEventSelectResultProjection:
    id: UUID
    channel_id: int
    channel_id_str: str
    message_id: int | None
    message_id_str: str | None
    name: str
    status: 'ProjectionStatus'


@dataclass
class HTTPExceptionModel:
    detail: str


@dataclass
class HTTPValidationError:
    detail: list['ValidationError'] | None = None


@dataclass
class HistoireDeleteByIdResult:
    id: UUID


@dataclass
class HistoireGetByIdResult:
    id: UUID
    title: str
    text: str
    formatted: bool


@dataclass
class HistoireInsertResult:
    id: UUID


@dataclass
class HistoireSelectIdTitleResult:
    id: UUID
    title: str


@dataclass
class LoginResponse:
    access_token: str
    token_type: str


@dataclass
class MediaAlbumResult:
    total: int
    owned: int
    media: 'MediaSelectResult'
    url: str | None = None


@dataclass
class MediaSelectResult:
    id_al: int
    favourites: int
    site_url: str
    type: 'AnilistMediaType'
    id_mal: int | None
    title_user_preferred: str
    title_native: str | None
    title_english: str | None
    synonyms: list[str]
    description: str | None
    status: 'AnilistMediaStatus | None'
    season: 'AnilistMediaSeason | None'
    season_year: int | None
    episodes: int | None
    duration: int | None
    chapters: int | None
    cover_image_extra_large: str
    cover_image_color: str | None
    popularity: int
    is_adult: bool
    genres: list[str]


@dataclass
class MediaTitleAutocompleteResult:
    id_al: int
    title_user_preferred: str
    type: 'MediaType'


@dataclass
class MediasPoolExportResult:
    id_al: int
    image: str
    favourites: int


@dataclass
class NewClientBody:
    username: str
    password: str


@dataclass
class NewCollectionBody:
    discord_id: int
    name: str


@dataclass
class NewCouponBody:
    code: str | None = None


@dataclass
class NewGameBody:
    message_id: int
    quizz_id: UUID
    answer_bananed: str | None = None


@dataclass
class NewHistoireBody:
    title: str
    text: str


@dataclass
class NewOfferingBody:
    player_discord_id: int
    chara_id_al: int
    bot_discord_id: int


@dataclass
class NewPresenceBody:
    type: Literal['PLAYING', 'LISTENING', 'WATCHING']
    name: str


@dataclass
class NewProjectionBody:
    name: str
    channel_id: int


@dataclass
class NewQuizzBody:
    channel_id: int
    description: str
    is_image: bool
    author_discord_id: int
    author_discord_username: str
    url: str | None = None


@dataclass
class NewReminderBody:
    discord_id: int
    discord_username: str
    channel_id: int
    message: str
    timestamp: datetime


@dataclass
class NewRoleBody:
    role_id: int
    emoji: str


@dataclass
class NewTradeBody:
    player_a_discord_id: int
    waifus_a_ids: list[str]
    player_b_discord_id: int
    waifus_b_ids: list[str]
    moecoins_a: int | None = None
    blood_shards_a: int | None = None
    moecoins_b: int | None = None
    blood_shards_b: int | None = None


@dataclass
class ParticipantAddBody:
    participant_username: str


@dataclass
class PlayerAddCoinsResult:
    game_mode: 'WaicolleGameMode'
    moecoins: int
    blood_shards: int
    user: 'PlayerAddCoinsResultUser'


@dataclass
class PlayerAddCoinsResultUser:
    discord_id: int
    discord_id_str: str


@dataclass
class PlayerAddCollectionResult:
    player: 'PlayerAddCollectionResultPlayer'
    collection: 'PlayerAddCollectionResultCollection'


@dataclass
class PlayerAddCollectionResultCollection:
    id: UUID
    name: str


@dataclass
class PlayerAddCollectionResultPlayer:
    id: UUID


@dataclass
class PlayerAddMediaResult:
    player: 'PlayerAddMediaResultPlayer'
    media: 'PlayerAddMediaResultMedia'


@dataclass
class PlayerAddMediaResultMedia:
    id_al: int
    type: 'AnilistMediaType'
    title_user_preferred: str


@dataclass
class PlayerAddMediaResultPlayer:
    id: UUID


@dataclass
class PlayerAddStaffResult:
    player: 'PlayerAddStaffResultPlayer'
    staff: 'PlayerAddStaffResultStaff'


@dataclass
class PlayerAddStaffResultPlayer:
    id: UUID


@dataclass
class PlayerAddStaffResultStaff:
    id_al: int
    name_user_preferred: str
    name_native: str | None


@dataclass
class PlayerCollectionStatsResult:
    collection: 'PlayerCollectionStatsResultCollection'
    nb_charas: int
    nb_owned: int


@dataclass
class PlayerCollectionStatsResultCollection:
    id: UUID
    name: str
    author: 'PlayerCollectionStatsResultCollectionAuthor'
    medias: list['PlayerCollectionStatsResultCollectionMedias']
    staffs: list['PlayerCollectionStatsResultCollectionStaffs']


@dataclass
class PlayerCollectionStatsResultCollectionAuthor:
    user: 'PlayerCollectionStatsResultCollectionAuthorUser'


@dataclass
class PlayerCollectionStatsResultCollectionAuthorUser:
    discord_id: int
    discord_id_str: str


@dataclass
class PlayerCollectionStatsResultCollectionMedias:
    type: 'AnilistMediaType'
    id_al: int
    title_user_preferred: str


@dataclass
class PlayerCollectionStatsResultCollectionStaffs:
    id_al: int
    name_user_preferred: str
    name_native: str | None


@dataclass
class PlayerGetByUserResult:
    game_mode: 'WaicolleGameMode'
    moecoins: int
    blood_shards: int
    user: 'PlayerGetByUserResultUser'


@dataclass
class PlayerGetByUserResultUser:
    discord_id: int
    discord_id_str: str


@dataclass
class PlayerMediaStatsResult:
    media: 'PlayerMediaStatsResultMedia'
    nb_charas: int
    nb_owned: int


@dataclass
class PlayerMediaStatsResultMedia:
    type: 'AnilistMediaType'
    id_al: int
    title_user_preferred: str


@dataclass
class PlayerMergeResult:
    id: UUID


@dataclass
class PlayerRemoveCollectionResult:
    id: UUID


@dataclass
class PlayerRemoveMediaResult:
    id: UUID


@dataclass
class PlayerRemoveStaffResult:
    id: UUID


@dataclass
class PlayerSelectAllResultUser:
    discord_id: int
    discord_id_str: str


@dataclass
class PlayerSelectResult:
    game_mode: 'WaicolleGameMode'
    moecoins: int
    blood_shards: int
    user: 'PlayerSelectAllResultUser'


@dataclass
class PlayerStaffStatsResult:
    staff: 'PlayerStaffStatsResultStaff'
    nb_charas: int
    nb_owned: int


@dataclass
class PlayerStaffStatsResultStaff:
    id_al: int
    name_user_preferred: str
    name_native: str | None


@dataclass
class PlayerTrackReversedResult:
    waifu: 'WaifuSelectResult'
    trackers_not_owners: list['PlayerSelectResult']
    locked: list['WaifuSelectResult']


@dataclass
class PlayerTrackedItemsResult:
    tracked_medias: list['PlayerTrackedItemsResultTrackedMedias']
    tracked_staffs: list['PlayerTrackedItemsResultTrackedStaffs']
    tracked_collections: list['PlayerTrackedItemsResultTrackedCollections']


@dataclass
class PlayerTrackedItemsResultTrackedCollections:
    id: UUID


@dataclass
class PlayerTrackedItemsResultTrackedMedias:
    id_al: int


@dataclass
class PlayerTrackedItemsResultTrackedStaffs:
    id_al: int


@dataclass
class PotAddResult:
    amount: float
    count: int


@dataclass
class PotGetByUserResult:
    amount: float
    count: int


@dataclass
class PresenceDeleteByIdResult:
    id: UUID


@dataclass
class PresenceInsertResult:
    id: UUID


@dataclass
class PresenceSelectAllResult:
    id: UUID
    type: 'PresencePresenceType'
    name: str


@dataclass
class ProfileGetByDiscordIdResultUser:
    discord_id: int
    discord_id_str: str


@dataclass
class ProfileSearchResult:
    full_name: str | None
    photo: str | None
    promotion: str | None
    telephone: str | None
    user: 'ProfileGetByDiscordIdResultUser'


@dataclass
class ProjoAddEventResult:
    id: UUID


@dataclass
class ProjoAddExternalMediaBody:
    title: str


@dataclass
class ProjoAddExternalMediaResult:
    id: UUID


@dataclass
class ProjoAddMediaResult:
    id: UUID


@dataclass
class ProjoDeleteResult:
    id: UUID


@dataclass
class ProjoDeleteUpcomingEventsResult:
    id: UUID


@dataclass
class ProjoInsertResult:
    id: UUID


@dataclass
class ProjoParticipantAddResult:
    id: UUID


@dataclass
class ProjoParticipantRemoveResult:
    id: UUID


@dataclass
class ProjoRemoveExternalMediaResult:
    id: UUID


@dataclass
class ProjoRemoveMediaResult:
    id: UUID


@dataclass
class ProjoSelectResult:
    medias: list['ProjoSelectResultMedias']
    external_medias: list['ProjoSelectResultExternalMedias']
    participants: list['ProjoSelectResultParticipants']
    guild_events: list['ProjoSelectResultGuildEvents']
    status: 'ProjectionStatus'
    name: str
    message_id_str: str | None
    message_id: int | None
    channel_id_str: str
    channel_id: int
    id: UUID


@dataclass
class ProjoSelectResultExternalMedias:
    id: UUID
    title: str
    added_alias: datetime | None = Field(alias='@added')


@dataclass
class ProjoSelectResultGuildEvents:
    id: UUID
    discord_id: int
    description: str | None
    discord_id_str: str
    end_time: datetime
    image: str | None
    location: str | None
    name: str
    start_time: datetime
    url: str | None


@dataclass
class ProjoSelectResultMedias:
    id_al: int
    title_user_preferred: str
    added_alias: datetime | None = Field(alias='@added')


@dataclass
class ProjoSelectResultParticipants:
    id: UUID
    discord_id: int
    discord_id_str: str
    discord_username: str


@dataclass
class ProjoUpdateMessageIdResult:
    id: UUID


@dataclass
class ProjoUpdateNameResult:
    id: UUID


@dataclass
class ProjoUpdateStatusResult:
    id: UUID


@dataclass
class QuizzDeleteByIdResult:
    id: UUID


@dataclass
class QuizzGetByIdResult:
    id: UUID
    channel_id: int
    channel_id_str: str
    description: str | None
    url: str | None
    is_image: bool
    answer: str | None
    answer_source: str | None
    submitted_at: datetime
    hikaried: bool | None
    author: 'QuizzGetByIdResultAuthor'


@dataclass
class QuizzGetByIdResultAuthor:
    discord_id: int
    discord_id_str: str


@dataclass
class QuizzGetOldestResult:
    id: UUID
    channel_id: int
    channel_id_str: str
    description: str | None
    url: str | None
    is_image: bool
    answer: str | None
    answer_source: str | None
    submitted_at: datetime
    hikaried: bool | None
    author: 'QuizzGetOldestResultAuthor'


@dataclass
class QuizzGetOldestResultAuthor:
    discord_id: int
    discord_id_str: str


@dataclass
class QuizzInsertResult:
    id: UUID


@dataclass
class QuizzSetAnswerResult:
    id: UUID


@dataclass
class Rank:
    tier: int
    wc_rank: str
    min_favourites: int
    blood_shards: int
    blood_price: int
    color: int
    emoji: str


@dataclass
class ReminderDeleteByIdResult:
    id: UUID


@dataclass
class ReminderInsertSelectResult:
    id: UUID
    channel_id: int
    channel_id_str: str
    message: str
    timestamp: datetime
    user: 'ReminderInsertSelectResultUser'


@dataclass
class ReminderInsertSelectResultUser:
    discord_id: int
    discord_id_str: str


@dataclass
class ReminderSelectAllResult:
    id: UUID
    channel_id: int
    channel_id_str: str
    message: str
    timestamp: datetime
    user: 'ReminderSelectAllResultUser'


@dataclass
class ReminderSelectAllResultUser:
    discord_id: int
    discord_id_str: str


@dataclass
class ReorderWaifuBody:
    custom_position: Literal['DEFAULT', 'LEFT_OF', 'RIGHT_OF'] | None = None
    other_waifu_id: UUID | None = None


@dataclass
class RerollBody:
    player_discord_id: int
    waifus_ids: list[str]
    bot_discord_id: int


@dataclass
class RerollResponse:
    obtained: list['WaifuSelectResult']
    nanascends: list['WaifuSelectResult']


@dataclass
class RoleDeleteByRoleIdResult:
    id: UUID


@dataclass
class RoleInsertSelectResult:
    role_id: int
    role_id_str: str
    emoji: str


@dataclass
class RoleSelectAllResult:
    role_id: int
    role_id_str: str
    emoji: str


@dataclass
class RollData:
    id: str
    name: str
    price: int


@dataclass
class SetGameBananedAnswerBody:
    answer_bananed: str | None = None


@dataclass
class SetProjectionMessageIdBody:
    message_id: int


@dataclass
class SetProjectionNameBody:
    name: str


@dataclass
class SetProjectionStatusBody:
    status: Literal['ONGOING', 'COMPLETED']


@dataclass
class SetQuizzAnswerBody:
    answer: str | None = None
    answer_source: str | None = None


@dataclass
class SettingsMergeResult:
    id: UUID


@dataclass
class SettingsSelectAllResult:
    key: str
    value: str


@dataclass
class StaffAlbumResult:
    total: int
    owned: int
    staff: 'StaffSelectResult'
    url: str | None = None


@dataclass
class StaffNameAutocompleteResult:
    id_al: int
    name_user_preferred: str
    name_native: str | None = None


@dataclass
class StaffSelectResult:
    id_al: int
    favourites: int
    site_url: str
    name_user_preferred: str
    name_native: str | None
    name_alternative: list[str]
    description: str | None
    image_large: str
    gender: str | None
    age: int | None
    date_of_birth_year: int | None
    date_of_birth_month: int | None
    date_of_birth_day: int | None
    date_of_death_year: int | None
    date_of_death_month: int | None
    date_of_death_day: int | None


@dataclass
class TradeDeleteResult:
    id: UUID


@dataclass
class TradeSelectResult:
    id: UUID
    player_a: 'TradeSelectResultPlayerA'
    waifus_a: list['TradeSelectResultWaifusA']
    moecoins_a: int
    blood_shards_a: int
    player_b: 'TradeSelectResultPlayerB'
    waifus_b: list['TradeSelectResultWaifusB']
    moecoins_b: int
    blood_shards_b: int


@dataclass
class TradeSelectResultPlayerA:
    user: 'TradeSelectResultPlayerAUser'


@dataclass
class TradeSelectResultPlayerAUser:
    discord_id: int
    discord_id_str: str


@dataclass
class TradeSelectResultPlayerB:
    user: 'TradeSelectResultPlayerBUser'


@dataclass
class TradeSelectResultPlayerBUser:
    discord_id: int
    discord_id_str: str


@dataclass
class TradeSelectResultWaifusA:
    id: UUID
    timestamp: datetime
    level: int
    locked: bool
    trade_locked: bool
    blooded: bool
    nanaed: bool
    custom_image: str | None
    custom_name: str | None
    custom_collage: bool
    custom_position: 'WaicolleCollagePosition'
    character: 'TradeSelectResultWaifusACharacter'
    owner: 'TradeSelectResultWaifusAOwner'
    original_owner: 'TradeSelectResultWaifusAOriginalOwner | None'
    custom_position_waifu: 'TradeSelectResultWaifusACustomPositionWaifu | None'


@dataclass
class TradeSelectResultWaifusACharacter:
    id_al: int


@dataclass
class TradeSelectResultWaifusACustomPositionWaifu:
    id: UUID


@dataclass
class TradeSelectResultWaifusAOriginalOwner:
    user: 'TradeSelectResultWaifusAOriginalOwnerUser'


@dataclass
class TradeSelectResultWaifusAOriginalOwnerUser:
    discord_id: int
    discord_id_str: str


@dataclass
class TradeSelectResultWaifusAOwner:
    user: 'TradeSelectResultWaifusAOwnerUser'


@dataclass
class TradeSelectResultWaifusAOwnerUser:
    discord_id: int
    discord_id_str: str


@dataclass
class TradeSelectResultWaifusB:
    id: UUID
    timestamp: datetime
    level: int
    locked: bool
    trade_locked: bool
    blooded: bool
    nanaed: bool
    custom_image: str | None
    custom_name: str | None
    custom_collage: bool
    custom_position: 'WaicolleCollagePosition'
    character: 'TradeSelectResultWaifusBCharacter'
    owner: 'TradeSelectResultWaifusBOwner'
    original_owner: 'TradeSelectResultWaifusBOriginalOwner | None'
    custom_position_waifu: 'TradeSelectResultWaifusBCustomPositionWaifu | None'


@dataclass
class TradeSelectResultWaifusBCharacter:
    id_al: int


@dataclass
class TradeSelectResultWaifusBCustomPositionWaifu:
    id: UUID


@dataclass
class TradeSelectResultWaifusBOriginalOwner:
    user: 'TradeSelectResultWaifusBOriginalOwnerUser'


@dataclass
class TradeSelectResultWaifusBOriginalOwnerUser:
    discord_id: int
    discord_id_str: str


@dataclass
class TradeSelectResultWaifusBOwner:
    user: 'TradeSelectResultWaifusBOwnerUser'


@dataclass
class TradeSelectResultWaifusBOwnerUser:
    discord_id: int
    discord_id_str: str


@dataclass
class UpdateAMQSettingsBody:
    settings: str


@dataclass
class UpsertAMQAccountBody:
    discord_username: str
    username: str


@dataclass
class UpsertAnilistAccountBody:
    discord_username: str
    service: Literal['ANILIST', 'MYANIMELIST']
    username: str


@dataclass
class UpsertDiscordAccountBodyItem:
    discord_id: int
    discord_username: str


@dataclass
class UpsertGuildEventBody:
    name: str
    start_time: datetime
    end_time: datetime
    organizer_id: int
    organizer_username: str
    description: str | None = None
    location: str | None = None
    image: str | None = None
    url: str | None = None


@dataclass
class UpsertPlayerBody:
    discord_username: str
    game_mode: Literal['WAIFU', 'HUSBANDO', 'ALL']


@dataclass
class UpsertProfileBody:
    discord_username: str
    full_name: str | None = None
    photo: str | None = None
    promotion: str | None = None
    telephone: str | None = None


@dataclass
class UpsertUserCalendarBody:
    discord_username: str
    ics: str


@dataclass
class UserBulkMergeResult:
    id: UUID


@dataclass
class UserCalendarDeleteResult:
    id: UUID


@dataclass
class UserCalendarMergeResult:
    id: UUID


@dataclass
class UserCalendarSelectAllResult:
    id: UUID
    ics: str
    user: 'UserCalendarSelectAllResultUser'


@dataclass
class UserCalendarSelectAllResultUser:
    id: UUID
    discord_id: int
    discord_id_str: str
    discord_username: str


@dataclass
class UserCalendarSelectResult:
    id: UUID
    ics: str
    user: 'UserCalendarSelectResultUser'


@dataclass
class UserCalendarSelectResultUser:
    id: UUID
    discord_id: int
    discord_id_str: str
    discord_username: str


@dataclass
class UserSelectResult:
    discord_id: int
    discord_id_str: str
    discord_username: str


@dataclass
class ValidationError:
    loc: list[str | int]
    msg: str
    type: str


@dataclass
class WaifuBulkUpdateResult:
    id: UUID
    timestamp: datetime
    level: int
    locked: bool
    trade_locked: bool
    blooded: bool
    nanaed: bool
    custom_image: str | None
    custom_name: str | None
    custom_collage: bool
    custom_position: 'WaicolleCollagePosition'
    character: 'WaifuBulkUpdateResultCharacter'
    owner: 'WaifuBulkUpdateResultOwner'
    original_owner: 'WaifuBulkUpdateResultOriginalOwner | None'
    custom_position_waifu: 'WaifuBulkUpdateResultCustomPositionWaifu | None'


@dataclass
class WaifuBulkUpdateResultCharacter:
    id_al: int


@dataclass
class WaifuBulkUpdateResultCustomPositionWaifu:
    id: UUID


@dataclass
class WaifuBulkUpdateResultOriginalOwner:
    user: 'WaifuBulkUpdateResultOriginalOwnerUser'


@dataclass
class WaifuBulkUpdateResultOriginalOwnerUser:
    discord_id: int
    discord_id_str: str


@dataclass
class WaifuBulkUpdateResultOwner:
    user: 'WaifuBulkUpdateResultOwnerUser'


@dataclass
class WaifuBulkUpdateResultOwnerUser:
    discord_id: int
    discord_id_str: str


@dataclass
class WaifuExportResult:
    players: list['WaifuExportResultPlayers']
    waifus: list['WaifuExportResultWaifus']
    charas: list['WaifuExportResultCharas']


@dataclass
class WaifuExportResultCharas:
    id_al: int
    image: str
    favourites: int


@dataclass
class WaifuExportResultPlayers:
    discord_id: str
    discord_username: str
    tracked: list[int]


@dataclass
class WaifuExportResultWaifus:
    id: UUID
    character_id: int
    owner_discord_id: str
    original_owner_discord_id: str | None
    timestamp: datetime
    level: int
    locked: bool
    nanaed: bool
    blooded: bool
    trade_locked: bool


@dataclass
class WaifuReplaceCustomPositionResult:
    id: UUID


@dataclass
class WaifuSelectResult:
    id: UUID
    timestamp: datetime
    level: int
    locked: bool
    trade_locked: bool
    blooded: bool
    nanaed: bool
    custom_image: str | None
    custom_name: str | None
    custom_collage: bool
    custom_position: 'WaicolleCollagePosition'
    character: 'WaifuSelectResultCharacter'
    owner: 'WaifuSelectResultOwner'
    original_owner: 'WaifuSelectResultOriginalOwner | None'
    custom_position_waifu: 'WaifuSelectResultCustomPositionWaifu | None'


@dataclass
class WaifuSelectResultCharacter:
    id_al: int


@dataclass
class WaifuSelectResultCustomPositionWaifu:
    id: UUID


@dataclass
class WaifuSelectResultOriginalOwner:
    user: 'WaifuSelectResultOriginalOwnerUser'


@dataclass
class WaifuSelectResultOriginalOwnerUser:
    discord_id: int
    discord_id_str: str


@dataclass
class WaifuSelectResultOwner:
    user: 'WaifuSelectResultOwnerUser'


@dataclass
class WaifuSelectResultOwnerUser:
    discord_id: int
    discord_id_str: str


@dataclass
class WaifuUpdateCustomImageNameResult:
    id: UUID


@dataclass
class WhoamiResponse:
    id: UUID
    username: str
