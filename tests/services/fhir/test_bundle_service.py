from typing import Any, List, Literal
from uuid import uuid4

import pytest

from app.models.auth.context import AuthContext, AuthenticationClaims
from app.models.auth.data import AuthorizationScope
from app.models.fhir.bundle import BundleEntry, EntryRequest
from app.models.fhir.resources.localization_list.resource import LocalizationList
from app.models.ura import UraNumber
from app.services.fhir.bundle import BundleService

TEST_URA = UraNumber("00000001")
TEST_ORG_NAME = "Test Organization"
TEST_SOURCE_ID = "SRC-001"

RESOURCE_ID = uuid4()
QUERY_URL = "List?subject:identifier=pseudonym-value&code=MEDAFSPRAAK"
ID_URL = f"List/{RESOURCE_ID}"

ALL_SCOPES = [
    AuthorizationScope.CREATE,
    AuthorizationScope.READ,
    AuthorizationScope.DELETE,
    AuthorizationScope.LOCALIZE,
]


class LocalizationListServiceSpy:
    """
    Stands in for LocalizationListService so we can assert an entry never reaches it when
    the caller lacks the scope for that entry.
    """

    def __init__(self) -> None:
        self.calls: List[str] = []

    def create(self, *_args: Any, **_kwargs: Any) -> Any:
        self.calls.append("create")
        return None

    def get(self, *_args: Any, **_kwargs: Any) -> Any:
        self.calls.append("get")
        return None

    def query(self, *_args: Any, **_kwargs: Any) -> Any:
        self.calls.append("query")
        return None

    def delete(self, *_args: Any, **_kwargs: Any) -> Any:
        self.calls.append("delete")
        return None, 200

    def delete_by_query(self, *_args: Any, **_kwargs: Any) -> Any:
        self.calls.append("delete_by_query")
        return None, 200


@pytest.fixture()
def service() -> LocalizationListServiceSpy:
    return LocalizationListServiceSpy()


@pytest.fixture()
def bundle_service(service: LocalizationListServiceSpy) -> BundleService:
    return BundleService(service)  # type: ignore[arg-type]


HttpMethod = Literal["POST", "DELETE", "GET", "PUT"]


def make_entry(method: HttpMethod, url: str, resource: LocalizationList | None = None) -> BundleEntry[Any]:
    return BundleEntry(request=EntryRequest(method=method, url=url), resource=resource)


def make_ctx(scopes: List[AuthorizationScope], source_id: str | None = TEST_SOURCE_ID) -> AuthContext:
    return AuthContext(
        claims=AuthenticationClaims(
            ura_number=TEST_URA,
            organization_name=TEST_ORG_NAME,
            source_id=source_id,
        ),
        scope=scopes,
        audience="nvi.service",
    )


def process(
    bundle_service: BundleService,
    entry: BundleEntry[Any],
    scopes: List[AuthorizationScope],
    index: int = 0,
    source_id: str | None = TEST_SOURCE_ID,
) -> BundleEntry[Any]:
    return bundle_service.process_entry(
        ctx=make_ctx(scopes, source_id=source_id),
        entry=entry,
        index=index,
    )


class TestRequiredScope:
    @pytest.mark.parametrize(
        ("method", "url", "required"),
        [
            ("POST", "List", AuthorizationScope.CREATE),
            ("GET", ID_URL, AuthorizationScope.READ),
            ("GET", QUERY_URL, AuthorizationScope.LOCALIZE),
            ("DELETE", ID_URL, AuthorizationScope.DELETE),
            ("DELETE", QUERY_URL, AuthorizationScope.DELETE),
        ],
    )
    def test_denies_entry_without_required_scope(
        self,
        bundle_service: BundleService,
        service: LocalizationListServiceSpy,
        method: HttpMethod,
        url: str,
        required: AuthorizationScope,
    ) -> None:
        scopes = [s for s in ALL_SCOPES if s != required]

        result = process(bundle_service, make_entry(method, url), scopes)

        assert result.response is not None
        assert result.response.status == "403"
        assert service.calls == []

    @pytest.mark.parametrize(
        ("method", "url", "required", "expected_call"),
        [
            ("GET", ID_URL, AuthorizationScope.READ, "get"),
            ("GET", QUERY_URL, AuthorizationScope.LOCALIZE, "query"),
            ("DELETE", ID_URL, AuthorizationScope.DELETE, "delete"),
            ("DELETE", QUERY_URL, AuthorizationScope.DELETE, "delete_by_query"),
        ],
    )
    def test_allows_entry_with_required_scope(
        self,
        bundle_service: BundleService,
        service: LocalizationListServiceSpy,
        method: HttpMethod,
        url: str,
        required: AuthorizationScope,
        expected_call: str,
    ) -> None:
        process(bundle_service, make_entry(method, url), [required])

        assert service.calls == [expected_call]

    def test_read_scope_does_not_grant_search(
        self,
        bundle_service: BundleService,
        service: LocalizationListServiceSpy,
    ) -> None:
        result = process(bundle_service, make_entry("GET", QUERY_URL), [AuthorizationScope.READ])

        assert result.response is not None
        assert result.response.status == "403"
        assert service.calls == []

    def test_localize_scope_does_not_grant_read_by_id(
        self,
        bundle_service: BundleService,
        service: LocalizationListServiceSpy,
    ) -> None:
        result = process(bundle_service, make_entry("GET", ID_URL), [AuthorizationScope.LOCALIZE])

        assert result.response is not None
        assert result.response.status == "403"
        assert service.calls == []

    def test_empty_scope_denies_every_entry(
        self,
        bundle_service: BundleService,
        service: LocalizationListServiceSpy,
    ) -> None:
        entries: List[tuple[HttpMethod, str]] = [
            ("POST", "List"),
            ("GET", ID_URL),
            ("GET", QUERY_URL),
            ("DELETE", ID_URL),
        ]
        for method, url in entries:
            result = process(bundle_service, make_entry(method, url), [])

            assert result.response is not None
            assert result.response.status == "403"

        assert service.calls == []

    def test_unsupported_method_stays_unsupported(
        self,
        bundle_service: BundleService,
        service: LocalizationListServiceSpy,
    ) -> None:
        result = process(bundle_service, make_entry("PUT", ID_URL), ALL_SCOPES)

        assert result.response is not None
        assert result.response.status == "403"
        assert result.response.outcome is not None
        assert "not supported" in str(result.response.outcome.model_dump())
        assert service.calls == []

    def test_denial_is_per_entry(
        self,
        bundle_service: BundleService,
        service: LocalizationListServiceSpy,
    ) -> None:
        """An entry the caller may not perform must not block the entries it may."""
        allowed = process(bundle_service, make_entry("GET", ID_URL), [AuthorizationScope.READ], index=0)
        denied = process(bundle_service, make_entry("DELETE", ID_URL), [AuthorizationScope.READ], index=1)

        assert denied.response is not None
        assert denied.response.status == "403"
        assert allowed.response is not None
        assert allowed.response.status != "403"
        assert service.calls == ["get"]

    def test_denial_message_names_the_entry_and_scope(
        self,
        bundle_service: BundleService,
    ) -> None:
        result = process(bundle_service, make_entry("DELETE", ID_URL), [AuthorizationScope.READ], index=3)

        assert result.response is not None
        assert result.response.outcome is not None
        message = str(result.response.outcome.model_dump())
        assert "Bundle.entry.3" in message
        assert AuthorizationScope.DELETE.value in message


class TestManagingRequest:
    """
    Managing operations need a source_id, mirroring `POST /fhir/List` and `DELETE /fhir/List`.
    """

    @pytest.mark.parametrize(
        ("method", "url", "required"),
        [
            ("POST", "List", AuthorizationScope.CREATE),
            ("DELETE", QUERY_URL, AuthorizationScope.DELETE),
        ],
    )
    def test_denies_managing_entry_without_source_id(
        self,
        bundle_service: BundleService,
        service: LocalizationListServiceSpy,
        method: HttpMethod,
        url: str,
        required: AuthorizationScope,
    ) -> None:
        result = process(bundle_service, make_entry(method, url), [required], source_id=None)

        assert result.response is not None
        assert result.response.status == "403"
        assert service.calls == []

    @pytest.mark.parametrize(
        ("method", "url", "required", "expected_call"),
        [
            ("GET", ID_URL, AuthorizationScope.READ, "get"),
            ("GET", QUERY_URL, AuthorizationScope.LOCALIZE, "query"),
            ("DELETE", ID_URL, AuthorizationScope.DELETE, "delete"),
        ],
    )
    def test_non_managing_entry_does_not_need_source_id(
        self,
        bundle_service: BundleService,
        service: LocalizationListServiceSpy,
        method: HttpMethod,
        url: str,
        required: AuthorizationScope,
        expected_call: str,
    ) -> None:
        process(bundle_service, make_entry(method, url), [required], source_id=None)

        assert service.calls == [expected_call]

    def test_managing_entry_proceeds_with_source_id(
        self,
        bundle_service: BundleService,
        service: LocalizationListServiceSpy,
    ) -> None:
        process(bundle_service, make_entry("DELETE", QUERY_URL), [AuthorizationScope.DELETE])

        assert service.calls == ["delete_by_query"]

    def test_scope_is_checked_before_source_id(
        self,
        bundle_service: BundleService,
    ) -> None:
        """A caller missing both should hear about the scope, not the source_id."""
        result = process(bundle_service, make_entry("POST", "List"), [], source_id=None)

        assert result.response is not None
        assert result.response.outcome is not None
        message = str(result.response.outcome.model_dump())
        assert AuthorizationScope.CREATE.value in message
        assert "source_id" not in message

    def test_denial_message_names_the_entry_and_source_id(
        self,
        bundle_service: BundleService,
    ) -> None:
        result = process(
            bundle_service,
            make_entry("POST", "List"),
            [AuthorizationScope.CREATE],
            index=2,
            source_id=None,
        )

        assert result.response is not None
        assert result.response.outcome is not None
        message = str(result.response.outcome.model_dump())
        assert "Bundle.entry.2" in message
        assert "source_id" in message
