import logging
from typing import Any

from app.exceptions.fhir_exception import FHIRException
from app.models.fhir.bundle import Bundle, BundleEntry, EntryRequestDto, EntryResponse
from app.models.fhir.resources.localization_list.request import LocalizationListParams
from app.models.fhir.resources.localization_list.resource import LocalizationList
from app.models.ura import UraNumber
from app.services.fhir.localization_list import LocalizationListService

logger = logging.getLogger(__name__)


class BundleService:
    def __init__(
        self,
        localisation_list_service: LocalizationListService,
    ) -> None:
        self.localizaton_list_service = localisation_list_service

    def process_entry(self, authenticated_ura: UraNumber, entry: BundleEntry[Any], index: int) -> BundleEntry[Any]:
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

        match method:
            case "GET":
                if resolved_url.id:
                    try:
                        results = self.localizaton_list_service.get(resolved_url.id, authenticated_ura)
                        return BundleEntry(
                            resource=results,
                            response=EntryResponse.make_good_response("Resource has been retrieved successfully"),
                        )
                    except FHIRException as e:
                        return BundleEntry(
                            response=EntryResponse.make_error_response(
                                msg=f"Bundle.entry.{index}: {e.outcome}",
                                status=str(e.status_code),
                            )
                        )
                try:
                    params = LocalizationListParams.model_validate(resolved_url.params)
                except ValueError:
                    return BundleEntry(
                        response=EntryResponse.make_validation_response(
                            f"Bundle.entry.{index}.request: invalid url parameter"
                        )
                    )

                try:
                    query_results = self.localizaton_list_service.query(params, authenticated_ura)
                    return BundleEntry(
                        resource=query_results,
                        response=EntryResponse.make_good_response(),
                    )

                except FHIRException as e:
                    return BundleEntry(
                        response=EntryResponse.make_error_response(
                            f"Bundle.entry.{index}: {e.outcome}",
                            status=str(e.status_code),
                        )
                    )

            case "POST":
                if entry.resource is None:
                    return BundleEntry(
                        response=EntryResponse.make_validation_response(
                            msg=f"Bundle.entry.{index}: resource cannot be empty"
                        )
                    )

                resource = entry.resource
                if not isinstance(resource, LocalizationList):
                    return BundleEntry(
                        response=EntryResponse.make_validation_response(f"Bundle.entry.{index}: invalid List resource")
                    )

                try:
                    results = self.localizaton_list_service.create(resource, authenticated_ura)
                    return BundleEntry(
                        resource=resource,
                        response=EntryResponse.make_good_response(msg="Resource has been created successfully"),
                    )
                except FHIRException as e:
                    return BundleEntry(
                        response=EntryResponse.make_error_response(
                            msg=f"Bundle.entry.{index}: {str(e.outcome)}",
                            status=str(e.status_code),
                        )
                    )

            case "DELETE":
                if resolved_url.id:
                    try:
                        outcome, status_code = self.localizaton_list_service.delete(resolved_url.id, authenticated_ura)
                        return BundleEntry(response=EntryResponse(status=str(status_code), outcome=outcome))
                    except FHIRException as e:
                        return BundleEntry(
                            response=EntryResponse.make_error_response(
                                msg=f"Bundle.entry.{index}: {e.outcome}",
                                status=str(e.status_code),
                            )
                        )
                try:
                    params = LocalizationListParams.model_validate(resolved_url.params)
                except ValueError:
                    return BundleEntry(
                        response=EntryResponse.make_validation_response(
                            f"Bundle.entry.{index}.request: invalid url parameter"
                        )
                    )
                outcome, status_code = self.localizaton_list_service.delete_by_query(params, authenticated_ura)

                return BundleEntry(response=EntryResponse(status=str(status_code), outcome=outcome))

            case _:
                return BundleEntry(
                    response=EntryResponse.make_forbidden_respone(
                        msg=f"Bundle.entry.{index}.request.method {method} not supported"
                    )
                )

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
