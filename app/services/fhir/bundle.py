import logging
from typing import Any, Callable

import gfmodules.logging as gflog
from gfmodules.logging import LogEvent

from app.errors.mapping import spec_for
from app.logging.events import Log
from app.models.auth.context import AuthContext
from app.models.auth.data import AuthorizationScope
from app.models.fhir.bundle import Bundle, BundleEntry, EntryRequestDto, EntryResponse
from app.models.fhir.resources.localization_list.request import LocalizationListParams
from app.models.fhir.resources.localization_list.resource import LocalizationList
from app.models.ura import UraNumber
from app.services.auth.auth_context import AuthContextService
from app.services.exceptions import (
    UnauthorizedManagingRequestError,
    UnauthorizedScopeError,
    UnauthorizedSourceError,
)
from app.services.fhir.localization_list import LocalizationListService

logger = logging.getLogger(__name__)


class BundleService:
    def __init__(
        self,
        localisation_list_service: LocalizationListService,
    ) -> None:
        self.localizaton_list_service = localisation_list_service

    def process_entry(self, ctx: AuthContext, entry: BundleEntry[Any], index: int) -> BundleEntry[Any]:
        authenticated_ura = ctx.claims.ura_number
        organization_name = ctx.claims.organization_name

        if entry.request is None:
            return BundleEntry(
                response=EntryResponse.make_validation_response(f"Bundle.entry.{index}.request is required")
            )

        if entry.request.method is None:
            return BundleEntry(
                response=EntryResponse.make_validation_response(f"Bundle.entry.{index}.request.method is required")
            )

        method = entry.request.method
        resolved_url = self.resolve_request_url(entry.request.url, index)
        if isinstance(resolved_url, BundleEntry):
            return resolved_url

        endpoint = f"{method} {entry.request.url}"

        required_scope = self.required_scope(method, resolved_url)
        if required_scope is not None and required_scope not in ctx.scope:
            error: Exception = UnauthorizedScopeError(ctx.scope, required_scope)
            gflog.emit(
                logger,
                Log.REFERRAL_ACCESS_DENIED,
                "Bundle entry denied: missing scope",
                fields={"ura_number": str(authenticated_ura), "endpoint": endpoint},
            )
            return BundleEntry(response=EntryResponse.make_forbidden_respone(msg=f"Bundle.entry.{index}: {error}"))

        if self.requires_managing_request(method) and not AuthContextService.is_managing_request(ctx):
            error = UnauthorizedManagingRequestError()
            gflog.emit(
                logger,
                Log.REFERRAL_ACCESS_DENIED,
                "Bundle entry denied: not a managing request",
                fields={"ura_number": str(authenticated_ura), "endpoint": endpoint},
            )
            return BundleEntry(response=EntryResponse.make_forbidden_respone(msg=f"Bundle.entry.{index}: {error}"))

        resource: LocalizationList | None = None
        if method == "POST":
            validated = self._validate_post_resource(entry, authenticated_ura, index)
            if isinstance(validated, BundleEntry):
                return validated
            resource = validated

        params: LocalizationListParams | None = None
        if method in ("GET", "DELETE") and resolved_url.id is None:
            parsed = self._parse_params(resolved_url, index)
            if isinstance(parsed, BundleEntry):
                return parsed
            params = parsed

        denied = self._deny_mismatched_source(ctx, resource, params, index, endpoint)
        if denied is not None:
            return denied

        match method:
            case "GET":
                if resolved_url.id:
                    resource_id = resolved_url.id
                    return self._entry_result(
                        index,
                        authenticated_ura,
                        lambda: BundleEntry(
                            resource=self.localizaton_list_service.get(
                                resource_id, authenticated_ura, organization_name=organization_name
                            ),
                            response=EntryResponse.make_good_response("Resource has been retrieved successfully"),
                        ),
                    )

                query_params = params
                assert query_params is not None  # noqa: S101 - parsed above for every id-less GET
                return self._entry_result(
                    index,
                    authenticated_ura,
                    lambda: BundleEntry(
                        resource=self.localizaton_list_service.query(
                            query_params, authenticated_ura, organization_name=organization_name
                        ),
                        response=EntryResponse.make_good_response(),
                    ),
                    failure_event=Log.LOCALIZATION_FAILED,
                    failure_msg="Localization failed",
                )

            case "POST":
                post_resource = resource
                assert post_resource is not None  # noqa: S101 - validated above for every POST
                return self._entry_result(
                    index,
                    authenticated_ura,
                    lambda: BundleEntry(
                        resource=self.localizaton_list_service.create(
                            post_resource, authenticated_ura, organization_name=organization_name
                        ),
                        response=EntryResponse.make_good_response(msg="Resource has been created successfully"),
                    ),
                    failure_event=Log.REFERRAL_REGISTRATION_FAILED,
                    failure_msg="Referral registration failed",
                )

            case "DELETE":
                managing_source = ctx.claims.source_id
                assert managing_source is not None  # noqa: S101 - guaranteed by the managing-request guard above

                if resolved_url.id:
                    resource_id = resolved_url.id
                    return self._entry_result(
                        index,
                        authenticated_ura,
                        lambda: self._delete_by_id_entry(
                            resource_id, authenticated_ura, managing_source, organization_name
                        ),
                    )

                delete_params = params
                assert delete_params is not None  # noqa: S101 - parsed above for every id-less DELETE
                return self._entry_result(
                    index,
                    authenticated_ura,
                    lambda: self._delete_by_query_entry(
                        delete_params, authenticated_ura, managing_source, organization_name
                    ),
                    failure_event=Log.LOCALIZATION_FAILED,
                    failure_msg="Localization failed",
                )

            case _:
                return BundleEntry(
                    response=EntryResponse.make_forbidden_respone(
                        msg=f"Bundle.entry.{index}.request.method {method} not supported"
                    )
                )

    def _entry_result(
        self,
        index: int,
        authenticated_ura: UraNumber,
        action: Callable[[], BundleEntry[Any]],
        *,
        failure_event: LogEvent | None = None,
        failure_msg: str = "",
    ) -> BundleEntry[Any]:
        """Run an entry's service call, mapping any raised exception to an error entry."""
        try:
            return action()
        except Exception as exc:
            status_code = spec_for(exc).http_status
            if failure_event is not None:
                gflog.emit(
                    logger,
                    failure_event,
                    failure_msg,
                    fields={"ura_number": str(authenticated_ura), "http_status": status_code, "error_reason": str(exc)},
                )
            return BundleEntry(
                response=EntryResponse.make_error_response(
                    msg=f"Bundle.entry.{index}: {exc}",
                    status=str(status_code),
                )
            )

    def _delete_by_id_entry(
        self, resource_id: Any, authenticated_ura: UraNumber, source: str, organization_name: str
    ) -> BundleEntry[Any]:
        outcome, status_code = self.localizaton_list_service.delete(
            resource_id, authenticated_ura, source, organization_name=organization_name
        )
        return BundleEntry(response=EntryResponse(status=str(status_code), outcome=outcome))

    def _delete_by_query_entry(
        self, params: LocalizationListParams, authenticated_ura: UraNumber, source: str, organization_name: str
    ) -> BundleEntry[Any]:
        outcome, status_code = self.localizaton_list_service.delete_by_query(
            params, authenticated_ura, source, organization_name=organization_name
        )
        return BundleEntry(response=EntryResponse(status=str(status_code), outcome=outcome))

    @staticmethod
    def _parse_params(resolved_url: EntryRequestDto, index: int) -> LocalizationListParams | BundleEntry[Any]:
        try:
            return LocalizationListParams.model_validate(resolved_url.params)
        except ValueError as e:
            return BundleEntry(
                response=EntryResponse.make_validation_response(
                    f"Bundle.entry.{index}.request: invalid url parameter: {e}"
                )
            )

    def _deny_mismatched_source(
        self,
        ctx: AuthContext,
        resource: LocalizationList | None,
        params: LocalizationListParams | None,
        index: int,
        endpoint: str,
    ) -> BundleEntry[Any] | None:
        """Reject an entry naming a source other than the caller's, mirroring the standalone routes.

        Returns ``None`` when the entry may proceed. An entry that names no source at all
        is left alone, so localization searches keep working for a caller without one.
        """
        try:
            entry_source = resource.get_device() if resource is not None else (params.source if params else None)
        except ValueError as e:
            # A source built on the wrong naming system, which the standalone route rejects
            # before it reaches the service too.
            return BundleEntry(
                response=EntryResponse.make_error_response(
                    msg=f"Bundle.entry.{index}: {e}",
                    status=str(spec_for(e).http_status),
                )
            )

        try:
            AuthContextService.assert_source_matches(ctx, entry_source)
        except UnauthorizedSourceError as error:
            gflog.emit(
                logger,
                Log.REFERRAL_ACCESS_DENIED,
                "Bundle entry denied: source does not match the authenticated source",
                fields={"ura_number": str(ctx.claims.ura_number), "endpoint": endpoint},
            )
            return BundleEntry(response=EntryResponse.make_forbidden_respone(msg=f"Bundle.entry.{index}: {error}"))

        return None

    def _validate_post_resource(
        self, entry: BundleEntry[Any], authenticated_ura: UraNumber, index: int
    ) -> LocalizationList | BundleEntry[Any]:
        """Return the validated ``LocalizationList`` or an error ``BundleEntry``."""
        if entry.resource is None:
            gflog.emit(
                logger,
                Log.REFERRAL_REGISTRATION_FAILED,
                "Referral registration failed",
                fields={
                    "ura_number": str(authenticated_ura),
                    "http_status": 422,
                    "error_reason": f"Bundle.entry.{index}: resource cannot be empty",
                },
            )
            return BundleEntry(
                response=EntryResponse.make_validation_response(msg=f"Bundle.entry.{index}: resource cannot be empty")
            )

        if not isinstance(entry.resource, LocalizationList):
            gflog.emit(
                logger,
                Log.REFERRAL_REGISTRATION_FAILED,
                "Referral registration failed",
                fields={
                    "ura_number": str(authenticated_ura),
                    "http_status": 422,
                    "error_reason": f"Bundle.entry.{index}: invalid List resource",
                },
            )
            return BundleEntry(
                response=EntryResponse.make_validation_response(f"Bundle.entry.{index}: invalid List resource")
            )

        return entry.resource

    @staticmethod
    def required_scope(method: str, resolved_url: EntryRequestDto) -> AuthorizationScope | None:
        match method:
            case "POST":
                return AuthorizationScope.CREATE
            case "DELETE":
                return AuthorizationScope.DELETE
            case "GET":
                return AuthorizationScope.READ if resolved_url.id else BundleService._query_scope(resolved_url.params)
            case _:
                return None

    @staticmethod
    def _query_scope(params: dict[str, str] | None) -> AuthorizationScope:
        try:
            parsed = LocalizationListParams.model_validate(params or {})
        except ValueError:
            return AuthorizationScope.LOCALIZE

        return AuthorizationScope.LOCALIZE if parsed.is_localize_params() else AuthorizationScope.READ

    @staticmethod
    def requires_managing_request(method: str) -> bool:
        """Whether an entry is a managing operation and so needs a source_id"""
        return method in ("POST", "DELETE")

    @staticmethod
    def validate_localization_bundle_structure(bundle: Bundle[Any]) -> bool:
        if len(bundle.entry) == 0 or bundle.entry is None:
            return False

        return True

    def resolve_request_url(self, url: str, index: int) -> EntryRequestDto | BundleEntry[LocalizationList]:
        try:
            request_dto = EntryRequestDto.from_url(url)
        except ValueError:
            return BundleEntry(
                response=EntryResponse.make_validation_response(f"Bundle.entry.{index}.request.url is malformed")
            )

        if request_dto.resource is None:
            return BundleEntry(
                response=EntryResponse.make_validation_response(f"Bundle.entry.{index}.request.url: resource not found")
            )

        if request_dto.resource != "List":
            return BundleEntry(
                response=EntryResponse.make_validation_response(
                    f"Bundle.entry.{index}.request.url unsupported {request_dto.resource} resource"
                )
            )

        if request_dto.id is not None and request_dto.params is not None:
            return BundleEntry(
                response=EntryResponse.make_validation_response(
                    f"Bundle.entry.{index}.request.url:  unsupported url for requested transaction"
                )
            )

        return request_dto
