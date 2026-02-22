from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AnilistCharacterRole(str, Enum):
    BACKGROUND = 'BACKGROUND'
    MAIN = 'MAIN'
    SUPPORTING = 'SUPPORTING'


class AnilistEntryStatus(str, Enum):
    COMPLETED = 'COMPLETED'
    CURRENT = 'CURRENT'
    DROPPED = 'DROPPED'
    PAUSED = 'PAUSED'
    PLANNING = 'PLANNING'
    REPEATING = 'REPEATING'


class AnilistMediaSeason(str, Enum):
    FALL = 'FALL'
    SPRING = 'SPRING'
    SUMMER = 'SUMMER'
    WINTER = 'WINTER'


class AnilistMediaStatus(str, Enum):
    CANCELLED = 'CANCELLED'
    FINISHED = 'FINISHED'
    HIATUS = 'HIATUS'
    NOT_YET_RELEASED = 'NOT_YET_RELEASED'
    RELEASING = 'RELEASING'


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
    LISTENING = 'LISTENING'
    PLAYING = 'PLAYING'
    WATCHING = 'WATCHING'


class ProjectionStatus(str, Enum):
    COMPLETED = 'COMPLETED'
    ONGOING = 'ONGOING'


class QuizzStatus(str, Enum):
    ENDED = 'ENDED'
    STARTED = 'STARTED'


class WaicolleCollagePosition(str, Enum):
    DEFAULT = 'DEFAULT'
    LEFT_OF = 'LEFT_OF'
    RIGHT_OF = 'RIGHT_OF'


class WaicolleGameMode(str, Enum):
    ALL = 'ALL'
    HUSBANDO = 'HUSBANDO'
    WAIFU = 'WAIFU'


class WaicolleRank(str, Enum):
    A = 'A'
    B = 'B'
    C = 'C'
    D = 'D'
    E = 'E'
    S = 'S'


class AccountMergeResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class AccountSelectAllResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    service: 'AnilistService'
    user: 'AccountSelectAllResultUser'
    username: str


class AccountSelectAllResultUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class AccountSelectResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'AccountSelectResultUser'
    username: str


class AccountSelectResultUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class AddPlayerCoinsBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    moecoins: int | None = None
    blood_shards: int | None = None


class Body_client_login(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    username: str
    password: Any
    grant_type: str | None = None
    scope: str | None = None
    client_id: str | None = None
    client_secret: str | None = None


class BulkUpdateMessageNoindexBodyItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    message_id: str
    noindex: str


class BulkUpdateWaifusBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ids: list[str]
    locked: bool | None = None
    blooded: bool | None = None
    nanaed: bool | None = None
    custom_collage: bool | None = None


class CEdgeSelectFilterCharaResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    character_role: 'AnilistCharacterRole'
    media: 'CEdgeSelectFilterCharaResultMedia'
    voice_actors: list['CEdgeSelectFilterCharaResultVoiceActors']


class CEdgeSelectFilterCharaResultMedia(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    chapters: int | None
    cover_image_color: str | None
    cover_image_extra_large: str
    description: str | None
    duration: int | None
    episodes: int | None
    favourites: int
    genres: list[str]
    id_al: int
    id_mal: int | None
    is_adult: bool
    popularity: int
    season: 'AnilistMediaSeason | None'
    season_year: int | None
    site_url: str
    status: 'AnilistMediaStatus | None'
    synonyms: list[str]
    title_english: str | None
    title_native: str | None
    title_user_preferred: str
    type: 'AnilistMediaType'


class CEdgeSelectFilterCharaResultVoiceActors(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    age: int | None
    date_of_birth_day: int | None
    date_of_birth_month: int | None
    date_of_birth_year: int | None
    date_of_death_day: int | None
    date_of_death_month: int | None
    date_of_death_year: int | None
    description: str | None
    favourites: int
    gender: str | None
    id_al: int
    image_large: str
    name_alternative: list[str]
    name_native: str | None
    name_user_preferred: str
    site_url: str


class CEdgeSelectFilterMediaResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    character: 'CEdgeSelectFilterMediaResultCharacter'
    character_role: 'AnilistCharacterRole'
    voice_actors: list['CEdgeSelectFilterMediaResultVoiceActors']


class CEdgeSelectFilterMediaResultCharacter(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    age: str | None
    date_of_birth_day: int | None
    date_of_birth_month: int | None
    date_of_birth_year: int | None
    description: str | None
    favourites: int
    fuzzy_gender: str | None
    gender: str | None
    id_al: int
    image_large: str
    name_alternative: list[str]
    name_alternative_spoiler: list[str]
    name_native: str | None
    name_user_preferred: str
    rank: 'WaicolleRank'
    site_url: str


class CEdgeSelectFilterMediaResultVoiceActors(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    age: int | None
    date_of_birth_day: int | None
    date_of_birth_month: int | None
    date_of_birth_year: int | None
    date_of_death_day: int | None
    date_of_death_month: int | None
    date_of_death_year: int | None
    description: str | None
    favourites: int
    gender: str | None
    id_al: int
    image_large: str
    name_alternative: list[str]
    name_native: str | None
    name_user_preferred: str
    site_url: str


class CEdgeSelectFilterStaffResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    character: 'CEdgeSelectFilterStaffResultCharacter'
    character_role: 'AnilistCharacterRole'
    media: 'CEdgeSelectFilterStaffResultMedia'


class CEdgeSelectFilterStaffResultCharacter(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    age: str | None
    date_of_birth_day: int | None
    date_of_birth_month: int | None
    date_of_birth_year: int | None
    description: str | None
    favourites: int
    fuzzy_gender: str | None
    gender: str | None
    id_al: int
    image_large: str
    name_alternative: list[str]
    name_alternative_spoiler: list[str]
    name_native: str | None
    name_user_preferred: str
    rank: 'WaicolleRank'
    site_url: str


class CEdgeSelectFilterStaffResultMedia(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    chapters: int | None
    cover_image_color: str | None
    cover_image_extra_large: str
    description: str | None
    duration: int | None
    episodes: int | None
    favourites: int
    genres: list[str]
    id_al: int
    id_mal: int | None
    is_adult: bool
    popularity: int
    season: 'AnilistMediaSeason | None'
    season_year: int | None
    site_url: str
    status: 'AnilistMediaStatus | None'
    synonyms: list[str]
    title_english: str | None
    title_native: str | None
    title_user_preferred: str
    type: 'AnilistMediaType'


class CharaNameAutocompleteResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int
    name_user_preferred: str
    name_native: str | None = None


class CharaSelectResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    age: str | None
    date_of_birth_day: int | None
    date_of_birth_month: int | None
    date_of_birth_year: int | None
    description: str | None
    favourites: int
    fuzzy_gender: str | None
    gender: str | None
    id_al: int
    image_large: str
    name_alternative: list[str]
    name_alternative_spoiler: list[str]
    name_native: str | None
    name_user_preferred: str
    rank: 'WaicolleRank'
    site_url: str


class ClientInsertResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class CollageResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    total: int
    url: str | None = None


class CollectPotBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_username: str
    amount: float


class CollectionAddMediaResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    collection: 'CollectionAddMediaResultCollection'
    media: 'CollectionAddMediaResultMedia'


class CollectionAddMediaResultCollection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    name: str


class CollectionAddMediaResultMedia(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int
    title_user_preferred: str
    type: 'AnilistMediaType'


class CollectionAddStaffResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    collection: 'CollectionAddStaffResultCollection'
    staff: 'CollectionAddStaffResultStaff'


class CollectionAddStaffResultCollection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    name: str


class CollectionAddStaffResultStaff(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int
    name_native: str | None
    name_user_preferred: str


class CollectionAlbumResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    total: int
    owned: int
    collection: 'CollectionGetByIdResult'
    url: str | None = None


class CollectionDeleteResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class CollectionGetByIdResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    author: 'CollectionGetByIdResultAuthor'
    characters_ids_al: list[int]
    id: UUID
    medias_ids_al: list[int]
    name: str
    staffs_ids_al: list[int]


class CollectionGetByIdResultAuthor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'CollectionGetByIdResultAuthorUser'


class CollectionGetByIdResultAuthorUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class CollectionInsertResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    author: 'CollectionInsertResultAuthor'
    id: UUID
    name: str


class CollectionInsertResultAuthor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'CollectionInsertResultAuthorUser'


class CollectionInsertResultAuthorUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class CollectionNameAutocompleteResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    name: str
    author_discord_id: str


class CollectionRemoveMediaResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class CollectionRemoveStaffResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class CommitTradeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    received: list['WaifuSelectResult']
    offered: list['WaifuSelectResult']


class CouponDeleteResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class CouponInsertResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    code: str


class CouponSelectAllResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    claimed_by: list['CouponSelectAllResultClaimedBy']
    code: str


class CouponSelectAllResultClaimedBy(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'CouponSelectAllResultClaimedByUser'


class CouponSelectAllResultClaimedByUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class CustomizeWaifuBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    custom_image: str | None = None
    custom_name: str | None = None


class DonatePlayerCoinsBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    moecoins: int


class EndGameBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    winner_discord_id: str
    winner_discord_username: str


class EntrySelectAllResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    account: 'EntrySelectAllResultAccount'
    media: 'EntrySelectAllResultMedia'
    progress: int
    score: float
    status: 'AnilistEntryStatus'


class EntrySelectAllResultAccount(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'EntrySelectAllResultAccountUser'


class EntrySelectAllResultAccountUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class EntrySelectAllResultMedia(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int


class EntrySelectFilterMediaResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    account: 'EntrySelectFilterMediaResultAccount'
    progress: int
    score: float
    status: 'AnilistEntryStatus'


class EntrySelectFilterMediaResultAccount(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'EntrySelectFilterMediaResultAccountUser'


class EntrySelectFilterMediaResultAccountUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class GameDeleteByMessageIdResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class GameEndResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ended_at: datetime | None
    id: UUID
    message_id: str
    quizz: 'GameEndResultQuizz'
    started_at: datetime
    status: 'QuizzStatus'
    winner: 'GameEndResultWinner | None'


class GameEndResultQuizz(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    answer: str | None
    attachment_url: str | None
    author: 'GameEndResultQuizzAuthor'
    channel_id: str
    hints: list[str] | None
    id: UUID
    question: str | None
    submitted_at: datetime


class GameEndResultQuizzAuthor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class GameEndResultWinner(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class GameGetByIdResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ended_at: datetime | None
    id: UUID
    message_id: str
    quizz: 'GameGetByIdResultQuizz'
    started_at: datetime
    status: 'QuizzStatus'
    winner: 'GameGetByIdResultWinner | None'


class GameGetByIdResultQuizz(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    answer: str | None
    attachment_url: str | None
    author: 'GameGetByIdResultQuizzAuthor'
    channel_id: str
    hints: list[str] | None
    id: UUID
    question: str | None
    submitted_at: datetime


class GameGetByIdResultQuizzAuthor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class GameGetByIdResultWinner(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class GameGetCurrentResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ended_at: datetime | None
    id: UUID
    message_id: str
    quizz: 'GameGetCurrentResultQuizz'
    started_at: datetime
    status: 'QuizzStatus'
    winner: 'GameGetCurrentResultWinner | None'


class GameGetCurrentResultQuizz(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    answer: str | None
    attachment_url: str | None
    author: 'GameGetCurrentResultQuizzAuthor'
    channel_id: str
    hints: list[str] | None
    id: UUID
    question: str | None
    submitted_at: datetime


class GameGetCurrentResultQuizzAuthor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class GameGetCurrentResultWinner(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class GameGetLastResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ended_at: datetime | None
    id: UUID
    message_id: str
    quizz: 'GameGetLastResultQuizz'
    started_at: datetime
    status: 'QuizzStatus'
    winner: 'GameGetLastResultWinner | None'


class GameGetLastResultQuizz(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    answer: str | None
    attachment_url: str | None
    author: 'GameGetLastResultQuizzAuthor'
    channel_id: str
    hints: list[str] | None
    id: UUID
    question: str | None
    submitted_at: datetime


class GameGetLastResultQuizzAuthor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class GameGetLastResultWinner(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class GameNewResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class GameSelectResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ended_at: datetime | None
    id: UUID
    message_id: str
    quizz: 'GameSelectResultQuizz'
    started_at: datetime
    status: 'QuizzStatus'
    winner: 'GameSelectResultWinner | None'


class GameSelectResultQuizz(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    answer: str | None
    attachment_url: str | None
    author: 'GameSelectResultQuizzAuthor'
    channel_id: str
    hints: list[str] | None
    id: UUID
    question: str | None
    submitted_at: datetime


class GameSelectResultQuizzAuthor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class GameSelectResultWinner(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class GuildEventDeleteResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    client: 'GuildEventDeleteResultClient'
    description: str | None
    discord_id: str
    end_time: datetime
    id: UUID
    image: str | None
    location: str | None
    name: str
    organizer: 'GuildEventDeleteResultOrganizer'
    participants: list['GuildEventDeleteResultParticipants']
    projection: 'GuildEventDeleteResultProjection | None'
    start_time: datetime
    url: str | None


class GuildEventDeleteResultClient(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    password_hash: str
    username: str


class GuildEventDeleteResultOrganizer(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    age_verified: bool
    discord_id: str
    discord_username: str
    id: UUID


class GuildEventDeleteResultParticipants(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    age_verified: bool
    discord_id: str
    discord_username: str
    id: UUID


class GuildEventDeleteResultProjection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    channel_id: str
    id: UUID
    message_id: str | None
    name: str
    status: 'ProjectionStatus'


class GuildEventMergeResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    client: 'GuildEventMergeResultClient'
    description: str | None
    discord_id: str
    end_time: datetime
    id: UUID
    image: str | None
    location: str | None
    name: str
    organizer: 'GuildEventMergeResultOrganizer'
    participants: list['GuildEventMergeResultParticipants']
    projection: 'GuildEventMergeResultProjection | None'
    start_time: datetime
    url: str | None


class GuildEventMergeResultClient(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    password_hash: str
    username: str


class GuildEventMergeResultOrganizer(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    age_verified: bool
    discord_id: str
    discord_username: str
    id: UUID


class GuildEventMergeResultParticipants(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    age_verified: bool
    discord_id: str
    discord_username: str
    id: UUID


class GuildEventMergeResultProjection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    channel_id: str
    id: UUID
    message_id: str | None
    name: str
    status: 'ProjectionStatus'


class GuildEventParticipantAddResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class GuildEventParticipantRemoveResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class GuildEventSelectResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    client: 'GuildEventSelectResultClient'
    description: str | None
    discord_id: str
    end_time: datetime
    id: UUID
    image: str | None
    location: str | None
    name: str
    organizer: 'GuildEventSelectResultOrganizer'
    participants: list['GuildEventSelectResultParticipants']
    projection: 'GuildEventSelectResultProjection | None'
    start_time: datetime
    url: str | None


class GuildEventSelectResultClient(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    password_hash: str
    username: str


class GuildEventSelectResultOrganizer(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    age_verified: bool
    discord_id: str
    discord_username: str
    id: UUID


class GuildEventSelectResultParticipants(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    age_verified: bool
    discord_id: str
    discord_username: str
    id: UUID


class GuildEventSelectResultProjection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    channel_id: str
    id: UUID
    message_id: str | None
    name: str
    status: 'ProjectionStatus'


class HTTPExceptionModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    detail: str


class HTTPValidationError(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    detail: list['ValidationError'] | None = None


class HistoireDeleteByIdResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class HistoireGetByIdResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    formatted: bool
    id: UUID
    text: str
    title: str


class HistoireInsertResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class HistoireSelectIdTitleResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    title: str


class InsertSkillBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str
    description: str
    content: str


class LoginResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    access_token: str
    token_type: str


class MediaAlbumResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    total: int
    owned: int
    media: 'MediaSelectResult'
    url: str | None = None


class MediaSelectResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    chapters: int | None
    cover_image_color: str | None
    cover_image_extra_large: str
    description: str | None
    duration: int | None
    episodes: int | None
    favourites: int
    genres: list[str]
    id_al: int
    id_mal: int | None
    is_adult: bool
    popularity: int
    season: 'AnilistMediaSeason | None'
    season_year: int | None
    site_url: str
    status: 'AnilistMediaStatus | None'
    synonyms: list[str]
    title_english: str | None
    title_native: str | None
    title_user_preferred: str
    type: 'AnilistMediaType'


class MediaTitleAutocompleteResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int
    title_user_preferred: str
    type: 'MediaType'


class MediasPoolExportResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    favourites: int
    id_al: int
    image: str


class MessageBulkDeleteResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class MessageBulkInsertResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class MessageBulkUpdateNoindexResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class MessageMergeResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class MessageUpdateNoindexResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class MessagesRagResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    object: 'RagQueryResultObject'
    distance: float


class NewClientBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    username: str
    password: str


class NewCollectionBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str
    name: str


class NewCouponBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    code: str | None = None


class NewGameBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    message_id: str
    quizz_id: UUID


class NewHistoireBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    title: str
    text: str


class NewLootBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    player_discord_id: str
    chara_id_al: int


class NewOfferingBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    player_discord_id: str
    chara_id_al: int
    bot_discord_id: str


class NewPresenceBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: Literal['PLAYING', 'LISTENING', 'WATCHING']
    name: str


class NewProjectionBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str
    channel_id: str


class NewQuizzBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    channel_id: str
    author_discord_id: str
    author_discord_username: str
    question: str | None = None
    attachment_url: str | None = None
    answer: str | None = None
    hints: list[str] | None = None


class NewReminderBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str
    discord_username: str
    channel_id: str
    message: str
    timestamp: datetime


class NewRoleBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    role_id: str
    emoji: str


class NewTradeBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    author_discord_id: str
    received_ids: list[str]
    offeree_discord_id: str
    offered_ids: list[str]
    blood_shards: int | None = None


class ParticipantAddBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    participant_username: str


class PlayerAddCoinsResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    blood_shards: int
    frozen_at: datetime | None
    game_mode: 'WaicolleGameMode'
    id: UUID
    moecoins: int
    user: 'PlayerAddCoinsResultUser'


class PlayerAddCoinsResultUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class PlayerAddCollectionResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    collection: 'PlayerAddCollectionResultCollection'
    player: 'PlayerAddCollectionResultPlayer'


class PlayerAddCollectionResultCollection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    name: str


class PlayerAddCollectionResultPlayer(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class PlayerAddMediaResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    media: 'PlayerAddMediaResultMedia'
    player: 'PlayerAddMediaResultPlayer'


class PlayerAddMediaResultMedia(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int
    title_user_preferred: str
    type: 'AnilistMediaType'


class PlayerAddMediaResultPlayer(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class PlayerAddStaffResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    player: 'PlayerAddStaffResultPlayer'
    staff: 'PlayerAddStaffResultStaff'


class PlayerAddStaffResultPlayer(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class PlayerAddStaffResultStaff(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int
    name_native: str | None
    name_user_preferred: str


class PlayerCollectionStatsResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    collection: 'PlayerCollectionStatsResultCollection'
    nb_charas: int
    nb_owned: int


class PlayerCollectionStatsResultCollection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    author: 'PlayerCollectionStatsResultCollectionAuthor'
    id: UUID
    medias: list['PlayerCollectionStatsResultCollectionMedias']
    name: str
    staffs: list['PlayerCollectionStatsResultCollectionStaffs']


class PlayerCollectionStatsResultCollectionAuthor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'PlayerCollectionStatsResultCollectionAuthorUser'


class PlayerCollectionStatsResultCollectionAuthorUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class PlayerCollectionStatsResultCollectionMedias(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int
    title_user_preferred: str
    type: 'AnilistMediaType'


class PlayerCollectionStatsResultCollectionStaffs(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int
    name_native: str | None
    name_user_preferred: str


class PlayerFreezeResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class PlayerGetByUserResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    blood_shards: int
    frozen_at: datetime | None
    game_mode: 'WaicolleGameMode'
    id: UUID
    moecoins: int
    user: 'PlayerGetByUserResultUser'


class PlayerGetByUserResultUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    age_verified: bool
    discord_id: str


class PlayerMediaStatsResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    media: 'PlayerMediaStatsResultMedia'
    nb_charas: int
    nb_owned: int


class PlayerMediaStatsResultMedia(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int
    title_user_preferred: str
    type: 'AnilistMediaType'


class PlayerMergeResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class PlayerRemoveCollectionResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class PlayerRemoveMediaResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class PlayerRemoveStaffResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class PlayerSelectAllResultUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class PlayerSelectResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    blood_shards: int
    frozen_at: datetime | None
    game_mode: 'WaicolleGameMode'
    id: UUID
    moecoins: int
    user: 'PlayerSelectAllResultUser'


class PlayerStaffStatsResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    nb_charas: int
    nb_owned: int
    staff: 'PlayerStaffStatsResultStaff'


class PlayerStaffStatsResultStaff(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int
    name_native: str | None
    name_user_preferred: str


class PlayerTrackReversedResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    waifu: 'WaifuSelectResult'
    trackers_not_owners: list['PlayerSelectResult']
    locked: list['WaifuSelectResult']


class PlayerTrackedItemsResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    tracked_collections: list['PlayerTrackedItemsResultTrackedCollections']
    tracked_medias: list['PlayerTrackedItemsResultTrackedMedias']
    tracked_staffs: list['PlayerTrackedItemsResultTrackedStaffs']


class PlayerTrackedItemsResultTrackedCollections(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class PlayerTrackedItemsResultTrackedMedias(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int


class PlayerTrackedItemsResultTrackedStaffs(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int


class PotAddResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    amount: float
    count: int


class PotGetByUserResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    amount: float
    count: int


class PresenceDeleteByIdResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class PresenceInsertResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class PresenceSelectAllResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    name: str
    type: 'PresencePresenceType'


class ProfileGetByDiscordIdResultUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class ProfileSearchResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    birthday: datetime | None
    full_name: str | None
    graduation_year: int | None
    n7_major: str | None
    photo: str | None
    pronouns: str | None
    telephone: str | None
    user: 'ProfileGetByDiscordIdResultUser'


class ProjoAddEventResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class ProjoAddExternalMediaBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    title: str


class ProjoAddExternalMediaResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class ProjoAddMediaResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class ProjoDeleteResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class ProjoDeleteUpcomingEventsResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class ProjoInsertResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class ProjoParticipantAddResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class ProjoParticipantRemoveResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class ProjoRemoveExternalMediaResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class ProjoRemoveMediaResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class ProjoSelectResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    channel_id: str
    external_medias: list['ProjoSelectResultExternalMedias']
    guild_events: list['ProjoSelectResultGuildEvents']
    id: UUID
    legacy_events: list['ProjoSelectResultLegacyEvents']
    medias: list['ProjoSelectResultMedias']
    message_id: str | None
    name: str
    participants: list['ProjoSelectResultParticipants']
    status: 'ProjectionStatus'


class ProjoSelectResultExternalMedias(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    added_alias: datetime | None = Field(validation_alias='@added', serialization_alias='@added')
    title: str


class ProjoSelectResultGuildEvents(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    description: str | None
    discord_id: str
    end_time: datetime
    id: UUID
    image: str | None
    location: str | None
    name: str
    start_time: datetime
    url: str | None


class ProjoSelectResultLegacyEvents(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    date: datetime
    description: str
    id: UUID


class ProjoSelectResultMedias(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int
    added_alias: datetime | None = Field(validation_alias='@added', serialization_alias='@added')
    title_user_preferred: str


class ProjoSelectResultParticipants(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    age_verified: bool
    discord_id: str
    discord_username: str
    id: UUID


class ProjoUpdateMessageIdResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class ProjoUpdateNameResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class ProjoUpdateStatusResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class QuizzDeleteByIdResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class QuizzGetByIdResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    answer: str | None
    attachment_url: str | None
    author: 'QuizzGetByIdResultAuthor'
    channel_id: str
    hints: list[str] | None
    id: UUID
    question: str | None
    submitted_at: datetime


class QuizzGetByIdResultAuthor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class QuizzGetOldestResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    answer: str | None
    attachment_url: str | None
    author: 'QuizzGetOldestResultAuthor'
    channel_id: str
    hints: list[str] | None
    id: UUID
    question: str | None
    submitted_at: datetime


class QuizzGetOldestResultAuthor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class QuizzInsertResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class QuizzSetAnswerResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class RagQueryResultObject(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    context: str
    messages: list['RagQueryResultObjectMessages']


class RagQueryResultObjectMessages(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    data: Any
    channel_id: str
    timestamp: datetime


class Rank(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    tier: int
    wc_rank: str
    min_favourites: int
    blood_shards: int
    blood_price: int
    color: int
    emoji: str


class ReactionAddBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    animated: bool | None = None
    burst: bool | None = None


class ReactionDeleteResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class ReactionInsertResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class ReminderDeleteByIdResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class ReminderInsertSelectResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    channel_id: str
    id: UUID
    message: str
    timestamp: datetime
    user: 'ReminderInsertSelectResultUser'


class ReminderInsertSelectResultUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class ReminderSelectAllResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    channel_id: str
    id: UUID
    message: str
    timestamp: datetime
    user: 'ReminderSelectAllResultUser'


class ReminderSelectAllResultUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class ReorderWaifuBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    custom_position: Literal['DEFAULT', 'LEFT_OF', 'RIGHT_OF'] | None = None
    other_waifu_id: UUID | None = None


class RerollBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    player_discord_id: str
    waifus_ids: list[str]
    bot_discord_id: str


class RerollResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    obtained: list['WaifuSelectResult']
    nanascends: list['WaifuSelectResult']


class RoleDeleteByRoleIdResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class RoleInsertSelectResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    emoji: str
    role_id: str


class RoleSelectAllResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    emoji: str
    role_id: str


class RollData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str
    name: str
    price: int


class SetProjectionMessageIdBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    message_id: str


class SetProjectionNameBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str


class SetProjectionStatusBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    status: Literal['ONGOING', 'COMPLETED']


class SetQuizzAnswerBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    answer: str | None = None
    hints: list[str] | None = None


class SettingsMergeResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class SettingsSelectAllResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    key: str
    value: str


class SkillDeleteByIdResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class SkillInsertResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class SkillSelectAllResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    content: str
    description: str
    id: UUID
    name: str


class StaffAlbumResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    total: int
    owned: int
    staff: 'StaffSelectResult'
    url: str | None = None


class StaffNameAutocompleteResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int
    name_user_preferred: str
    name_native: str | None = None


class StaffSelectResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    age: int | None
    date_of_birth_day: int | None
    date_of_birth_month: int | None
    date_of_birth_year: int | None
    date_of_death_day: int | None
    date_of_death_month: int | None
    date_of_death_year: int | None
    description: str | None
    favourites: int
    gender: str | None
    id_al: int
    image_large: str
    name_alternative: list[str]
    name_native: str | None
    name_user_preferred: str
    site_url: str


class TradeDeleteResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class TradeSelectResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    author: 'TradeSelectResultAuthor'
    blood_shards: int
    completed_at: datetime | None
    created_at: datetime
    id: UUID
    offered: list['TradeSelectResultOffered']
    offeree: 'TradeSelectResultOfferee'
    received: list['TradeSelectResultReceived']


class TradeSelectResultAuthor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'TradeSelectResultAuthorUser'


class TradeSelectResultAuthorUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class TradeSelectResultOffered(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    blooded: bool
    character: 'TradeSelectResultOfferedCharacter'
    custom_collage: bool
    custom_image: str | None
    custom_name: str | None
    custom_position: 'WaicolleCollagePosition'
    custom_position_waifu: 'TradeSelectResultOfferedCustomPositionWaifu | None'
    disabled: bool
    frozen: bool
    id: UUID
    level: int
    locked: bool
    nanaed: bool
    original_owner: 'TradeSelectResultOfferedOriginalOwner | None'
    owner: 'TradeSelectResultOfferedOwner'
    timestamp: datetime
    trade_locked: bool


class TradeSelectResultOfferedCharacter(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int


class TradeSelectResultOfferedCustomPositionWaifu(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class TradeSelectResultOfferedOriginalOwner(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'TradeSelectResultOfferedOriginalOwnerUser'


class TradeSelectResultOfferedOriginalOwnerUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class TradeSelectResultOfferedOwner(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'TradeSelectResultOfferedOwnerUser'


class TradeSelectResultOfferedOwnerUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class TradeSelectResultOfferee(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'TradeSelectResultOffereeUser'


class TradeSelectResultOffereeUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class TradeSelectResultReceived(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    blooded: bool
    character: 'TradeSelectResultReceivedCharacter'
    custom_collage: bool
    custom_image: str | None
    custom_name: str | None
    custom_position: 'WaicolleCollagePosition'
    custom_position_waifu: 'TradeSelectResultReceivedCustomPositionWaifu | None'
    disabled: bool
    frozen: bool
    id: UUID
    level: int
    locked: bool
    nanaed: bool
    original_owner: 'TradeSelectResultReceivedOriginalOwner | None'
    owner: 'TradeSelectResultReceivedOwner'
    timestamp: datetime
    trade_locked: bool


class TradeSelectResultReceivedCharacter(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int


class TradeSelectResultReceivedCustomPositionWaifu(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class TradeSelectResultReceivedOriginalOwner(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'TradeSelectResultReceivedOriginalOwnerUser'


class TradeSelectResultReceivedOriginalOwnerUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class TradeSelectResultReceivedOwner(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'TradeSelectResultReceivedOwnerUser'


class TradeSelectResultReceivedOwnerUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class UpdateMessageNoindexBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    noindex: str


class UpsertAMQAccountBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_username: str
    username: str


class UpsertAnilistAccountBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_username: str
    service: Literal['ANILIST', 'MYANIMELIST']
    username: str


class UpsertDiscordAccountBodyItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str
    discord_username: str


class UpsertGuildEventBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str
    start_time: datetime
    end_time: datetime
    organizer_id: str
    organizer_username: str
    description: str | None = None
    location: str | None = None
    image: str | None = None
    url: str | None = None


class UpsertPlayerBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_username: str
    game_mode: Literal['WAIFU', 'HUSBANDO', 'ALL']


class UpsertProfileBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_username: str
    birthday: datetime | None = None
    full_name: str | None = None
    graduation_year: int | None = None
    n7_major: str | None = None
    photo: str | None = None
    pronouns: str | None = None
    telephone: str | None = None


class UpsertUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str
    discord_username: str
    age_verified: bool


class UpsertUserCalendarBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_username: str
    ics: str


class UserBulkMergeResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class UserCalendarDeleteResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class UserCalendarMergeResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class UserCalendarSelectAllResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ics: str
    id: UUID
    user: 'UserCalendarSelectAllResultUser'


class UserCalendarSelectAllResultUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    age_verified: bool
    discord_id: str
    discord_username: str
    id: UUID


class UserCalendarSelectResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ics: str
    id: UUID
    user: 'UserCalendarSelectResultUser'


class UserCalendarSelectResultUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    age_verified: bool
    discord_id: str
    discord_username: str
    id: UUID


class UserSelectResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    age_verified: bool
    discord_id: str
    discord_username: str


class UserUpsertResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class ValidationError(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    loc: list[str | int]
    msg: str
    type: str
    input: Any | None = None
    ctx: dict[str, Any] | None = None


class WaifuBulkUpdateResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    blooded: bool
    character: 'WaifuBulkUpdateResultCharacter'
    custom_collage: bool
    custom_image: str | None
    custom_name: str | None
    custom_position: 'WaicolleCollagePosition'
    custom_position_waifu: 'WaifuBulkUpdateResultCustomPositionWaifu | None'
    disabled: bool
    frozen: bool
    id: UUID
    level: int
    locked: bool
    nanaed: bool
    original_owner: 'WaifuBulkUpdateResultOriginalOwner | None'
    owner: 'WaifuBulkUpdateResultOwner'
    timestamp: datetime
    trade_locked: bool


class WaifuBulkUpdateResultCharacter(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int


class WaifuBulkUpdateResultCustomPositionWaifu(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class WaifuBulkUpdateResultOriginalOwner(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'WaifuBulkUpdateResultOriginalOwnerUser'


class WaifuBulkUpdateResultOriginalOwnerUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class WaifuBulkUpdateResultOwner(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'WaifuBulkUpdateResultOwnerUser'


class WaifuBulkUpdateResultOwnerUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class WaifuExportResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    charas: list['WaifuExportResultCharas']
    players: list['WaifuExportResultPlayers']
    waifus: list['WaifuExportResultWaifus']


class WaifuExportResultCharas(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    favourites: int
    id_al: int
    image: str


class WaifuExportResultPlayers(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str
    discord_username: str
    tracked: list[int]


class WaifuExportResultWaifus(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    blooded: bool
    character_id: int
    id: UUID
    level: int
    locked: bool
    nanaed: bool
    original_owner_discord_id: str | None
    owner_discord_id: str
    timestamp: datetime
    trade_locked: bool


class WaifuReplaceCustomPositionResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class WaifuSelectResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    blooded: bool
    character: 'WaifuSelectResultCharacter'
    custom_collage: bool
    custom_image: str | None
    custom_name: str | None
    custom_position: 'WaicolleCollagePosition'
    custom_position_waifu: 'WaifuSelectResultCustomPositionWaifu | None'
    disabled: bool
    frozen: bool
    id: UUID
    level: int
    locked: bool
    nanaed: bool
    original_owner: 'WaifuSelectResultOriginalOwner | None'
    owner: 'WaifuSelectResultOwner'
    timestamp: datetime
    trade_locked: bool


class WaifuSelectResultCharacter(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int


class WaifuSelectResultCustomPositionWaifu(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class WaifuSelectResultOriginalOwner(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'WaifuSelectResultOriginalOwnerUser'


class WaifuSelectResultOriginalOwnerUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class WaifuSelectResultOwner(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'WaifuSelectResultOwnerUser'


class WaifuSelectResultOwnerUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str


class WaifuUpdateCustomImageNameResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class WhoamiResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    username: str


class WrappedEmbed(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    title: str | None = None
    description: str | None = None
    color: int | None = None
    fields: list['WrappedEmbedField'] | None = None
    footer: str | None = None
    image_url: str | None = None


class WrappedEmbedField(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str
    value: str
    inline: bool | None = None


class WrappedResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    embeds: list['WrappedEmbed']
