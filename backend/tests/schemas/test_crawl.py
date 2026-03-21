from api.models.base import CrawlJobStatus, CrawlResultStatus
from api.schemas.crawl import (
    CrawlContentResponse,
    CrawlJobDetailResponse,
    CrawlJobListItem,
    CrawlJobResponse,
    CrawlResultDetailResponse,
    CrawlResultResponse,
    ExtractedEventListItem,
    ExtractedEventResponse,
)

from tests.schemas.helpers import (
    make_crawl_content_obj,
    make_crawl_job_obj,
    make_crawl_result_obj,
    make_extracted_event_obj,
)

# ---------------------------------------------------------------------------
# CrawlContentResponse
# ---------------------------------------------------------------------------


def test_crawl_content_response_from_orm():
    obj = make_crawl_content_obj()
    resp = CrawlContentResponse.model_validate(obj, from_attributes=True)
    assert resp.id == 1
    assert resp.crawled_content == "<html>content</html>"
    assert resp.extracted_content == "extracted text"


def test_crawl_content_response_nullable():
    obj = make_crawl_content_obj(crawled_content=None, extracted_content=None)
    resp = CrawlContentResponse.model_validate(obj, from_attributes=True)
    assert resp.crawled_content is None
    assert resp.extracted_content is None


# ---------------------------------------------------------------------------
# ExtractedEventResponse / ExtractedEventListItem
# ---------------------------------------------------------------------------


def test_extracted_event_response_from_orm():
    obj = make_extracted_event_obj(
        name="Test Event",
        location_name="MoMA",
        occurrences=[{"date": "2026-01-01"}],
        tags=["art", "free"],
    )
    resp = ExtractedEventResponse.model_validate(obj, from_attributes=True)
    assert resp.name == "Test Event"
    assert resp.location_name == "MoMA"
    assert resp.occurrences == [{"date": "2026-01-01"}]
    assert resp.tags == ["art", "free"]


def test_extracted_event_list_item_from_orm():
    obj = make_extracted_event_obj(name="Listed Event", location_name="Venue")
    item = ExtractedEventListItem.model_validate(obj, from_attributes=True)
    assert item.id == 1
    assert item.name == "Listed Event"
    assert item.location_name == "Venue"


# ---------------------------------------------------------------------------
# CrawlResultResponse / CrawlResultDetailResponse
# ---------------------------------------------------------------------------


def test_crawl_result_response_from_orm():
    obj = make_crawl_result_obj(status="crawled")
    resp = CrawlResultResponse.model_validate(obj, from_attributes=True)
    assert resp.id == 1
    assert resp.status == CrawlResultStatus.crawled


def test_crawl_result_detail_response_from_orm():
    obj = make_crawl_result_obj(
        extracted_events=[make_extracted_event_obj()],
        content=make_crawl_content_obj(),
    )
    resp = CrawlResultDetailResponse.model_validate(obj, from_attributes=True)
    assert len(resp.extracted_events) == 1
    assert resp.content is not None


def test_crawl_result_detail_response_no_content():
    obj = make_crawl_result_obj(extracted_events=[], content=None)
    resp = CrawlResultDetailResponse.model_validate(obj, from_attributes=True)
    assert resp.extracted_events == []
    assert resp.content is None


# ---------------------------------------------------------------------------
# CrawlJobResponse / CrawlJobDetailResponse / CrawlJobListItem
# ---------------------------------------------------------------------------


def test_crawl_job_response_from_orm():
    obj = make_crawl_job_obj()
    resp = CrawlJobResponse.model_validate(obj, from_attributes=True)
    assert resp.id == 1
    assert resp.status == CrawlJobStatus.running
    assert resp.completed_at is None


def test_crawl_job_detail_response_from_orm():
    obj = make_crawl_job_obj(results=[make_crawl_result_obj()])
    resp = CrawlJobDetailResponse.model_validate(obj, from_attributes=True)
    assert len(resp.results) == 1


def test_crawl_job_detail_response_empty_results():
    obj = make_crawl_job_obj(results=[])
    resp = CrawlJobDetailResponse.model_validate(obj, from_attributes=True)
    assert resp.results == []


def test_crawl_job_list_item_from_orm():
    obj = make_crawl_job_obj(status="completed")
    item = CrawlJobListItem.model_validate(obj, from_attributes=True)
    assert item.status == CrawlJobStatus.completed
