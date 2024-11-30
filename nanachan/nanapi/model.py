from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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


class AccountMergeResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class AccountSelectAllResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    service: 'AnilistService'
    username: str
    user: 'AccountSelectAllResultUser'


class AccountSelectAllResultUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class AccountSelectResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    username: str
    user: 'AccountSelectResultUser'


class AccountSelectResultUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class AddPlayerCoinsBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    moecoins: int | None = None
    blood_shards: int | None = None


class Body_client_login(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    username: str
    password: str
    grant_type: str | None = None
    scope: str | None = None
    client_id: str | None = None
    client_secret: str | None = None


class BulkUpdateWaifusBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
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


class CEdgeSelectFilterCharaResultVoiceActors(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
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


class CEdgeSelectFilterMediaResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    character_role: 'AnilistCharacterRole'
    character: 'CEdgeSelectFilterMediaResultCharacter'
    voice_actors: list['CEdgeSelectFilterMediaResultVoiceActors']


class CEdgeSelectFilterMediaResultCharacter(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
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


class CEdgeSelectFilterMediaResultVoiceActors(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
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


class CEdgeSelectFilterStaffResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    character_role: 'AnilistCharacterRole'
    media: 'CEdgeSelectFilterStaffResultMedia'
    character: 'CEdgeSelectFilterStaffResultCharacter'


class CEdgeSelectFilterStaffResultCharacter(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
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


class CEdgeSelectFilterStaffResultMedia(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
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


class CharaNameAutocompleteResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int
    name_user_preferred: str
    name_native: str | None = None


class CharaSelectResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
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
    type: 'AnilistMediaType'
    title_user_preferred: str


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
    name_user_preferred: str
    name_native: str | None


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
    id: UUID
    name: str
    author: 'CollectionGetByIdResultAuthor'
    medias_ids_al: list[int]
    staffs_ids_al: list[int]
    characters_ids_al: list[int]


class CollectionGetByIdResultAuthor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'CollectionGetByIdResultAuthorUser'


class CollectionGetByIdResultAuthorUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class CollectionInsertResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    name: str
    author: 'CollectionInsertResultAuthor'


class CollectionInsertResultAuthor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'CollectionInsertResultAuthorUser'


class CollectionInsertResultAuthorUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class CollectionNameAutocompleteResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    name: str
    author_discord_id: int


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
    code: str
    claimed_by: list['CouponSelectAllResultClaimedBy']


class CouponSelectAllResultClaimedBy(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'CouponSelectAllResultClaimedByUser'


class CouponSelectAllResultClaimedByUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class CustomizeWaifuBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    custom_image: str | None = None
    custom_name: str | None = None


class DonatePlayerCoinsBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    moecoins: int


class EndGameBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    winner_discord_id: int
    winner_discord_username: str


class EntrySelectAllResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    status: 'AnilistEntryStatus'
    progress: int
    score: float
    media: 'EntrySelectAllResultMedia'
    account: 'EntrySelectAllResultAccount'


class EntrySelectAllResultAccount(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'EntrySelectAllResultAccountUser'


class EntrySelectAllResultAccountUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class EntrySelectAllResultMedia(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int


class EntrySelectFilterMediaResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    status: 'AnilistEntryStatus'
    progress: int
    score: float
    account: 'EntrySelectFilterMediaResultAccount'


class EntrySelectFilterMediaResultAccount(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'EntrySelectFilterMediaResultAccountUser'


class EntrySelectFilterMediaResultAccountUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class GameDeleteByMessageIdResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class GameEndResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    status: 'QuizzStatus'
    message_id: int
    message_id_str: str
    answer_bananed: str | None
    started_at: datetime
    ended_at: datetime | None
    winner: 'GameEndResultWinner | None'
    quizz: 'GameEndResultQuizz'


class GameEndResultQuizz(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
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


class GameEndResultQuizzAuthor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class GameEndResultWinner(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class GameGetByIdResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    status: 'QuizzStatus'
    message_id: int
    message_id_str: str
    answer_bananed: str | None
    started_at: datetime
    ended_at: datetime | None
    winner: 'GameGetByIdResultWinner | None'
    quizz: 'GameGetByIdResultQuizz'


class GameGetByIdResultQuizz(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
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


class GameGetByIdResultQuizzAuthor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class GameGetByIdResultWinner(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class GameGetCurrentResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    status: 'QuizzStatus'
    message_id: int
    message_id_str: str
    answer_bananed: str | None
    started_at: datetime
    ended_at: datetime | None
    winner: 'GameGetCurrentResultWinner | None'
    quizz: 'GameGetCurrentResultQuizz'


class GameGetCurrentResultQuizz(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
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


class GameGetCurrentResultQuizzAuthor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class GameGetCurrentResultWinner(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class GameGetLastResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    status: 'QuizzStatus'
    message_id: int
    message_id_str: str
    answer_bananed: str | None
    started_at: datetime
    ended_at: datetime | None
    winner: 'GameGetLastResultWinner | None'
    quizz: 'GameGetLastResultQuizz'


class GameGetLastResultQuizz(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
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


class GameGetLastResultQuizzAuthor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class GameGetLastResultWinner(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class GameNewResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class GameSelectResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    status: 'QuizzStatus'
    message_id: int
    message_id_str: str
    answer_bananed: str | None
    started_at: datetime
    ended_at: datetime | None
    winner: 'GameSelectResultWinner | None'
    quizz: 'GameSelectResultQuizz'


class GameSelectResultQuizz(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
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


class GameSelectResultQuizzAuthor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class GameSelectResultWinner(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class GameUpdateBananedResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class GuildEventDeleteResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
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
    organizer: 'GuildEventDeleteResultOrganizer'
    participants: list['GuildEventDeleteResultParticipants']
    projection: 'GuildEventDeleteResultProjection | None'
    client: 'GuildEventDeleteResultClient'


class GuildEventDeleteResultClient(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    password_hash: str
    username: str


class GuildEventDeleteResultOrganizer(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    discord_id: int
    discord_id_str: str
    discord_username: str


class GuildEventDeleteResultParticipants(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    discord_id: int
    discord_id_str: str
    discord_username: str


class GuildEventDeleteResultProjection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    channel_id: int
    channel_id_str: str
    message_id: int | None
    message_id_str: str | None
    name: str
    status: 'ProjectionStatus'


class GuildEventMergeResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
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
    projection: 'GuildEventMergeResultProjection | None'
    participants: list['GuildEventMergeResultParticipants']
    organizer: 'GuildEventMergeResultOrganizer'


class GuildEventMergeResultClient(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    password_hash: str
    username: str


class GuildEventMergeResultOrganizer(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    discord_id: int
    discord_id_str: str
    discord_username: str


class GuildEventMergeResultParticipants(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    discord_id: int
    discord_id_str: str
    discord_username: str


class GuildEventMergeResultProjection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    channel_id: int
    channel_id_str: str
    message_id: int | None
    message_id_str: str | None
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
    projection: 'GuildEventSelectResultProjection | None'
    participants: list['GuildEventSelectResultParticipants']
    organizer: 'GuildEventSelectResultOrganizer'


class GuildEventSelectResultClient(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    password_hash: str
    username: str


class GuildEventSelectResultOrganizer(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    discord_id: int
    discord_id_str: str
    discord_username: str


class GuildEventSelectResultParticipants(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    discord_id: int
    discord_id_str: str
    discord_username: str


class GuildEventSelectResultProjection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    channel_id: int
    channel_id_str: str
    message_id: int | None
    message_id_str: str | None
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
    id: UUID
    title: str
    text: str
    formatted: bool


class HistoireInsertResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class HistoireSelectIdTitleResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    title: str


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


class MediaTitleAutocompleteResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int
    title_user_preferred: str
    type: 'MediaType'


class MediasPoolExportResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int
    image: str
    favourites: int


class NewClientBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    username: str
    password: str


class NewCollectionBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    name: str


class NewCouponBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    code: str | None = None


class NewGameBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    message_id: int
    quizz_id: UUID
    answer_bananed: str | None = None


class NewHistoireBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    title: str
    text: str


class NewOfferingBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    player_discord_id: int
    chara_id_al: int
    bot_discord_id: int


class NewPresenceBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: Literal['PLAYING', 'LISTENING', 'WATCHING']
    name: str


class NewProjectionBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str
    channel_id: int


class NewQuizzBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    channel_id: int
    description: str
    is_image: bool
    author_discord_id: int
    author_discord_username: str
    url: str | None = None


class NewReminderBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_username: str
    channel_id: int
    message: str
    timestamp: datetime


class NewRoleBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    role_id: int
    emoji: str


class NewTradeBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    author_discord_id: int
    received_ids: list[str]
    offeree_discord_id: int
    offered_ids: list[str]
    blood_shards: int | None = None


class ParticipantAddBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    participant_username: str


class PlayerAddCoinsResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    game_mode: 'WaicolleGameMode'
    moecoins: int
    blood_shards: int
    user: 'PlayerAddCoinsResultUser'


class PlayerAddCoinsResultUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class PlayerAddCollectionResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    player: 'PlayerAddCollectionResultPlayer'
    collection: 'PlayerAddCollectionResultCollection'


class PlayerAddCollectionResultCollection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    name: str


class PlayerAddCollectionResultPlayer(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class PlayerAddMediaResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    player: 'PlayerAddMediaResultPlayer'
    media: 'PlayerAddMediaResultMedia'


class PlayerAddMediaResultMedia(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int
    type: 'AnilistMediaType'
    title_user_preferred: str


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
    name_user_preferred: str
    name_native: str | None


class PlayerCollectionStatsResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    collection: 'PlayerCollectionStatsResultCollection'
    nb_charas: int
    nb_owned: int


class PlayerCollectionStatsResultCollection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    name: str
    author: 'PlayerCollectionStatsResultCollectionAuthor'
    medias: list['PlayerCollectionStatsResultCollectionMedias']
    staffs: list['PlayerCollectionStatsResultCollectionStaffs']


class PlayerCollectionStatsResultCollectionAuthor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'PlayerCollectionStatsResultCollectionAuthorUser'


class PlayerCollectionStatsResultCollectionAuthorUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class PlayerCollectionStatsResultCollectionMedias(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: 'AnilistMediaType'
    id_al: int
    title_user_preferred: str


class PlayerCollectionStatsResultCollectionStaffs(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int
    name_user_preferred: str
    name_native: str | None


class PlayerGetByUserResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    game_mode: 'WaicolleGameMode'
    moecoins: int
    blood_shards: int
    user: 'PlayerGetByUserResultUser'


class PlayerGetByUserResultUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class PlayerMediaStatsResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    media: 'PlayerMediaStatsResultMedia'
    nb_charas: int
    nb_owned: int


class PlayerMediaStatsResultMedia(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: 'AnilistMediaType'
    id_al: int
    title_user_preferred: str


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
    discord_id: int
    discord_id_str: str


class PlayerSelectResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    game_mode: 'WaicolleGameMode'
    moecoins: int
    blood_shards: int
    user: 'PlayerSelectAllResultUser'


class PlayerStaffStatsResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    staff: 'PlayerStaffStatsResultStaff'
    nb_charas: int
    nb_owned: int


class PlayerStaffStatsResultStaff(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int
    name_user_preferred: str
    name_native: str | None


class PlayerTrackReversedResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    waifu: 'WaifuSelectResult'
    trackers_not_owners: list['PlayerSelectResult']
    locked: list['WaifuSelectResult']


class PlayerTrackedItemsResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    tracked_medias: list['PlayerTrackedItemsResultTrackedMedias']
    tracked_staffs: list['PlayerTrackedItemsResultTrackedStaffs']
    tracked_collections: list['PlayerTrackedItemsResultTrackedCollections']


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
    type: 'PresencePresenceType'
    name: str


class ProfileGetByDiscordIdResultUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class ProfileSearchResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    full_name: str | None
    photo: str | None
    promotion: str | None
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


class ProjoSelectResultExternalMedias(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    title: str
    added_alias: datetime | None = Field(validation_alias='@added', serialization_alias='@added')


class ProjoSelectResultGuildEvents(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
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


class ProjoSelectResultMedias(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int
    title_user_preferred: str
    added_alias: datetime | None = Field(validation_alias='@added', serialization_alias='@added')


class ProjoSelectResultParticipants(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    discord_id: int
    discord_id_str: str
    discord_username: str


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


class QuizzGetByIdResultAuthor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class QuizzGetOldestResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
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


class QuizzGetOldestResultAuthor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class QuizzInsertResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class QuizzSetAnswerResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class Rank(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    tier: int
    wc_rank: str
    min_favourites: int
    blood_shards: int
    blood_price: int
    color: int
    emoji: str


class ReminderDeleteByIdResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class ReminderInsertSelectResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    channel_id: int
    channel_id_str: str
    message: str
    timestamp: datetime
    user: 'ReminderInsertSelectResultUser'


class ReminderInsertSelectResultUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class ReminderSelectAllResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    channel_id: int
    channel_id_str: str
    message: str
    timestamp: datetime
    user: 'ReminderSelectAllResultUser'


class ReminderSelectAllResultUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class ReorderWaifuBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    custom_position: Literal['DEFAULT', 'LEFT_OF', 'RIGHT_OF'] | None = None
    other_waifu_id: UUID | None = None


class RerollBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    player_discord_id: int
    waifus_ids: list[str]
    bot_discord_id: int


class RerollResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    obtained: list['WaifuSelectResult']
    nanascends: list['WaifuSelectResult']


class RoleDeleteByRoleIdResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class RoleInsertSelectResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    role_id: int
    role_id_str: str
    emoji: str


class RoleSelectAllResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    role_id: int
    role_id_str: str
    emoji: str


class RollData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str
    name: str
    price: int


class SetGameBananedAnswerBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    answer_bananed: str | None = None


class SetProjectionMessageIdBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    message_id: int


class SetProjectionNameBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str


class SetProjectionStatusBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    status: Literal['ONGOING', 'COMPLETED']


class SetQuizzAnswerBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    answer: str | None = None
    answer_source: str | None = None


class SettingsMergeResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class SettingsSelectAllResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    key: str
    value: str


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


class TradeDeleteResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class TradeSelectResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    author: 'TradeSelectResultAuthor'
    received: list['TradeSelectResultReceived']
    offeree: 'TradeSelectResultOfferee'
    offered: list['TradeSelectResultOffered']
    id: UUID
    blood_shards: int
    completed_at: datetime | None
    created_at: datetime


class TradeSelectResultAuthor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'TradeSelectResultAuthorUser'


class TradeSelectResultAuthorUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class TradeSelectResultOffered(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    character: 'TradeSelectResultOfferedCharacter'
    owner: 'TradeSelectResultOfferedOwner'
    original_owner: 'TradeSelectResultOfferedOriginalOwner | None'
    custom_position_waifu: 'TradeSelectResultOfferedCustomPositionWaifu | None'
    id: UUID
    blooded: bool
    custom_collage: bool
    custom_image: str | None
    custom_name: str | None
    custom_position: 'WaicolleCollagePosition'
    level: int
    locked: bool
    nanaed: bool
    timestamp: datetime
    trade_locked: bool
    disabled: bool


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
    discord_id: int
    discord_id_str: str


class TradeSelectResultOfferedOwner(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'TradeSelectResultOfferedOwnerUser'


class TradeSelectResultOfferedOwnerUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class TradeSelectResultOfferee(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'TradeSelectResultOffereeUser'


class TradeSelectResultOffereeUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class TradeSelectResultReceived(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    character: 'TradeSelectResultReceivedCharacter'
    owner: 'TradeSelectResultReceivedOwner'
    original_owner: 'TradeSelectResultReceivedOriginalOwner | None'
    custom_position_waifu: 'TradeSelectResultReceivedCustomPositionWaifu | None'
    id: UUID
    blooded: bool
    custom_collage: bool
    custom_image: str | None
    custom_name: str | None
    custom_position: 'WaicolleCollagePosition'
    level: int
    locked: bool
    nanaed: bool
    timestamp: datetime
    trade_locked: bool
    disabled: bool


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
    discord_id: int
    discord_id_str: str


class TradeSelectResultReceivedOwner(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'TradeSelectResultReceivedOwnerUser'


class TradeSelectResultReceivedOwnerUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class UpdateAMQSettingsBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    settings: str


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
    discord_id: int
    discord_username: str


class UpsertGuildEventBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str
    start_time: datetime
    end_time: datetime
    organizer_id: int
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
    full_name: str | None = None
    photo: str | None = None
    promotion: str | None = None
    telephone: str | None = None


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
    id: UUID
    ics: str
    user: 'UserCalendarSelectAllResultUser'


class UserCalendarSelectAllResultUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    discord_id: int
    discord_id_str: str
    discord_username: str


class UserCalendarSelectResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    ics: str
    user: 'UserCalendarSelectResultUser'


class UserCalendarSelectResultUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    discord_id: int
    discord_id_str: str
    discord_username: str


class UserSelectResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str
    discord_username: str


class ValidationError(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    loc: list[str | int]
    msg: str
    type: str


class WaifuBulkUpdateResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
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
    discord_id: int
    discord_id_str: str


class WaifuBulkUpdateResultOwner(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'WaifuBulkUpdateResultOwnerUser'


class WaifuBulkUpdateResultOwnerUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class WaifuExportResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    players: list['WaifuExportResultPlayers']
    waifus: list['WaifuExportResultWaifus']
    charas: list['WaifuExportResultCharas']


class WaifuExportResultCharas(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id_al: int
    image: str
    favourites: int


class WaifuExportResultPlayers(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: str
    discord_username: str
    tracked: list[int]


class WaifuExportResultWaifus(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
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


class WaifuReplaceCustomPositionResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class WaifuSelectResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
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
    discord_id: int
    discord_id_str: str


class WaifuSelectResultOwner(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user: 'WaifuSelectResultOwnerUser'


class WaifuSelectResultOwnerUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    discord_id: int
    discord_id_str: str


class WaifuUpdateCustomImageNameResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID


class WhoamiResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    username: str
