from unittest.mock import Mock

import pytest
from requests.exceptions import ConnectTimeout, ReadTimeout, Timeout
from urllib3.exceptions import (
    ConnectTimeoutError,
    ReadTimeoutError,
    TimeoutError as Urllib3TimeoutError,
)

from app.core.error_handler import (
    DuplicateReviewError,
    OCIPersistenceError,
    OCITimeoutError,
    map_oci_error,
)


@pytest.mark.parametrize(
    "timeout_type",
    [
        Timeout,
        ConnectTimeout,
        ReadTimeout,
        Urllib3TimeoutError,
        ConnectTimeoutError,
        ReadTimeoutError,
    ],
)
def test_map_oci_error_maps_request_and_urllib3_timeouts(timeout_type):
    error = Mock(spec=timeout_type)
    error.__class__ = timeout_type

    assert isinstance(map_oci_error(error), OCITimeoutError)


def test_map_oci_error_maps_oci_request_exception_with_timeout_cause():
    from app.core import error_handler

    oci_error = Mock(spec=error_handler.OCIRequestException)
    oci_error.__class__ = error_handler.OCIRequestException
    oci_error.__cause__ = ReadTimeout("read timed out")

    assert isinstance(map_oci_error(oci_error), OCITimeoutError)


def test_map_oci_error_maps_builtin_timeout():
    assert isinstance(map_oci_error(TimeoutError()), OCITimeoutError)


def test_map_oci_error_keeps_non_timeout_oci_request_exception_generic():
    from app.core import error_handler

    oci_error = Mock(spec=error_handler.OCIRequestException)
    oci_error.__class__ = error_handler.OCIRequestException

    assert isinstance(map_oci_error(oci_error), OCIPersistenceError)


def test_map_oci_error_maps_412_to_duplicate_review_error():
    error = Mock(status=412)

    assert isinstance(
        map_oci_error(error, duplicate_on_precondition=True), DuplicateReviewError
    )
