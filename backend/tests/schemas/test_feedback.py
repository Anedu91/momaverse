import pytest
from pydantic import ValidationError

from api.schemas.feedback import FeedbackCreate


def test_create_valid():
    fb = FeedbackCreate(message="Great site!")
    assert fb.message == "Great site!"
    assert fb.page_url is None


def test_create_with_page_url():
    fb = FeedbackCreate(message="Bug here", page_url="/events")
    assert fb.page_url == "/events"


def test_create_message_required():
    with pytest.raises(ValidationError):
        FeedbackCreate()


def test_create_message_max_length():
    with pytest.raises(ValidationError):
        FeedbackCreate(message="x" * 10_001)


def test_create_page_url_max_length():
    with pytest.raises(ValidationError):
        FeedbackCreate(message="ok", page_url="x" * 501)
