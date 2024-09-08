from dataclasses import asdict, dataclass
from enum import Enum
from typing import Literal, TypeGuard
from uuid import UUID

import aiohttp

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
    GameUpdateBananedResult,
    GuildEventDeleteResult,
    GuildEventMergeResult,
    GuildEventParticipantAddResult,
    GuildEventParticipantRemoveResult,
    GuildEventSelectAllResult,
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
    NewClientBody,
    NewCollectionBody,
    NewCouponBody,
    NewGameBody,
    NewHistoireBody,
    NewOfferingBody,
    NewPresenceBody,
    NewProjectionBody,
    NewProjectionEventBody,
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
    SetGameBananedAnswerBody,
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
    UpdateAMQSettingsBody,
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


def success[S: Success](maybe: S | Error) -> TypeGuard[S]:
    return isinstance(maybe, Success)


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
        url = f'{self.server_url}/amq/accounts'
        params = dict(
            username=username,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, discord_id: int, body: UpsertAMQAccountBody
    ) -> (
        Success[Literal[200], AccountMergeResult]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
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
        url = f'{self.server_url}/amq/settings'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, body: UpdateAMQSettingsBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], list[SettingsMergeResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/amq/settings'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, discord_id: int, body: UpsertAnilistAccountBody
    ) -> (
        Success[Literal[200], AccountMergeResult]
        | Error[Literal[409], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
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
        url = f'{self.server_url}/anilist/accounts/all/entries'
        params = dict(
            type=type,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, discord_id: int, type: Literal['ANIME', 'MANGA'] | None = None
    ) -> (
        Success[Literal[200], list[EntrySelectAllResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/anilist/accounts/{discord_id}/entries'
        params = dict(
            type=type,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/anilist/medias'
        params = dict(
            ids_al=ids_al,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, type: Literal['ANIME', 'MANGA'], search: str
    ) -> (
        Success[Literal[200], list[MediaSelectResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/anilist/medias/search'
        params = dict(
            type=type,
            search=search,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/anilist/medias/autocomplete'
        params = dict(
            search=search,
            type=type,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/anilist/medias/collages'
        params = dict(
            ids_al=ids_al,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/anilist/charas'
        params = dict(
            ids_al=ids_al,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/anilist/charas/search'
        params = dict(
            search=search,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/anilist/charas/autocomplete'
        params = dict(
            search=search,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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

    async def anilist_get_chara_collage(
        self, ids_al: str, hide_no_images: int | None = None, blooded: int | None = None
    ) -> (
        Success[Literal[200], None]
        | Error[Literal[400], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/anilist/charas/collages'
        params = dict(
            ids_al=ids_al,
            hide_no_images=hide_no_images,
            blooded=blooded,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/anilist/staffs'
        params = dict(
            ids_al=ids_al,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/anilist/staffs/search'
        params = dict(
            search=search,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/anilist/staffs/autocomplete'
        params = dict(
            search=search,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, discord_id: int
    ) -> (
        Success[Literal[200], UserCalendarSelectResult]
        | Error[Literal[404], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
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
        self, discord_id: int, body: UpsertUserCalendarBody
    ) -> (
        Success[Literal[200], UserCalendarMergeResult]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
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
        self, discord_id: int
    ) -> (
        Success[Literal[200], UserCalendarDeleteResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/calendar/user_calendars/{discord_id}'

        async with self.session.delete(
            url,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], UserCalendarDeleteResult](
                    code=200, result=UserCalendarDeleteResult(**(await resp.json()))
                )
            if resp.status == 204:
                return Success[Literal[204], None](code=204, result=None)
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
        self, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], list[GuildEventSelectAllResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/calendar/guild_events'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[GuildEventSelectAllResult]](
                    code=200, result=[GuildEventSelectAllResult(**e) for e in (await resp.json())]
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
        self, discord_id: int, body: UpsertGuildEventBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], GuildEventMergeResult]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/calendar/guild_events/{discord_id}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, discord_id: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], GuildEventDeleteResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/calendar/guild_events/{discord_id}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], GuildEventDeleteResult](
                    code=200, result=GuildEventDeleteResult(**(await resp.json()))
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

    async def calendar_add_participant_to_guild_event(
        self, discord_id: int, body: ParticipantAddBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], GuildEventParticipantAddResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/calendar/guild_events/{discord_id}/participants'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

        async with self.session.post(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], GuildEventParticipantAddResult](
                    code=200, result=GuildEventParticipantAddResult(**(await resp.json()))
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

    async def calendar_remove_participant_from_guild_event(
        self, discord_id: int, participant_id: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], GuildEventParticipantRemoveResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/calendar/guild_events/{discord_id}/participants/{participant_id}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], GuildEventParticipantRemoveResult](
                    code=200, result=GuildEventParticipantRemoveResult(**(await resp.json()))
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

    async def calendar_get_ics(
        self, client: str, discord_id: int
    ) -> (
        Success[Literal[200], None]
        | Error[Literal[404], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/calendar/ics'
        params = dict(
            client=client,
            discord_id=discord_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

        async with self.session.get(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], None](code=200, result=None)
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
        url = f'{self.server_url}/clients/'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/clients/token'

        async with self.session.post(
            url,
            data=aiohttp.FormData(asdict(body)),
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
        url = f'{self.server_url}/histoires/'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/histoires/'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/histoires/{id}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/histoires/{id}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, discord_id: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PotGetByUserResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/pots/{discord_id}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, discord_id: int, body: CollectPotBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PotAddResult]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/pots/{discord_id}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/presences/'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/presences/'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/presences/{id}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        message_id: int | None = None,
        channel_id: int | None = None,
        client_id: UUID | None = None,
    ) -> (
        Success[Literal[200], list[ProjoSelectResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/projections/'
        params = dict(
            status=status,
            message_id=message_id,
            channel_id=channel_id,
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/projections/'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/projections/{id}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/projections/{id}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/projections/{id}/name'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/projections/{id}/status'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/projections/{id}/message_id'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/projections/{id}/medias/anilist/{id_al}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/projections/{id}/medias/anilist/{id_al}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/projections/{id}/medias/external'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/projections/{id}/medias/external/{external_media_id}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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

    async def projection_new_projection_event(
        self, id: UUID, body: NewProjectionEventBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[201], ProjoAddEventResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/projections/{id}/events'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

        async with self.session.post(
            url,
            params=params,
            json=body,
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
        Success[Literal[200], list[ProjoDeleteUpcomingEventsResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/projections/{id}/events'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

        async with self.session.delete(
            url,
            params=params,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], list[ProjoDeleteUpcomingEventsResult]](
                    code=200,
                    result=[ProjoDeleteUpcomingEventsResult(**e) for e in (await resp.json())],
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
        url = f'{self.server_url}/quizz/quizzes'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, channel_id: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], QuizzGetOldestResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/quizz/quizzes/oldest'
        params = dict(
            channel_id=channel_id,
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/quizz/quizzes/{id}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/quizz/quizzes/{id}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/quizz/quizzes/{id}/answer'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/quizz/games'
        params = dict(
            status=status,
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/quizz/games'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, message_id: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], GameDeleteByMessageIdResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/quizz/games'
        params = dict(
            message_id=message_id,
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, channel_id: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], GameGetCurrentResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/quizz/games/current'
        params = dict(
            channel_id=channel_id,
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, channel_id: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], GameGetLastResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/quizz/games/last'
        params = dict(
            channel_id=channel_id,
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/quizz/games/{id}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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

    async def quizz_set_game_bananed_answer(
        self, id: UUID, body: SetGameBananedAnswerBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], GameUpdateBananedResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/quizz/games/{id}/bananed'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

        async with self.session.put(
            url,
            params=params,
            json=body,
        ) as resp:
            if resp.status == 200:
                return Success[Literal[200], GameUpdateBananedResult](
                    code=200, result=GameUpdateBananedResult(**(await resp.json()))
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

    async def quizz_end_game(
        self, id: UUID, body: EndGameBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], GameEndResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/quizz/games/{id}/end'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/reminders/'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/reminders/'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/reminders/{id}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/roles/'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/roles/'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, role_id: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], RoleDeleteByRoleIdResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/roles/{role_id}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/user/profiles/search'
        params = dict(
            discord_ids=discord_ids,
            pattern=pattern,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, discord_id: int
    ) -> (
        Success[Literal[200], ProfileSearchResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
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
        self, discord_id: int, body: UpsertProfileBody
    ) -> (
        Success[Literal[200], ProfileSearchResult]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
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
        url = f'{self.server_url}/waicolle/players'
        params = dict(
            chara_id_al=chara_id_al,
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, discord_id: int, body: UpsertPlayerBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerMergeResult]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/waicolle/players/{discord_id}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, discord_id: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerGetByUserResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/waicolle/players/{discord_id}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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

    async def waicolle_add_player_coins(
        self, discord_id: int, body: AddPlayerCoinsBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerAddCoinsResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[409], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/waicolle/players/{discord_id}/coins/add'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        discord_id: int,
        to_discord_id: int,
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
        url = f'{self.server_url}/waicolle/players/{discord_id}/coins/donate'
        params = dict(
            to_discord_id=to_discord_id,
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        discord_id: int,
        roll_id: str | None = None,
        coupon_code: str | None = None,
        nb: int | None = None,
        pool_discord_id: int | None = None,
        client_id: UUID | None = None,
    ) -> (
        Success[Literal[201], list[WaifuSelectResult]]
        | Error[Literal[400], HTTPExceptionModel]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[409], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/waicolle/players/{discord_id}/roll'
        params = dict(
            roll_id=roll_id,
            coupon_code=coupon_code,
            nb=nb,
            pool_discord_id=pool_discord_id,
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

        async with self.session.post(
            url,
            params=params,
        ) as resp:
            if resp.status == 201:
                return Success[Literal[201], list[WaifuSelectResult]](
                    code=201, result=[WaifuSelectResult(**e) for e in (await resp.json())]
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

    async def waicolle_get_player_tracked_items(
        self, discord_id: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerTrackedItemsResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/waicolle/players/{discord_id}/tracks'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, discord_id: int, hide_singles: int | None = None, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], list[WaifuSelectResult]]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/waicolle/players/{discord_id}/tracks/unlocked'
        params = dict(
            hide_singles=hide_singles,
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, discord_id: int, hide_singles: int | None = None, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], list[PlayerTrackReversedResult]]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/waicolle/players/{discord_id}/tracks/reversed'
        params = dict(
            hide_singles=hide_singles,
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, discord_id: int, id_al: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerMediaStatsResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/waicolle/players/{discord_id}/tracks/medias/{id_al}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, discord_id: int, id_al: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerAddMediaResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/waicolle/players/{discord_id}/tracks/medias/{id_al}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, discord_id: int, id_al: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerRemoveMediaResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/waicolle/players/{discord_id}/tracks/medias/{id_al}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, discord_id: int, id_al: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerStaffStatsResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/waicolle/players/{discord_id}/tracks/staffs/{id_al}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, discord_id: int, id_al: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerAddStaffResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/waicolle/players/{discord_id}/tracks/staffs/{id_al}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, discord_id: int, id_al: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerRemoveStaffResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/waicolle/players/{discord_id}/tracks/staffs/{id_al}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, discord_id: int, id: UUID, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerCollectionStatsResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/waicolle/players/{discord_id}/tracks/collections/{id}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, discord_id: int, id: UUID, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerAddCollectionResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/waicolle/players/{discord_id}/tracks/collections/{id}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, discord_id: int, id: UUID, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], PlayerRemoveCollectionResult]
        | Success[Literal[204], None]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/waicolle/players/{discord_id}/tracks/collections/{id}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        discord_id: int,
        filter: Literal['FULL', 'LOCKED', 'UNLOCKED', 'ASCENDED', 'EDGED', 'CUSTOM'],
        client_id: UUID | None = None,
    ) -> (
        Success[Literal[200], CollageResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/waicolle/players/{discord_id}/collages/waifus'
        params = dict(
            filter=filter,
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        discord_id: int,
        id_al: int,
        owned_only: int | None = None,
        client_id: UUID | None = None,
    ) -> (
        Success[Literal[200], MediaAlbumResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/waicolle/players/{discord_id}/collages/medias/{id_al}'
        params = dict(
            owned_only=owned_only,
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        discord_id: int,
        id_al: int,
        owned_only: int | None = None,
        client_id: UUID | None = None,
    ) -> (
        Success[Literal[200], StaffAlbumResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/waicolle/players/{discord_id}/collages/staffs/{id_al}'
        params = dict(
            owned_only=owned_only,
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        discord_id: int,
        id: UUID,
        owned_only: int | None = None,
        client_id: UUID | None = None,
    ) -> (
        Success[Literal[200], CollectionAlbumResult]
        | Error[Literal[404], HTTPExceptionModel]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/waicolle/players/{discord_id}/collages/collections/{id}'
        params = dict(
            owned_only=owned_only,
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        discord_id: int | None = None,
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
        url = f'{self.server_url}/waicolle/waifus'
        params = dict(
            ids=ids,
            discord_id=discord_id,
            level=level,
            locked=locked,
            trade_locked=trade_locked,
            blooded=blooded,
            nanaed=nanaed,
            custom_collage=custom_collage,
            as_og=as_og,
            ascended=ascended,
            edged=edged,
            ascendable=ascendable,
            chara_id_al=chara_id_al,
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, ids: str, body: BulkUpdateWaifusBody, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], list[WaifuBulkUpdateResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/waicolle/waifus'
        params = dict(
            ids=ids,
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/waicolle/waifus/reroll'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, discord_id: int, client_id: UUID | None = None
    ) -> (
        Success[Literal[200], list[WaifuSelectResult]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[403], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/waicolle/waifus/expired'
        params = dict(
            discord_id=discord_id,
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/waicolle/waifus/{id}/customs'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/waicolle/waifus/{id}/reorder'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/waicolle/waifus/{id}/ascend'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/waicolle/waifus/{id}/blood'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/waicolle/trades'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/waicolle/trades'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/waicolle/trades/offerings'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/waicolle/trades/{id}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/waicolle/trades/{id}/commit'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/waicolle/collections'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/waicolle/collections/autocomplete'
        params = dict(
            search=search,
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/waicolle/collections/{id}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/waicolle/collections/{id}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/waicolle/collections/{id}/medias/{id_al}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/waicolle/collections/{id}/medias/{id_al}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/waicolle/collections/{id}/staffs/{id_al}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/waicolle/collections/{id}/staffs/{id_al}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/waicolle/coupons'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/waicolle/coupons'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/waicolle/coupons/{code}'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        self, discord_id: int
    ) -> (
        Success[Literal[200], list[RollData]]
        | Error[Literal[401], HTTPExceptionModel]
        | Error[Literal[422], HTTPValidationError]
    ):
        url = f'{self.server_url}/waicolle/settings/rolls'
        params = dict(
            discord_id=discord_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
        url = f'{self.server_url}/waicolle/exports/waifus'
        params = dict(
            client_id=client_id,
        )
        params = {
            k: v.value if isinstance(v, Enum) else v for k, v in params.items() if v is not None
        }

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
    def __init__(self, server_url: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.amq: AmqModule = AmqModule(self, server_url)
        self.anilist: AnilistModule = AnilistModule(self, server_url)
        self.calendar: CalendarModule = CalendarModule(self, server_url)
        self.client: ClientModule = ClientModule(self, server_url)
        self.histoire: HistoireModule = HistoireModule(self, server_url)
        self.pot: PotModule = PotModule(self, server_url)
        self.presence: PresenceModule = PresenceModule(self, server_url)
        self.projection: ProjectionModule = ProjectionModule(self, server_url)
        self.quizz: QuizzModule = QuizzModule(self, server_url)
        self.reminder: ReminderModule = ReminderModule(self, server_url)
        self.role: RoleModule = RoleModule(self, server_url)
        self.user: UserModule = UserModule(self, server_url)
        self.waicolle: WaicolleModule = WaicolleModule(self, server_url)


def get_session(server_url: str, *args, **kwargs) -> ClientSession:
    return ClientSession(server_url, *args, **kwargs)
