import logging
from typing import Any, Callable

from app.errors.mapping import spec_for
from app.logging.events import Log, NVIEvent
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
            Log.event(
                logger,
                Log.REFERRAL_ACCESS_DENIED,
                "Bundle entry denied: missing scope",
                ura_number=str(authenticated_ura),
                endpoint=endpoint,
            )
            return BundleEntry(response=EntryResponse.make_forbidden_respone(msg=f"Bundle.entry.{index}: {error}"))

        if self.requires_managing_request(method, resolved_url) and not AuthContextService.is_managing_request(ctx):
            error = UnauthorizedManagingRequestError()
            Log.event(
                logger,
                Log.REFERRAL_ACCESS_DENIED,
                "Bundle entry denied: not a managing request",
                ura_number=str(authenticated_ura),
                endpoint=endpoint,
            )
            return BundleEntry(response=EntryResponse.make_forbidden_respone(msg=f"Bundle.entry.{index}: {error}"))

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

                try:
                    params = LocalizationListParams.model_validate(resolved_url.params)
                except ValueError as e:
                    return BundleEntry(
                        response=EntryResponse.make_validation_response(
                            f"Bundle.entry.{index}.request: invalid url parameter: {e}"
                        )
                    )

                return self._entry_result(
                    index,
                    authenticated_ura,
                    lambda: BundleEntry(
                        resource=self.localizaton_list_service.query(
                            params, authenticated_ura, organization_name=organization_name
                        ),
                        response=EntryResponse.make_good_response(),
                    ),
                    failure_event=Log.LOCALIZATION_FAILED,
                    failure_msg="Localization failed",
                )

            case "POST":
                validated = self._validate_post_resource(entry, authenticated_ura, index)
                if isinstance(validated, BundleEntry):
                    return validated

                resource = validated
                return self._entry_result(
                    index,
                    authenticated_ura,
                    lambda: BundleEntry(
                        resource=self.localizaton_list_service.create(
                            resource, authenticated_ura, organization_name=organization_name
                        ),
                        response=EntryResponse.make_good_response(msg="Resource has been created successfully"),
                    ),
                    failure_event=Log.REFERRAL_REGISTRATION_FAILED,
                    failure_msg="Referral registration failed",
                )

            case "DELETE":
                if resolved_url.id:
                    resource_id = resolved_url.id
                    return self._entry_result(
                        index,
                        authenticated_ura,
                        lambda: self._delete_by_id_entry(resource_id, authenticated_ura, organization_name),
                    )

                try:
                    params = LocalizationListParams.model_validate(resolved_url.params)
                except ValueError:
                    return BundleEntry(
                        response=EntryResponse.make_validation_response(
                            f"Bundle.entry.{index}.request: invalid url parameter"
                        )
                    )

                delete_params = params
                return self._entry_result(
                    index,
                    authenticated_ura,
                    lambda: self._delete_by_query_entry(delete_params, authenticated_ura, organization_name),
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
        failure_event: NVIEvent | None = None,
        failure_msg: str = "",
    ) -> BundleEntry[Any]:
        """Run an entry's service call, mapping any raised exception to an error entry.

        A bundle reports per-entry outcomes, so a failing entry becomes an error entry
        rather than failing the whole request. The status comes from :func:`spec_for`,
        giving entries the same exception-to-status mapping the routers use. Operations
        that record a failure event pass ``failure_event`` with its ``failure_msg``.
        """
        try:
            return action()
        except Exception as exc:
            status_code = spec_for(exc).http_status
            if failure_event is not None:
                Log.event(
                    logger,
                    failure_event,
                    failure_msg,
                    ura_number=str(authenticated_ura),
                    http_status=status_code,
                    error_reason=str(exc),
                )
            return BundleEntry(
                response=EntryResponse.make_error_response(
                    msg=f"Bundle.entry.{index}: {exc}",
                    status=str(status_code),
                )
            )

    def _delete_by_id_entry(
        self, resource_id: Any, authenticated_ura: UraNumber, organization_name: str
    ) -> BundleEntry[Any]:
        outcome, status_code = self.localizaton_list_service.delete(
            resource_id, authenticated_ura, organization_name=organization_name
        )
        return BundleEntry(response=EntryResponse(status=str(status_code), outcome=outcome))

    def _delete_by_query_entry(
        self, params: LocalizationListParams, authenticated_ura: UraNumber, organization_name: str
    ) -> BundleEntry[Any]:
        outcome, status_code = self.localizaton_list_service.delete_by_query(
            params, authenticated_ura, organization_name=organization_name
        )
        return BundleEntry(response=EntryResponse(status=str(status_code), outcome=outcome))

    def _validate_post_resource(
        self, entry: BundleEntry[Any], authenticated_ura: UraNumber, index: int
    ) -> LocalizationList | BundleEntry[Any]:
        """Return the validated ``LocalizationList`` or an error ``BundleEntry``."""
        if entry.resource is None:
            Log.event(
                logger,
                Log.REFERRAL_REGISTRATION_FAILED,
                "Referral registration failed",
                ura_number=str(authenticated_ura),
                http_status=422,
                error_reason=f"Bundle.entry.{index}: resource cannot be empty",
            )
            return BundleEntry(
                response=EntryResponse.make_validation_response(msg=f"Bundle.entry.{index}: resource cannot be empty")
            )

        if not isinstance(entry.resource, LocalizationList):
            Log.event(
                logger,
                Log.REFERRAL_REGISTRATION_FAILED,
                "Referral registration failed",
                ura_number=str(authenticated_ura),
                http_status=422,
                error_reason=f"Bundle.entry.{index}: invalid List resource",
            )
            return BundleEntry(
                response=EntryResponse.make_validation_response(f"Bundle.entry.{index}: invalid List resource")
            )

        return entry.resource

    @staticmethod
    def required_scope(method: str, resolved_url: EntryRequestDto) -> AuthorizationScope | None:
        """
        Scope an entry needs, mirroring the standalone /fhir/List routes. Returns None for
        methods that are rejected as unsupported further down, so they keep that response.
        """
        match method:
            case "POST":
                return AuthorizationScope.CREATE
            case "DELETE":
                return AuthorizationScope.DELETE
            case "GET":
                # A read by id is `nvi:read`; a search is scoped by what it searches for.
                return AuthorizationScope.READ if resolved_url.id else BundleService._query_scope(resolved_url.params)
            case _:
                return None

    @staticmethod
    def _query_scope(params: dict[str, str] | None) -> AuthorizationScope:
        """Scope a search entry needs: `nvi:localize` for a localization, `nvi:read` otherwise.

        Decided by ``LocalizationListParams.is_localize_params`` so a search is scoped the
        same whether it arrives standalone or inside a bundle - the standalone route
        reaches the same rule through ``require_scope_for_localization_query``.

        Params that do not parse fall back to the stricter scope. Such an entry is
        rejected as invalid further down, so this only avoids admitting it on the weaker
        scope in the meantime.
        """
        try:
            parsed = LocalizationListParams.model_validate(params or {})
        except ValueError:
            return AuthorizationScope.LOCALIZE

        return AuthorizationScope.LOCALIZE if parsed.is_localize_params() else AuthorizationScope.READ

    @staticmethod
    def requires_managing_request(method: str, resolved_url: EntryRequestDto) -> bool:
        """
        Whether an entry is a managing operation and so needs a source_id, mirroring the
        standalone /fhir/List routes: creating and deleting by query do, reads and
        delete-by-id do not.
        """
        if method == "POST":
            return True

        return method == "DELETE" and resolved_url.id is None

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
