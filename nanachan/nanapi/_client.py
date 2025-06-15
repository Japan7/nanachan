import dataclasses
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time
from enum import Enum
from typing import Any, Literal, TypeGuard
from uuid import UUID

import aiohttp
from aiohttp.typedefs import Query
from pydantic import BaseModel
from yarl import QueryVariable, SimpleQuery

from .model import (
    AccountMergeResult,
    AccountSelectAllResult,
    AccountSelectResult,
    AddPlayerCoinsBody,
    Body_client_login,
    BulkUpdateWaifusBody,
    CEdgeSelectFilterCharaResult,
    CEdgeSelectFilterMediaResult,
    CEdgeSelectFilterStaffResult,
    CharaNameAutocompleteResult,
    CharaSelectResult,
    ClientInsertResult,
    CollageResult,
    CollectionAddMediaResult,
    CollectionAddStaffResult,
    CollectionAlbumResult,
    CollectionDeleteResult,
    CollectionGetByIdResult,
    CollectionInsertResult,
    CollectionNameAutocompleteResult,
    CollectionRemoveMediaResult,
    CollectionRemoveStaffResult,
    CollectPotBody,
    CommitTradeResponse,
    CouponDeleteResult,
    CouponInsertResult,
    CouponSelectAllResult,
    CustomizeWaifuBody,
    DonatePlayerCoinsBody,
    EndGameBody,
    EntrySelectAllResult,
    EntrySelectFilterMediaResult,
    GameDeleteByMessageIdResult,
    GameEndResult,
    GameGetByIdResult,
    GameGetCurrentResult,
    GameGetLastResult,
    GameNewResult,
    GameSelectResult,
    GuildEventDeleteResult,
    GuildEventMergeResult,
    GuildEventParticipantAddResult,
    GuildEventParticipantRemoveResult,
    GuildEventSelectResult,
    HistoireDeleteByIdResult,
    HistoireGetByIdResult,
    HistoireInsertResult,
    HistoireSelectIdTitleResult,
    HTTPExceptionModel,
    HTTPValidationError,
    LoginResponse,
    MediaAlbumResult,
    MediaSelectResult,
    MediasPoolExportResult,
    MediaTitleAutocompleteResult,
    MessageBulkDeleteResult,
    MessageBulkInsertResult,
    MessageMergeResult,
    MessagesRagResult,
    MessageUpdateNoindexResult,
    NewClientBody,
    NewCollectionBody,
    NewCouponBody,
    NewGameBody,
    NewHistoireBody,
    NewLootBody,
    NewOfferingBody,
    NewPresenceBody,
    NewProjectionBody,
    NewQuizzBody,
    NewReminderBody,
    NewRoleBody,
    NewTradeBody,
    ParticipantAddBody,
    PlayerAddCoinsResult,
    PlayerAddCollectionResult,
    PlayerAddMediaResult,
    PlayerAddStaffResult,
    PlayerCollectionStatsResult,
    PlayerFreezeResult,
    PlayerGetByUserResult,
    PlayerMediaStatsResult,
    PlayerMergeResult,
    PlayerRemoveCollectionResult,
    PlayerRemoveMediaResult,
    PlayerRemoveStaffResult,
    PlayerSelectResult,
    PlayerStaffStatsResult,
    PlayerTrackedItemsResult,
    PlayerTrackReversedResult,
    PotAddResult,
    PotGetByUserResult,
    PresenceDeleteByIdResult,
    PresenceInsertResult,
    PresenceSelectAllResult,
    ProfileSearchResult,
    ProjoAddEventResult,
    ProjoAddExternalMediaBody,
    ProjoAddExternalMediaResult,
    ProjoAddMediaResult,
    ProjoDeleteResult,
    ProjoDeleteUpcomingEventsResult,
    ProjoInsertResult,
    ProjoParticipantAddResult,
    ProjoParticipantRemoveResult,
    ProjoRemoveExternalMediaResult,
    ProjoRemoveMediaResult,
    ProjoSelectResult,
    ProjoUpdateMessageIdResult,
    ProjoUpdateNameResult,
    ProjoUpdateStatusResult,
    QuizzDeleteByIdResult,
    QuizzGetByIdResult,
    QuizzGetOldestResult,
    QuizzInsertResult,
    QuizzSetAnswerResult,
    Rank,
    ReminderDeleteByIdResult,
    ReminderInsertSelectResult,
    ReminderSelectAllResult,
    ReorderWaifuBody,
    RerollBody,
    RerollResponse,
    RoleDeleteByRoleIdResult,
    RoleInsertSelectResult,
    RoleSelectAllResult,
    RollData,
    SetProjectionMessageIdBody,
    SetProjectionNameBody,
    SetProjectionStatusBody,
    SetQuizzAnswerBody,
    SettingsMergeResult,
    SettingsSelectAllResult,
    StaffAlbumResult,
    StaffNameAutocompleteResult,
    StaffSelectResult,
    TradeDeleteResult,
    TradeSelectResult,
    UpdateMessageNoindexBody,
    UpsertAMQAccountBody,
    UpsertAnilistAccountBody,
    UpsertDiscordAccountBodyItem,
    UpsertGuildEventBody,
    UpsertPlayerBody,
    UpsertProfileBody,
    UpsertUserCalendarBody,
    UserBulkMergeResult,
    UserCalendarDeleteResult,
    UserCalendarMergeResult,
    UserCalendarSelectAllResult,
    UserCalendarSelectResult,
    UserSelectResult,
    WaifuBulkUpdateResult,
    WaifuExportResult,
    WaifuReplaceCustomPositionResult,
    WaifuSelectResult,
    WaifuUpdateCustomImageNameResult,
    WhoamiResponse,
)


@dataclass(slots=True)
class Success[TCode, TSuccess]:
    code: TCode
    result: TSuccess


@dataclass(slots=True)
class Error[TCode, TError]:
    code: TCode
    result: TError


def success[S: Success[Any, Any]](maybe: S | Error[Any, Any]) -> TypeGuard[S]:
    return isinstance(maybe, Success)


def prep_scalar_serializationion(v: Any) -> SimpleQuery:
    # SimpleQuery is str, int, float at time of writing
    if isinstance(v, SimpleQuery):
        return v
    else:
        # FIXME: breaks things, maybe
        return str(v)


def prep_seq_serialization(v: Sequence[Any]) -> Sequence[SimpleQuery]:
    return tuple(prep_scalar_serializationion(lv) for lv in v)


def prep_val_serialization(v: Any) -> QueryVariable:
    if isinstance(v, Enum):
        return prep_val_serialization(v.value)
    elif isinstance(v, Sequence) and not isinstance(v, str):
        return prep_seq_serialization(v)
    else:
        return prep_scalar_serializationion(v)


def prep_serialization(d: dict[str, Any]) -> Query:
    return {k: prep_val_serialization(v) for k, v in d.items() if v is not None}


class JsonDataclassEncoder(json.JSONEncoder):
    def default(self, o: Any):
        if isinstance(o, BaseModel):
            return o.model_dump(by_alias=True)
        if isinstance(o, (datetime, date, time)):
            return o.isoformat()
        if dataclasses.is_dataclass(o) and not isinstance(o, type):
            return dataclasses.asdict(o)
        if isinstance(o, UUID):
            return str(o)
        return super().default(o)


def default_json_serializer(o: Any) -> str:
    return json.dumps(o, cls=JsonDataclassEncoder)


class AmqModule:
    def __init__(self, session: 'ClientSession', server_url: str):
        self.session: ClientSession = session
        self.server_url: str = server_url

    async def amq_get_accounts(
        self, username: str | None = None
    ) -> (
        Success[Literal[200], list[AccountSelectResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Retrieve AMQ accounts, optionally filtered by username."""
        url = f'{self.server_url}/amq/accounts'
        params = {
            'username': username,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[AccountSelectResult]](
                    code=200, result=[AccountSelectResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def amq_upsert_account(
        self, discord_id: str, body: UpsertAMQAccountBody
    ) -> (
        Success[Literal[200], AccountMergeResult]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Create or update an AMQ account by Discord ID."""
        url = f'{self.server_url}/amq/accounts/{discord_id}'

        async with self.session.patch(
            url,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], AccountMergeResult](
                    code=200, result=AccountMergeResult(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def amq_get_settings(
        self, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], list[SettingsSelectAllResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Retrieve all AMQ settings."""
        url = f'{self.server_url}/amq/settings'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[SettingsSelectAllResult]](
                    code=200, result=[SettingsSelectAllResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def amq_update_settings(
        self, body: str, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], list[SettingsMergeResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Update AMQ settings."""
        url = f'{self.server_url}/amq/settings'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.patch(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[SettingsMergeResult]](
                    code=200, result=[SettingsMergeResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )


class AnilistModule:
    def __init__(self, session: 'ClientSession', server_url: str):
        self.session: ClientSession = session
        self.server_url: str = server_url

    async def anilist_get_accounts(
        self,
    ) -> (
        Success[Literal[200], list[AccountSelectAllResult]]
        | Error[Literal[401], HTTPExceptionModel]
    ):
        """Get all AniList accounts."""
        url = f'{self.server_url}/anilist/accounts'

        async with self.session.get(
            url,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[AccountSelectAllResult]](
                    code=200, result=[AccountSelectAllResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def anilist_upsert_account(
        self, discord_id: str, body: UpsertAnilistAccountBody
    ) -> (
        Success[Literal[200], AccountMergeResult]
        | Error[Literal[409], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Upsert AniList account for a Discord user."""
        url = f'{self.server_url}/anilist/accounts/{discord_id}'

        async with self.session.patch(
            url,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], AccountMergeResult](
                    code=200, result=AccountMergeResult(**(await resp.json()))
                )
            if resp.status == 409:
                return Error[Literal[409], HTTPExceptionModel](
                    code=409, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def anilist_get_all_entries(
        self, type: Literal['ANIME', 'MANGA'] | None = None
    ) -> (
        Success[Literal[200], list[EntrySelectAllResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get all AniList entries for all accounts."""
        url = f'{self.server_url}/anilist/accounts/all/entries'
        params = {
            'type': type,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[EntrySelectAllResult]](
                    code=200, result=[EntrySelectAllResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def anilist_get_account_entries(
        self, discord_id: str, type: Literal['ANIME', 'MANGA'] | None = None
    ) -> (
        Success[Literal[200], list[EntrySelectAllResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get AniList entries for a specific Discord user."""
        url = f'{self.server_url}/anilist/accounts/{discord_id}/entries'
        params = {
            'type': type,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[EntrySelectAllResult]](
                    code=200, result=[EntrySelectAllResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def anilist_get_medias(
        self, ids_al: str
    ) -> (
        Success[Literal[200], list[MediaSelectResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get AniList media objects by IDs."""
        url = f'{self.server_url}/anilist/medias'
        params = {
            'ids_al': ids_al,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[MediaSelectResult]](
                    code=200, result=[MediaSelectResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def anilist_media_search(
        self, search: str, type: Literal['ANIME', 'MANGA'] | None = None
    ) -> (
        Success[Literal[200], list[MediaSelectResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Search for AniList media by title."""
        url = f'{self.server_url}/anilist/medias/search'
        params = {
            'search': search,
            'type': type,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[MediaSelectResult]](
                    code=200, result=[MediaSelectResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def anilist_media_title_autocomplete(
        self, search: str, type: Literal['ANIME', 'MANGA'] | None = None
    ) -> (
        Success[Literal[200], list[MediaTitleAutocompleteResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Autocomplete AniList media titles."""
        url = f'{self.server_url}/anilist/medias/autocomplete'
        params = {
            'search': search,
            'type': type,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[MediaTitleAutocompleteResult]](
                    code=200,
                    result=[MediaTitleAutocompleteResult(**e) for e in (await resp.json())],
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def anilist_get_medias_collage(
        self, ids_al: str
    ) -> (
        Success[Literal[200], None]
        | Error[Literal[400], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get a collage image of AniList media covers."""
        url = f'{self.server_url}/anilist/medias/collages'
        params = {
            'ids_al': ids_al,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], None](code=200, result=None)
            if resp.status == 400:
                return Error[Literal[400], HTTPExceptionModel](
                    code=400, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def anilist_get_media_list_entries(
        self, id_al: int
    ) -> (
        Success[Literal[200], list[EntrySelectFilterMediaResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get AniList entries for a specific media."""
        url = f'{self.server_url}/anilist/medias/{id_al}/entries'

        async with self.session.get(
            url,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[EntrySelectFilterMediaResult]](
                    code=200,
                    result=[EntrySelectFilterMediaResult(**e) for e in (await resp.json())],
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def anilist_get_media_chara_edges(
        self, id_al: int
    ) -> (
        Success[Literal[200], list[CEdgeSelectFilterMediaResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get character edges for a specific media."""
        url = f'{self.server_url}/anilist/medias/{id_al}/edges/charas'

        async with self.session.get(
            url,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[CEdgeSelectFilterMediaResult]](
                    code=200,
                    result=[CEdgeSelectFilterMediaResult(**e) for e in (await resp.json())],
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def anilist_get_charas(
        self, ids_al: str
    ) -> (
        Success[Literal[200], list[CharaSelectResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get AniList characters by IDs."""
        url = f'{self.server_url}/anilist/charas'
        params = {
            'ids_al': ids_al,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[CharaSelectResult]](
                    code=200, result=[CharaSelectResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def anilist_chara_search(
        self, search: str
    ) -> (
        Success[Literal[200], list[CharaSelectResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Search for AniList characters by name."""
        url = f'{self.server_url}/anilist/charas/search'
        params = {
            'search': search,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[CharaSelectResult]](
                    code=200, result=[CharaSelectResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def anilist_chara_name_autocomplete(
        self, search: str
    ) -> (
        Success[Literal[200], list[CharaNameAutocompleteResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Autocomplete AniList character names."""
        url = f'{self.server_url}/anilist/charas/autocomplete'
        params = {
            'search': search,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[CharaNameAutocompleteResult]](
                    code=200,
                    result=[CharaNameAutocompleteResult(**e) for e in (await resp.json())],
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def anilist_chara_birthdays(
        self,
    ) -> Success[Literal[200], list[CharaSelectResult]] | Error[Literal[401], HTTPExceptionModel]:
        """Characters Birthdays"""
        url = f'{self.server_url}/anilist/charas/birthdays'

        async with self.session.get(
            url,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[CharaSelectResult]](
                    code=200, result=[CharaSelectResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def anilist_get_chara_collage(
        self, ids_al: str, hide_no_images: int | None = None, blooded: int | None = None
    ) -> (
        Success[Literal[200], None]
        | Error[Literal[400], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get a collage image of AniList character images."""
        url = f'{self.server_url}/anilist/charas/collages'
        params = {
            'ids_al': ids_al,
            'hide_no_images': hide_no_images,
            'blooded': blooded,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], None](code=200, result=None)
            if resp.status == 400:
                return Error[Literal[400], HTTPExceptionModel](
                    code=400, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def anilist_get_chara_chara_edges(
        self, id_al: int
    ) -> (
        Success[Literal[200], list[CEdgeSelectFilterCharaResult]]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get character edges for a specific character."""
        url = f'{self.server_url}/anilist/charas/{id_al}/edges/charas'

        async with self.session.get(
            url,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[CEdgeSelectFilterCharaResult]](
                    code=200,
                    result=[CEdgeSelectFilterCharaResult(**e) for e in (await resp.json())],
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def anilist_get_staffs(
        self, ids_al: str
    ) -> (
        Success[Literal[200], list[StaffSelectResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get AniList staff by IDs."""
        url = f'{self.server_url}/anilist/staffs'
        params = {
            'ids_al': ids_al,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[StaffSelectResult]](
                    code=200, result=[StaffSelectResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def anilist_staff_search(
        self, search: str
    ) -> (
        Success[Literal[200], list[StaffSelectResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Search for AniList staff by name."""
        url = f'{self.server_url}/anilist/staffs/search'
        params = {
            'search': search,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[StaffSelectResult]](
                    code=200, result=[StaffSelectResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def anilist_staff_name_autocomplete(
        self, search: str
    ) -> (
        Success[Literal[200], list[StaffNameAutocompleteResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Autocomplete AniList staff names."""
        url = f'{self.server_url}/anilist/staffs/autocomplete'
        params = {
            'search': search,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[StaffNameAutocompleteResult]](
                    code=200,
                    result=[StaffNameAutocompleteResult(**e) for e in (await resp.json())],
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def anilist_get_staff_chara_edges(
        self, id_al: int
    ) -> (
        Success[Literal[200], list[CEdgeSelectFilterStaffResult]]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get character edges for a specific staff."""
        url = f'{self.server_url}/anilist/staffs/{id_al}/edges/charas'

        async with self.session.get(
            url,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[CEdgeSelectFilterStaffResult]](
                    code=200,
                    result=[CEdgeSelectFilterStaffResult(**e) for e in (await resp.json())],
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )


class CalendarModule:
    def __init__(self, session: 'ClientSession', server_url: str):
        self.session: ClientSession = session
        self.server_url: str = server_url

    async def calendar_get_user_calendars(
        self,
    ) -> (
        Success[Literal[200], list[UserCalendarSelectAllResult]]
        | Error[Literal[401], HTTPExceptionModel]
    ):
        """Get all user calendars."""
        url = f'{self.server_url}/calendar/user_calendars'

        async with self.session.get(
            url,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[UserCalendarSelectAllResult]](
                    code=200,
                    result=[UserCalendarSelectAllResult(**e) for e in (await resp.json())],
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def calendar_get_user_calendar(
        self, discord_id: str
    ) -> (
        Success[Literal[200], UserCalendarSelectResult]
        | Error[Literal[404], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get a user calendar by Discord ID."""
        url = f'{self.server_url}/calendar/user_calendars/{discord_id}'

        async with self.session.get(
            url,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], UserCalendarSelectResult](
                    code=200, result=UserCalendarSelectResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], None](code=404, result=None)
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def calendar_upsert_user_calendar(
        self, discord_id: str, body: UpsertUserCalendarBody
    ) -> (
        Success[Literal[200], UserCalendarMergeResult]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Upsert (update or insert) a user calendar."""
        url = f'{self.server_url}/calendar/user_calendars/{discord_id}'

        async with self.session.patch(
            url,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], UserCalendarMergeResult](
                    code=200, result=UserCalendarMergeResult(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def calendar_delete_user_calendar(
        self, discord_id: str
    ) -> (
        Success[Literal[200], UserCalendarDeleteResult]
        | Error[Literal[404], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Delete a user calendar by Discord ID."""
        url = f'{self.server_url}/calendar/user_calendars/{discord_id}'

        async with self.session.delete(
            url,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], UserCalendarDeleteResult](
                    code=200, result=UserCalendarDeleteResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], None](code=404, result=None)
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def calendar_get_guild_events(
        self, start_after: datetime | None = None, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], list[GuildEventSelectResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get all guild events, optionally after a certain date."""
        url = f'{self.server_url}/calendar/guild_events'
        params = {
            'start_after': start_after,
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[GuildEventSelectResult]](
                    code=200, result=[GuildEventSelectResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def calendar_upsert_guild_event(
        self, discord_id: str, body: UpsertGuildEventBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], GuildEventMergeResult]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Upsert (update or insert) a guild event."""
        url = f'{self.server_url}/calendar/guild_events/{discord_id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.put(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], GuildEventMergeResult](
                    code=200, result=GuildEventMergeResult(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def calendar_delete_guild_event(
        self, discord_id: str, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], GuildEventDeleteResult]
        | Error[Literal[404], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Delete a guild event by Discord ID."""
        url = f'{self.server_url}/calendar/guild_events/{discord_id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], GuildEventDeleteResult](
                    code=200, result=GuildEventDeleteResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], None](code=404, result=None)
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def calendar_add_guild_event_participant(
        self,
        discord_id: str,
        participant_id: str,
        body: ParticipantAddBody,
        client_id: UUID | None = None,
    ) -> (
        Success[Literal[200], GuildEventParticipantAddResult]
        | Error[Literal[404], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Add a participant to a guild event."""
        url = f'{self.server_url}/calendar/guild_events/{discord_id}/participants/{participant_id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.put(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], GuildEventParticipantAddResult](
                    code=200, result=GuildEventParticipantAddResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], None](code=404, result=None)
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def calendar_remove_guild_event_participant(
        self, discord_id: str, participant_id: str, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], GuildEventParticipantRemoveResult]
        | Error[Literal[404], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Remove a participant from a guild event."""
        url = f'{self.server_url}/calendar/guild_events/{discord_id}/participants/{participant_id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], GuildEventParticipantRemoveResult](
                    code=200, result=GuildEventParticipantRemoveResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], None](code=404, result=None)
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def calendar_get_ics(
        self, client: str, user: str | None = None, aggregate: bool | None = None
    ) -> (
        Success[Literal[200], None]
        | Error[Literal[404], None]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get an iCalendar (ICS) file for a client and optionally a user."""
        url = f'{self.server_url}/calendar/ics'
        params = {
            'client': client,
            'user': user,
            'aggregate': aggregate,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], None](code=200, result=None)
            if resp.status == 404:
                return Error[Literal[404], None](code=404, result=None)
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )


class ClientModule:
    def __init__(self, session: 'ClientSession', server_url: str):
        self.session: ClientSession = session
        self.server_url: str = server_url

    async def client_whoami(
        self, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], WhoamiResponse]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get information about the currently authenticated client."""
        url = f'{self.server_url}/clients/'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], WhoamiResponse](
                    code=200, result=WhoamiResponse(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def client_register(
        self, body: NewClientBody
    ) -> (
        Success[Literal[201], ClientInsertResult]
        | Error[Literal[409], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Register a new client account."""
        url = f'{self.server_url}/clients/'

        async with self.session.post(
            url,
            json=body,
        ) as resp:
            if resp.status == 201:
                return Success[Literal[201], ClientInsertResult](
                    code=201, result=ClientInsertResult(**(await resp.json()))
                )
            if resp.status == 409:
                return Error[Literal[409], HTTPExceptionModel](
                    code=409, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def client_login(
        self, body: Body_client_login
    ) -> (
        Success[Literal[201], LoginResponse]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Authenticate client and return JWT access token."""
        url = f'{self.server_url}/clients/token'

        async with self.session.post(
            url,
            data=aiohttp.FormData(body.model_dump(by_alias=True)),
        ) as resp:
            if resp.status == 201:
                return Success[Literal[201], LoginResponse](
                    code=201, result=LoginResponse(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )


class DiscordModule:
    def __init__(self, session: 'ClientSession', server_url: str):
        self.session: ClientSession = session
        self.server_url: str = server_url

    async def discord_bulk_insert_messages(
        self, body: list[str], client_id: UUID | None = None
    ) -> (
        Success[Literal[200], list[MessageBulkInsertResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Bulk create Discord messages."""
        url = f'{self.server_url}/discord/messages'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.post(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[MessageBulkInsertResult]](
                    code=200, result=[MessageBulkInsertResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def discord_delete_messages(
        self, message_ids: str, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], list[MessageBulkDeleteResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Delete Discord messages."""
        url = f'{self.server_url}/discord/messages'
        params = {
            'message_ids': message_ids,
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[MessageBulkDeleteResult]](
                    code=200, result=[MessageBulkDeleteResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def discord_messages_rag(
        self, search_query: str, limit: int | None = None, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], list[MessagesRagResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Retrieve relevant chat sections based on a search query in French."""
        url = f'{self.server_url}/discord/messages/rag'
        params = {
            'search_query': search_query,
            'limit': limit,
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[MessagesRagResult]](
                    code=200, result=[MessagesRagResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def discord_upsert_message(
        self, message_id: str, body: str, noindex: str | None = None, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], MessageMergeResult]
        | Error[Literal[400], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Create or update a Discord message."""
        url = f'{self.server_url}/discord/messages/{message_id}'
        params = {
            'noindex': noindex,
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.put(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], MessageMergeResult](
                    code=200, result=MessageMergeResult(**(await resp.json()))
                )
            if resp.status == 400:
                return Error[Literal[400], HTTPExceptionModel](
                    code=400, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def discord_update_message_noindex(
        self, message_id: str, body: UpdateMessageNoindexBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], MessageUpdateNoindexResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Update indexation instructions of a Discord message."""
        url = f'{self.server_url}/discord/messages/{message_id}/noindex'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.put(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], MessageUpdateNoindexResult](
                    code=200, result=MessageUpdateNoindexResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )


class HistoireModule:
    def __init__(self, session: 'ClientSession', server_url: str):
        self.session: ClientSession = session
        self.server_url: str = server_url

    async def histoire_histoire_index(
        self, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], list[HistoireSelectIdTitleResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """List all histoires (id and title)."""
        url = f'{self.server_url}/histoires/'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[HistoireSelectIdTitleResult]](
                    code=200,
                    result=[HistoireSelectIdTitleResult(**e) for e in (await resp.json())],
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def histoire_new_histoire(
        self, body: NewHistoireBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[201], HistoireInsertResult]
        | Error[Literal[409], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Create a new histoire."""
        url = f'{self.server_url}/histoires/'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.post(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 201:
                return Success[Literal[201], HistoireInsertResult](
                    code=201, result=HistoireInsertResult(**(await resp.json()))
                )
            if resp.status == 409:
                return Error[Literal[409], HTTPExceptionModel](
                    code=409, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def histoire_get_histoire(
        self, id: UUID, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], HistoireGetByIdResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get a single histoire by ID."""
        url = f'{self.server_url}/histoires/{id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], HistoireGetByIdResult](
                    code=200, result=HistoireGetByIdResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def histoire_delete_histoire(
        self, id: UUID, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], HistoireDeleteByIdResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Delete a single histoire by ID."""
        url = f'{self.server_url}/histoires/{id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], HistoireDeleteByIdResult](
                    code=200, result=HistoireDeleteByIdResult(**(await resp.json()))
                )
            if resp.status == 204:
                return Success[Literal[204], None](code=204, result=None)
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )


class PotModule:
    def __init__(self, session: 'ClientSession', server_url: str):
        self.session: ClientSession = session
        self.server_url: str = server_url

    async def pot_get_pot(
        self, discord_id: str, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PotGetByUserResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get pot information for a user by Discord ID."""
        url = f'{self.server_url}/pots/{discord_id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], PotGetByUserResult](
                    code=200, result=PotGetByUserResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def pot_collect_pot(
        self, discord_id: str, body: CollectPotBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PotAddResult]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Collect pot for a user by Discord ID."""
        url = f'{self.server_url}/pots/{discord_id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.post(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], PotAddResult](
                    code=200, result=PotAddResult(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )


class PresenceModule:
    def __init__(self, session: 'ClientSession', server_url: str):
        self.session: ClientSession = session
        self.server_url: str = server_url

    async def presence_get_presences(
        self, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], list[PresenceSelectAllResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get all presences."""
        url = f'{self.server_url}/presences/'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[PresenceSelectAllResult]](
                    code=200, result=[PresenceSelectAllResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def presence_new_presence(
        self, body: NewPresenceBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[201], PresenceInsertResult]
        | Error[Literal[409], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Create a new presence."""
        url = f'{self.server_url}/presences/'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.post(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 201:
                return Success[Literal[201], PresenceInsertResult](
                    code=201, result=PresenceInsertResult(**(await resp.json()))
                )
            if resp.status == 409:
                return Error[Literal[409], HTTPExceptionModel](
                    code=409, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def presence_delete_presence(
        self, id: UUID, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PresenceDeleteByIdResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Delete a presence by ID."""
        url = f'{self.server_url}/presences/{id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], PresenceDeleteByIdResult](
                    code=200, result=PresenceDeleteByIdResult(**(await resp.json()))
                )
            if resp.status == 204:
                return Success[Literal[204], None](code=204, result=None)
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )


class ProjectionModule:
    def __init__(self, session: 'ClientSession', server_url: str):
        self.session: ClientSession = session
        self.server_url: str = server_url

    async def projection_get_projections(
        self,
        status: Literal['ONGOING', 'COMPLETED'] | None = None,
        message_id: str | None = None,
        channel_id: str | None = None,
        client_id: UUID | None = None,
    ) -> (
        Success[Literal[200], list[ProjoSelectResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get a list of projections."""
        url = f'{self.server_url}/projections/'
        params = {
            'status': status,
            'message_id': message_id,
            'channel_id': channel_id,
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[ProjoSelectResult]](
                    code=200, result=[ProjoSelectResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def projection_new_projection(
        self, body: NewProjectionBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[201], ProjoInsertResult]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Create a new projection."""
        url = f'{self.server_url}/projections/'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.post(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 201:
                return Success[Literal[201], ProjoInsertResult](
                    code=201, result=ProjoInsertResult(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def projection_get_projection(
        self, id: UUID, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], ProjoSelectResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get a projection by ID."""
        url = f'{self.server_url}/projections/{id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], ProjoSelectResult](
                    code=200, result=ProjoSelectResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def projection_delete_projection(
        self, id: UUID, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], ProjoDeleteResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Delete a projection by ID."""
        url = f'{self.server_url}/projections/{id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], ProjoDeleteResult](
                    code=200, result=ProjoDeleteResult(**(await resp.json()))
                )
            if resp.status == 204:
                return Success[Literal[204], None](code=204, result=None)
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def projection_set_projection_name(
        self, id: UUID, body: SetProjectionNameBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], ProjoUpdateNameResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Set the name of a projection."""
        url = f'{self.server_url}/projections/{id}/name'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.put(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], ProjoUpdateNameResult](
                    code=200, result=ProjoUpdateNameResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def projection_set_projection_status(
        self, id: UUID, body: SetProjectionStatusBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], ProjoUpdateStatusResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Set the status of a projection."""
        url = f'{self.server_url}/projections/{id}/status'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.put(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], ProjoUpdateStatusResult](
                    code=200, result=ProjoUpdateStatusResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def projection_set_projection_message_id(
        self, id: UUID, body: SetProjectionMessageIdBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], ProjoUpdateMessageIdResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Set the message ID of a projection."""
        url = f'{self.server_url}/projections/{id}/message_id'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.put(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], ProjoUpdateMessageIdResult](
                    code=200, result=ProjoUpdateMessageIdResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def projection_add_projection_anilist_media(
        self, id: UUID, id_al: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], ProjoAddMediaResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Add an AniList media to a projection."""
        url = f'{self.server_url}/projections/{id}/medias/anilist/{id_al}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.put(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], ProjoAddMediaResult](
                    code=200, result=ProjoAddMediaResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def projection_remove_projection_media(
        self, id: UUID, id_al: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], ProjoRemoveMediaResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Remove an AniList media from a projection."""
        url = f'{self.server_url}/projections/{id}/medias/anilist/{id_al}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], ProjoRemoveMediaResult](
                    code=200, result=ProjoRemoveMediaResult(**(await resp.json()))
                )
            if resp.status == 204:
                return Success[Literal[204], None](code=204, result=None)
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def projection_add_projection_external_media(
        self, id: UUID, body: ProjoAddExternalMediaBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], ProjoAddExternalMediaResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Add an external media to a projection."""
        url = f'{self.server_url}/projections/{id}/medias/external'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.post(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], ProjoAddExternalMediaResult](
                    code=200, result=ProjoAddExternalMediaResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def projection_remove_projection_external_media(
        self, id: UUID, external_media_id: UUID, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], ProjoRemoveExternalMediaResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Remove an external media from a projection."""
        url = f'{self.server_url}/projections/{id}/medias/external/{external_media_id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], ProjoRemoveExternalMediaResult](
                    code=200, result=ProjoRemoveExternalMediaResult(**(await resp.json()))
                )
            if resp.status == 204:
                return Success[Literal[204], None](code=204, result=None)
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def projection_add_projection_participant(
        self,
        id: UUID,
        participant_id: str,
        body: ParticipantAddBody,
        client_id: UUID | None = None,
    ) -> (
        Success[Literal[200], ProjoParticipantAddResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Add a participant to a projection."""
        url = f'{self.server_url}/projections/{id}/participants/{participant_id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.put(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], ProjoParticipantAddResult](
                    code=200, result=ProjoParticipantAddResult(**(await resp.json()))
                )
            if resp.status == 204:
                return Success[Literal[204], None](code=204, result=None)
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def projection_remove_projection_participant(
        self, id: UUID, participant_id: str, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], ProjoParticipantRemoveResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Remove a participant from a projection."""
        url = f'{self.server_url}/projections/{id}/participants/{participant_id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], ProjoParticipantRemoveResult](
                    code=200, result=ProjoParticipantRemoveResult(**(await resp.json()))
                )
            if resp.status == 204:
                return Success[Literal[204], None](code=204, result=None)
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def projection_add_projection_guild_event(
        self, id: UUID, discord_id: str, client_id: UUID | None = None
    ) -> (
        Success[Literal[201], ProjoAddEventResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Add a guild event to a projection."""
        url = f'{self.server_url}/projections/{id}/guild_events/{discord_id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.put(
            url,
            params=params,
        ) as resp:
            if resp.status == 201:
                return Success[Literal[201], ProjoAddEventResult](
                    code=201, result=ProjoAddEventResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def projection_delete_upcoming_projection_events(
        self, id: UUID, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], ProjoDeleteUpcomingEventsResult]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Delete upcoming guild events from a projection."""
        url = f'{self.server_url}/projections/{id}/guild_events/upcoming'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], ProjoDeleteUpcomingEventsResult](
                    code=200, result=ProjoDeleteUpcomingEventsResult(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )


class QuizzModule:
    def __init__(self, session: 'ClientSession', server_url: str):
        self.session: ClientSession = session
        self.server_url: str = server_url

    async def quizz_new_quizz(
        self, body: NewQuizzBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[201], QuizzInsertResult]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Create a new quizz."""
        url = f'{self.server_url}/quizz/quizzes'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.post(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 201:
                return Success[Literal[201], QuizzInsertResult](
                    code=201, result=QuizzInsertResult(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def quizz_get_oldest_quizz(
        self, channel_id: str, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], QuizzGetOldestResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get the oldest quizz for a channel."""
        url = f'{self.server_url}/quizz/quizzes/oldest'
        params = {
            'channel_id': channel_id,
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], QuizzGetOldestResult](
                    code=200, result=QuizzGetOldestResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def quizz_get_quizz(
        self, id: UUID, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], QuizzGetByIdResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get a quizz by ID."""
        url = f'{self.server_url}/quizz/quizzes/{id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], QuizzGetByIdResult](
                    code=200, result=QuizzGetByIdResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def quizz_delete_quizz(
        self, id: UUID, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], QuizzDeleteByIdResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Delete a quizz by ID."""
        url = f'{self.server_url}/quizz/quizzes/{id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], QuizzDeleteByIdResult](
                    code=200, result=QuizzDeleteByIdResult(**(await resp.json()))
                )
            if resp.status == 204:
                return Success[Literal[204], None](code=204, result=None)
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def quizz_set_quizz_answer(
        self, id: UUID, body: SetQuizzAnswerBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], QuizzSetAnswerResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Set the answer for a quizz."""
        url = f'{self.server_url}/quizz/quizzes/{id}/answer'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.put(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], QuizzSetAnswerResult](
                    code=200, result=QuizzSetAnswerResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def quizz_get_games(
        self, status: Literal['STARTED', 'ENDED'], client_id: UUID | None = None
    ) -> (
        Success[Literal[200], list[GameSelectResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get games by status."""
        url = f'{self.server_url}/quizz/games'
        params = {
            'status': status,
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[GameSelectResult]](
                    code=200, result=[GameSelectResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def quizz_new_game(
        self, body: NewGameBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[201], GameNewResult]
        | Error[Literal[409], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Create a new game."""
        url = f'{self.server_url}/quizz/games'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.post(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 201:
                return Success[Literal[201], GameNewResult](
                    code=201, result=GameNewResult(**(await resp.json()))
                )
            if resp.status == 409:
                return Error[Literal[409], HTTPExceptionModel](
                    code=409, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def quizz_delete_game(
        self, message_id: str, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], GameDeleteByMessageIdResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Delete a game by message ID."""
        url = f'{self.server_url}/quizz/games'
        params = {
            'message_id': message_id,
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], GameDeleteByMessageIdResult](
                    code=200, result=GameDeleteByMessageIdResult(**(await resp.json()))
                )
            if resp.status == 204:
                return Success[Literal[204], None](code=204, result=None)
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def quizz_get_current_game(
        self, channel_id: str, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], GameGetCurrentResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get the current game for a channel."""
        url = f'{self.server_url}/quizz/games/current'
        params = {
            'channel_id': channel_id,
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], GameGetCurrentResult](
                    code=200, result=GameGetCurrentResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def quizz_get_last_game(
        self, channel_id: str, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], GameGetLastResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get the last game for a channel."""
        url = f'{self.server_url}/quizz/games/last'
        params = {
            'channel_id': channel_id,
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], GameGetLastResult](
                    code=200, result=GameGetLastResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def quizz_get_game(
        self, id: UUID, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], GameGetByIdResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get a game by ID."""
        url = f'{self.server_url}/quizz/games/{id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], GameGetByIdResult](
                    code=200, result=GameGetByIdResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def quizz_end_game(
        self, id: UUID, body: EndGameBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], GameEndResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """End a game by ID."""
        url = f'{self.server_url}/quizz/games/{id}/end'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.post(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], GameEndResult](
                    code=200, result=GameEndResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )


class ReminderModule:
    def __init__(self, session: 'ClientSession', server_url: str):
        self.session: ClientSession = session
        self.server_url: str = server_url

    async def reminder_get_reminders(
        self, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], list[ReminderSelectAllResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get all reminders."""
        url = f'{self.server_url}/reminders/'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[ReminderSelectAllResult]](
                    code=200, result=[ReminderSelectAllResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def reminder_new_reminder(
        self, body: NewReminderBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[201], ReminderInsertSelectResult]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Create a new reminder."""
        url = f'{self.server_url}/reminders/'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.post(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 201:
                return Success[Literal[201], ReminderInsertSelectResult](
                    code=201, result=ReminderInsertSelectResult(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def reminder_delete_reminder(
        self, id: UUID, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], ReminderDeleteByIdResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Delete a reminder by ID."""
        url = f'{self.server_url}/reminders/{id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], ReminderDeleteByIdResult](
                    code=200, result=ReminderDeleteByIdResult(**(await resp.json()))
                )
            if resp.status == 204:
                return Success[Literal[204], None](code=204, result=None)
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )


class RoleModule:
    def __init__(self, session: 'ClientSession', server_url: str):
        self.session: ClientSession = session
        self.server_url: str = server_url

    async def role_get_roles(
        self, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], list[RoleSelectAllResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get all roles."""
        url = f'{self.server_url}/roles/'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[RoleSelectAllResult]](
                    code=200, result=[RoleSelectAllResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def role_new_role(
        self, body: NewRoleBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[201], RoleInsertSelectResult]
        | Error[Literal[409], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Create a new role."""
        url = f'{self.server_url}/roles/'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.post(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 201:
                return Success[Literal[201], RoleInsertSelectResult](
                    code=201, result=RoleInsertSelectResult(**(await resp.json()))
                )
            if resp.status == 409:
                return Error[Literal[409], HTTPExceptionModel](
                    code=409, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def role_delete_role(
        self, role_id: str, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], RoleDeleteByRoleIdResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Delete a role by role_id."""
        url = f'{self.server_url}/roles/{role_id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], RoleDeleteByRoleIdResult](
                    code=200, result=RoleDeleteByRoleIdResult(**(await resp.json()))
                )
            if resp.status == 204:
                return Success[Literal[204], None](code=204, result=None)
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )


class UserModule:
    def __init__(self, session: 'ClientSession', server_url: str):
        self.session: ClientSession = session
        self.server_url: str = server_url

    async def user_discord_account_index(
        self,
    ) -> Success[Literal[200], list[UserSelectResult]] | Error[Literal[401], HTTPExceptionModel]:
        """List all Discord accounts."""
        url = f'{self.server_url}/user/accounts'

        async with self.session.get(
            url,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[UserSelectResult]](
                    code=200, result=[UserSelectResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def user_upsert_discord_accounts(
        self, body: list[UpsertDiscordAccountBodyItem]
    ) -> (
        Success[Literal[200], list[UserBulkMergeResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Bulk upsert Discord accounts."""
        url = f'{self.server_url}/user/accounts'

        async with self.session.patch(
            url,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[UserBulkMergeResult]](
                    code=200, result=[UserBulkMergeResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def user_profile_search(
        self, discord_ids: str | None = None, pattern: str | None = None
    ) -> (
        Success[Literal[200], list[ProfileSearchResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Search user profiles by Discord IDs or pattern."""
        url = f'{self.server_url}/user/profiles/search'
        params = {
            'discord_ids': discord_ids,
            'pattern': pattern,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[ProfileSearchResult]](
                    code=200, result=[ProfileSearchResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def user_get_profile(
        self, discord_id: str
    ) -> (
        Success[Literal[200], ProfileSearchResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get a user profile by Discord ID."""
        url = f'{self.server_url}/user/profiles/{discord_id}'

        async with self.session.get(
            url,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], ProfileSearchResult](
                    code=200, result=ProfileSearchResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def user_upsert_profile(
        self, discord_id: str, body: UpsertProfileBody
    ) -> (
        Success[Literal[200], ProfileSearchResult]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Upsert a user profile by Discord ID."""
        url = f'{self.server_url}/user/profiles/{discord_id}'

        async with self.session.patch(
            url,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], ProfileSearchResult](
                    code=200, result=ProfileSearchResult(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )


class WaicolleModule:
    def __init__(self, session: 'ClientSession', server_url: str):
        self.session: ClientSession = session
        self.server_url: str = server_url

    async def waicolle_get_players(
        self, chara_id_al: int | None = None, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], list[PlayerSelectResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get all players or only the ones who track a specific character."""
        url = f'{self.server_url}/waicolle/players'
        params = {
            'chara_id_al': chara_id_al,
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[PlayerSelectResult]](
                    code=200, result=[PlayerSelectResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_upsert_player(
        self, discord_id: str, body: UpsertPlayerBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerMergeResult]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Upsert a player by Discord ID."""
        url = f'{self.server_url}/waicolle/players/{discord_id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.patch(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], PlayerMergeResult](
                    code=200, result=PlayerMergeResult(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_get_player(
        self, discord_id: str, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerGetByUserResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get a player by Discord ID."""
        url = f'{self.server_url}/waicolle/players/{discord_id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], PlayerGetByUserResult](
                    code=200, result=PlayerGetByUserResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_freeze_player(
        self, discord_id: str, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerFreezeResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Freeze a player by Discord ID."""
        url = f'{self.server_url}/waicolle/players/{discord_id}/freeze'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.put(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], PlayerFreezeResult](
                    code=200, result=PlayerFreezeResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_add_player_coins(
        self, discord_id: str, body: AddPlayerCoinsBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerAddCoinsResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[409], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Add coins to a player."""
        url = f'{self.server_url}/waicolle/players/{discord_id}/coins/add'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.post(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], PlayerAddCoinsResult](
                    code=200, result=PlayerAddCoinsResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 409:
                return Error[Literal[409], HTTPExceptionModel](
                    code=409, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_donate_player_coins(
        self,
        discord_id: str,
        to_discord_id: str,
        body: DonatePlayerCoinsBody,
        client_id: UUID | None = None,
    ) -> (
        Success[Literal[200], list[PlayerAddCoinsResult]]
        | Error[Literal[400], HTTPExceptionModel]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[409], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Donate coins from one player to another."""
        url = f'{self.server_url}/waicolle/players/{discord_id}/coins/donate'
        params = {
            'to_discord_id': to_discord_id,
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.post(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[PlayerAddCoinsResult]](
                    code=200, result=[PlayerAddCoinsResult(**e) for e in (await resp.json())]
                )
            if resp.status == 400:
                return Error[Literal[400], HTTPExceptionModel](
                    code=400, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 409:
                return Error[Literal[409], HTTPExceptionModel](
                    code=409, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_player_roll(
        self,
        discord_id: str,
        roll_id: str | None = None,
        coupon_code: str | None = None,
        nb: int | None = None,
        pool_discord_id: str | None = None,
        reason: str | None = None,
        client_id: UUID | None = None,
    ) -> (
        Success[Literal[201], list[WaifuSelectResult]]
        | Success[Literal[204], None]
        | Error[Literal[400], HTTPExceptionModel]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[409], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Perform a waifu roll for a player.
        roll_id, coupon_code, and nb are mutually exclusive.
        By default, waifus are chosen from the player's pool. You can select another user's pool by
        setting pool_discord_id.
        reason is optional and will only be used for logging."""
        url = f'{self.server_url}/waicolle/players/{discord_id}/roll'
        params = {
            'roll_id': roll_id,
            'coupon_code': coupon_code,
            'nb': nb,
            'pool_discord_id': pool_discord_id,
            'reason': reason,
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.post(
            url,
            params=params,
        ) as resp:
            if resp.status == 201:
                return Success[Literal[201], list[WaifuSelectResult]](
                    code=201, result=[WaifuSelectResult(**e) for e in (await resp.json())]
                )
            if resp.status == 204:
                return Success[Literal[204], None](code=204, result=None)
            if resp.status == 400:
                return Error[Literal[400], HTTPExceptionModel](
                    code=400, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 409:
                return Error[Literal[409], HTTPExceptionModel](
                    code=409, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_get_player_tracked_items(
        self, discord_id: str, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerTrackedItemsResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get tracked items (medias, staffs, collections) for a player."""
        url = f'{self.server_url}/waicolle/players/{discord_id}/tracks'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], PlayerTrackedItemsResult](
                    code=200, result=PlayerTrackedItemsResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_get_player_track_unlocked(
        self, discord_id: str, hide_singles: int | None = None, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], list[WaifuSelectResult]]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Retrieve unlocked waifus owned by other players tracked by the player.
        Set hide_singles to 1 to exclude waifus the player already owns at least one copy of."""
        url = f'{self.server_url}/waicolle/players/{discord_id}/tracks/unlocked'
        params = {
            'hide_singles': hide_singles,
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[WaifuSelectResult]](
                    code=200, result=[WaifuSelectResult(**e) for e in (await resp.json())]
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_get_player_track_reversed(
        self, discord_id: str, hide_singles: int | None = None, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], list[PlayerTrackReversedResult]]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Retrieve unlocked waifus owned by the player that are tracked by other players.
        Set hide_singles to 1 to exclude waifus that other players already own at least one copy of."""
        url = f'{self.server_url}/waicolle/players/{discord_id}/tracks/reversed'
        params = {
            'hide_singles': hide_singles,
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[PlayerTrackReversedResult]](
                    code=200, result=[PlayerTrackReversedResult(**e) for e in (await resp.json())]
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_get_player_media_stats(
        self, discord_id: str, id_al: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerMediaStatsResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get ownership statistics (number owned / total) for a player on a specific media."""
        url = f'{self.server_url}/waicolle/players/{discord_id}/tracks/medias/{id_al}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], PlayerMediaStatsResult](
                    code=200, result=PlayerMediaStatsResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_player_track_media(
        self, discord_id: str, id_al: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerAddMediaResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Add a media to a player tracking list."""
        url = f'{self.server_url}/waicolle/players/{discord_id}/tracks/medias/{id_al}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.put(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], PlayerAddMediaResult](
                    code=200, result=PlayerAddMediaResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_player_untrack_media(
        self, discord_id: str, id_al: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerRemoveMediaResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Remove a media from a player tracking list."""
        url = f'{self.server_url}/waicolle/players/{discord_id}/tracks/medias/{id_al}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], PlayerRemoveMediaResult](
                    code=200, result=PlayerRemoveMediaResult(**(await resp.json()))
                )
            if resp.status == 204:
                return Success[Literal[204], None](code=204, result=None)
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_get_player_staff_stats(
        self, discord_id: str, id_al: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerStaffStatsResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get ownership statistics (number owned / total) for a player on a specific staff."""
        url = f'{self.server_url}/waicolle/players/{discord_id}/tracks/staffs/{id_al}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], PlayerStaffStatsResult](
                    code=200, result=PlayerStaffStatsResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_player_track_staff(
        self, discord_id: str, id_al: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerAddStaffResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Add a staff to a player tracking list."""
        url = f'{self.server_url}/waicolle/players/{discord_id}/tracks/staffs/{id_al}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.put(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], PlayerAddStaffResult](
                    code=200, result=PlayerAddStaffResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_player_untrack_staff(
        self, discord_id: str, id_al: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerRemoveStaffResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Remove a staff from a player tracking list."""
        url = f'{self.server_url}/waicolle/players/{discord_id}/tracks/staffs/{id_al}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], PlayerRemoveStaffResult](
                    code=200, result=PlayerRemoveStaffResult(**(await resp.json()))
                )
            if resp.status == 204:
                return Success[Literal[204], None](code=204, result=None)
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_get_player_collection_stats(
        self, discord_id: str, id: UUID, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerCollectionStatsResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get ownership statistics (number owned / total) for a player on a specific collection."""
        url = f'{self.server_url}/waicolle/players/{discord_id}/tracks/collections/{id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], PlayerCollectionStatsResult](
                    code=200, result=PlayerCollectionStatsResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_player_track_collection(
        self, discord_id: str, id: UUID, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerAddCollectionResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Add a collection to a player tracking list."""
        url = f'{self.server_url}/waicolle/players/{discord_id}/tracks/collections/{id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.put(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], PlayerAddCollectionResult](
                    code=200, result=PlayerAddCollectionResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_player_untrack_collection(
        self, discord_id: str, id: UUID, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerRemoveCollectionResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Remove a collection from a player tracking list."""
        url = f'{self.server_url}/waicolle/players/{discord_id}/tracks/collections/{id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], PlayerRemoveCollectionResult](
                    code=200, result=PlayerRemoveCollectionResult(**(await resp.json()))
                )
            if resp.status == 204:
                return Success[Literal[204], None](code=204, result=None)
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_get_player_collage(
        self,
        discord_id: str,
        filter: Literal['FULL', 'LOCKED', 'UNLOCKED', 'ASCENDED', 'EDGED', 'CUSTOM'],
        client_id: UUID | None = None,
    ) -> (
        Success[Literal[200], CollageResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get waifu collage for a player."""
        url = f'{self.server_url}/waicolle/players/{discord_id}/collages/waifus'
        params = {
            'filter': filter,
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], CollageResult](
                    code=200, result=CollageResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_get_player_media_album(
        self,
        discord_id: str,
        id_al: int,
        owned_only: int | None = None,
        client_id: UUID | None = None,
    ) -> (
        Success[Literal[200], MediaAlbumResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get media album collage for a player."""
        url = f'{self.server_url}/waicolle/players/{discord_id}/collages/medias/{id_al}'
        params = {
            'owned_only': owned_only,
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], MediaAlbumResult](
                    code=200, result=MediaAlbumResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_get_player_staff_album(
        self,
        discord_id: str,
        id_al: int,
        owned_only: int | None = None,
        client_id: UUID | None = None,
    ) -> (
        Success[Literal[200], StaffAlbumResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get staff album collage for a player."""
        url = f'{self.server_url}/waicolle/players/{discord_id}/collages/staffs/{id_al}'
        params = {
            'owned_only': owned_only,
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], StaffAlbumResult](
                    code=200, result=StaffAlbumResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_get_player_collection_album(
        self,
        discord_id: str,
        id: UUID,
        owned_only: int | None = None,
        client_id: UUID | None = None,
    ) -> (
        Success[Literal[200], CollectionAlbumResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get collection album collage for a player."""
        url = f'{self.server_url}/waicolle/players/{discord_id}/collages/collections/{id}'
        params = {
            'owned_only': owned_only,
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], CollectionAlbumResult](
                    code=200, result=CollectionAlbumResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_get_waifus(
        self,
        ids: str | None = None,
        discord_id: str | None = None,
        level: int | None = None,
        locked: int | None = None,
        trade_locked: int | None = None,
        blooded: int | None = None,
        nanaed: int | None = None,
        custom_collage: int | None = None,
        as_og: int | None = None,
        ascended: int | None = None,
        edged: int | None = None,
        ascendable: int | None = None,
        chara_id_al: int | None = None,
        client_id: UUID | None = None,
    ) -> (
        Success[Literal[200], list[WaifuSelectResult]]
        | Error[Literal[400], HTTPExceptionModel]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get waifus with various filters:
        ids: List of waifu IDs
        discord_id: Owner or original owner (if as_og)
        level: Waifu level
        locked: Whether waifu is currently locked (0: no, 1: yes, None: ignore filter)
        trade_locked: Whether waifu is currently in trade (0: no, 1: yes, None: ignore filter)
        blooded: Whether waifu is blooded (0: no, 1: yes, None: ignore filter)
        nanaed: Whether waifu can be retrieved with blood (0: no, 1: yes, None: ignore filter)
        custom_collage: Whether waifu is part of a custom collage (0: no, 1: yes, None: ignore filter)
        as_og: Use discord_id as original owner (0 or None: no, 1: yes)
        ascended: Filter waifus with level >= 1 (0 or None: ignore filter, 1: yes)
        edged: Whether waifu is close to a level upgrade (0 or None: ignore filter, 1: yes)
        ascendable: Whether waifu can level up (0 or None: ignore filter, 1: yes)
        chara_id_al: Waifus matching a specific character ID.
        chara_id_al is exclusive and cannot be used with other filters."""
        url = f'{self.server_url}/waicolle/waifus'
        params = {
            'ids': ids,
            'discord_id': discord_id,
            'level': level,
            'locked': locked,
            'trade_locked': trade_locked,
            'blooded': blooded,
            'nanaed': nanaed,
            'custom_collage': custom_collage,
            'as_og': as_og,
            'ascended': ascended,
            'edged': edged,
            'ascendable': ascendable,
            'chara_id_al': chara_id_al,
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[WaifuSelectResult]](
                    code=200, result=[WaifuSelectResult(**e) for e in (await resp.json())]
                )
            if resp.status == 400:
                return Error[Literal[400], HTTPExceptionModel](
                    code=400, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_bulk_update_waifus(
        self, body: BulkUpdateWaifusBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], list[WaifuBulkUpdateResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Bulk update waifus."""
        url = f'{self.server_url}/waicolle/waifus'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.patch(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[WaifuBulkUpdateResult]](
                    code=200, result=[WaifuBulkUpdateResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_reroll(
        self, body: RerollBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[201], RerollResponse]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Reroll waifus for a player."""
        url = f'{self.server_url}/waicolle/waifus/reroll'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.post(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 201:
                return Success[Literal[201], RerollResponse](
                    code=201, result=RerollResponse(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_blood_expired_waifus(
        self, discord_id: str, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], list[WaifuSelectResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Blood expired waifus for a player."""
        url = f'{self.server_url}/waicolle/waifus/expired'
        params = {
            'discord_id': discord_id,
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[WaifuSelectResult]](
                    code=200, result=[WaifuSelectResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_customize_waifu(
        self, id: UUID, body: CustomizeWaifuBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], WaifuUpdateCustomImageNameResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Customize waifu image name."""
        url = f'{self.server_url}/waicolle/waifus/{id}/customs'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.patch(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], WaifuUpdateCustomImageNameResult](
                    code=200, result=WaifuUpdateCustomImageNameResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_reorder_waifu(
        self, id: UUID, body: ReorderWaifuBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], WaifuReplaceCustomPositionResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Reorder waifu custom position."""
        url = f'{self.server_url}/waicolle/waifus/{id}/reorder'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.patch(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], WaifuReplaceCustomPositionResult](
                    code=200, result=WaifuReplaceCustomPositionResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_ascend_waifu(
        self, id: UUID, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], WaifuSelectResult]
        | Error[Literal[400], HTTPExceptionModel]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Ascend a waifu by ID."""
        url = f'{self.server_url}/waicolle/waifus/{id}/ascend'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.post(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], WaifuSelectResult](
                    code=200, result=WaifuSelectResult(**(await resp.json()))
                )
            if resp.status == 400:
                return Error[Literal[400], HTTPExceptionModel](
                    code=400, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_blood_waifu(
        self, id: UUID, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], CharaSelectResult]
        | Error[Literal[400], HTTPExceptionModel]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Blood a waifu by ID."""
        url = f'{self.server_url}/waicolle/waifus/{id}/blood'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.post(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], CharaSelectResult](
                    code=200, result=CharaSelectResult(**(await resp.json()))
                )
            if resp.status == 400:
                return Error[Literal[400], HTTPExceptionModel](
                    code=400, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_trade_index(
        self, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], list[TradeSelectResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get all trades."""
        url = f'{self.server_url}/waicolle/trades'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[TradeSelectResult]](
                    code=200, result=[TradeSelectResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_new_trade(
        self, body: NewTradeBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[201], TradeSelectResult]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Create a new trade."""
        url = f'{self.server_url}/waicolle/trades'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.post(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 201:
                return Success[Literal[201], TradeSelectResult](
                    code=201, result=TradeSelectResult(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_new_offering(
        self, body: NewOfferingBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[201], TradeSelectResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Create a new offering trade."""
        url = f'{self.server_url}/waicolle/trades/offerings'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.post(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 201:
                return Success[Literal[201], TradeSelectResult](
                    code=201, result=TradeSelectResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_new_loot(
        self, body: NewLootBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[201], TradeSelectResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Create a new loot trade."""
        url = f'{self.server_url}/waicolle/trades/loots'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.post(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 201:
                return Success[Literal[201], TradeSelectResult](
                    code=201, result=TradeSelectResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_cancel_trade(
        self, id: UUID, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], TradeDeleteResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Cancel a trade by ID."""
        url = f'{self.server_url}/waicolle/trades/{id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], TradeDeleteResult](
                    code=200, result=TradeDeleteResult(**(await resp.json()))
                )
            if resp.status == 204:
                return Success[Literal[204], None](code=204, result=None)
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_commit_trade(
        self, id: UUID, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], CommitTradeResponse]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[409], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Commit a trade by ID."""
        url = f'{self.server_url}/waicolle/trades/{id}/commit'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.post(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], CommitTradeResponse](
                    code=200, result=CommitTradeResponse(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 409:
                return Error[Literal[409], HTTPExceptionModel](
                    code=409, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_new_collection(
        self, body: NewCollectionBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[201], CollectionInsertResult]
        | Error[Literal[409], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Create a new collection."""
        url = f'{self.server_url}/waicolle/collections'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.post(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 201:
                return Success[Literal[201], CollectionInsertResult](
                    code=201, result=CollectionInsertResult(**(await resp.json()))
                )
            if resp.status == 409:
                return Error[Literal[409], HTTPExceptionModel](
                    code=409, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_collection_name_autocomplete(
        self, search: str, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], list[CollectionNameAutocompleteResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Autocomplete collection names."""
        url = f'{self.server_url}/waicolle/collections/autocomplete'
        params = {
            'search': search,
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[CollectionNameAutocompleteResult]](
                    code=200,
                    result=[CollectionNameAutocompleteResult(**e) for e in (await resp.json())],
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_get_collection(
        self, id: UUID, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], CollectionGetByIdResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get a collection by ID."""
        url = f'{self.server_url}/waicolle/collections/{id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], CollectionGetByIdResult](
                    code=200, result=CollectionGetByIdResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_delete_collection(
        self, id: UUID, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], CollectionDeleteResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Delete a collection by ID."""
        url = f'{self.server_url}/waicolle/collections/{id}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], CollectionDeleteResult](
                    code=200, result=CollectionDeleteResult(**(await resp.json()))
                )
            if resp.status == 204:
                return Success[Literal[204], None](code=204, result=None)
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_collection_track_media(
        self, id: UUID, id_al: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], CollectionAddMediaResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Track a media for a collection."""
        url = f'{self.server_url}/waicolle/collections/{id}/medias/{id_al}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.put(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], CollectionAddMediaResult](
                    code=200, result=CollectionAddMediaResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_collection_untrack_media(
        self, id: UUID, id_al: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], CollectionRemoveMediaResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Untrack a media for a collection."""
        url = f'{self.server_url}/waicolle/collections/{id}/medias/{id_al}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], CollectionRemoveMediaResult](
                    code=200, result=CollectionRemoveMediaResult(**(await resp.json()))
                )
            if resp.status == 204:
                return Success[Literal[204], None](code=204, result=None)
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_collection_track_staff(
        self, id: UUID, id_al: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], CollectionAddStaffResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Track a staff for a collection."""
        url = f'{self.server_url}/waicolle/collections/{id}/staffs/{id_al}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.put(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], CollectionAddStaffResult](
                    code=200, result=CollectionAddStaffResult(**(await resp.json()))
                )
            if resp.status == 404:
                return Error[Literal[404], HTTPExceptionModel](
                    code=404, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_collection_untrack_staff(
        self, id: UUID, id_al: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], CollectionRemoveStaffResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Untrack a staff for a collection."""
        url = f'{self.server_url}/waicolle/collections/{id}/staffs/{id_al}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], CollectionRemoveStaffResult](
                    code=200, result=CollectionRemoveStaffResult(**(await resp.json()))
                )
            if resp.status == 204:
                return Success[Literal[204], None](code=204, result=None)
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_get_coupons(
        self, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], list[CouponSelectAllResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get all coupons."""
        url = f'{self.server_url}/waicolle/coupons'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[CouponSelectAllResult]](
                    code=200, result=[CouponSelectAllResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_new_coupon(
        self, body: NewCouponBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[201], CouponInsertResult]
        | Error[Literal[409], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Create a new coupon."""
        url = f'{self.server_url}/waicolle/coupons'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.post(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 201:
                return Success[Literal[201], CouponInsertResult](
                    code=201, result=CouponInsertResult(**(await resp.json()))
                )
            if resp.status == 409:
                return Error[Literal[409], HTTPExceptionModel](
                    code=409, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_delete_coupon(
        self, code: str, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], CouponDeleteResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Delete a coupon by code."""
        url = f'{self.server_url}/waicolle/coupons/{code}'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], CouponDeleteResult](
                    code=200, result=CouponDeleteResult(**(await resp.json()))
                )
            if resp.status == 204:
                return Success[Literal[204], None](code=204, result=None)
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 403:
                return Error[Literal[403], HTTPExceptionModel](
                    code=403, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_get_ranks(
        self,
    ) -> Success[Literal[200], list[Rank]] | Error[Literal[401], HTTPExceptionModel]:
        """Get all ranks."""
        url = f'{self.server_url}/waicolle/settings/ranks'

        async with self.session.get(
            url,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[Rank]](
                    code=200, result=[Rank(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_get_rolls(
        self, discord_id: str
    ) -> (
        Success[Literal[200], list[RollData]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Get all rolls and their data."""
        url = f'{self.server_url}/waicolle/settings/rolls'
        params = {
            'discord_id': discord_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[RollData]](
                    code=200, result=[RollData(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_export_waifus(
        self, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], WaifuExportResult]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        """Export all waifus."""
        url = f'{self.server_url}/waicolle/exports/waifus'
        params = {
            'client_id': client_id,
        }
        params = prep_serialization(params)

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], WaifuExportResult](
                    code=200, result=WaifuExportResult(**(await resp.json()))
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            if resp.status == 422:
                return Error[Literal[422], HTTPValidationError](
                    code=422, result=HTTPValidationError(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )

    async def waicolle_export_daily(
        self,
    ) -> (
        Success[Literal[200], list[MediasPoolExportResult]]
        | Error[Literal[401], HTTPExceptionModel]
    ):
        """Export daily media pool."""
        url = f'{self.server_url}/waicolle/exports/daily'

        async with self.session.get(
            url,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[MediasPoolExportResult]](
                    code=200, result=[MediasPoolExportResult(**e) for e in (await resp.json())]
                )
            if resp.status == 401:
                return Error[Literal[401], HTTPExceptionModel](
                    code=401, result=HTTPExceptionModel(**(await resp.json()))
                )
            raise aiohttp.ClientResponseError(
                resp.request_info,
                resp.history,
                status=resp.status,
                message=str(resp.reason),
                headers=resp.headers,
            )


class ClientSession(aiohttp.ClientSession):
    def __init__(self, server_url: str, **kwargs):
        super().__init__(**kwargs)
        self.amq: AmqModule = AmqModule(self, server_url)
        self.anilist: AnilistModule = AnilistModule(self, server_url)
        self.calendar: CalendarModule = CalendarModule(self, server_url)
        self.client: ClientModule = ClientModule(self, server_url)
        self.discord: DiscordModule = DiscordModule(self, server_url)
        self.histoire: HistoireModule = HistoireModule(self, server_url)
        self.pot: PotModule = PotModule(self, server_url)
        self.presence: PresenceModule = PresenceModule(self, server_url)
        self.projection: ProjectionModule = ProjectionModule(self, server_url)
        self.quizz: QuizzModule = QuizzModule(self, server_url)
        self.reminder: ReminderModule = ReminderModule(self, server_url)
        self.role: RoleModule = RoleModule(self, server_url)
        self.user: UserModule = UserModule(self, server_url)
        self.waicolle: WaicolleModule = WaicolleModule(self, server_url)


def get_session(
    server_url: str, *, json_serialize: Callable[[Any], str] = default_json_serializer, **kwargs
) -> ClientSession:
    return ClientSession(server_url, json_serialize=json_serialize, **kwargs)
