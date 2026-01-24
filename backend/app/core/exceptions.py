"""
AutoCloud Architect - Custom Exceptions
"""
from fastapi import HTTPException, status


class AutoCloudException(Exception):
    """Base exception for AutoCloud Architect."""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class SageMakerException(AutoCloudException):
    """Exception for SageMaker-related errors."""
    pass


class ProvisioningException(AutoCloudException):
    """Exception for AWS provisioning errors."""
    pass


class DeploymentException(AutoCloudException):
    """Exception for deployment errors."""
    pass


class ValidationException(AutoCloudException):
    """Exception for input validation errors."""
    pass


# HTTP Exceptions
def not_found_exception(resource: str, resource_id: str) -> HTTPException:
    """Create a 404 Not Found exception."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{resource} with ID '{resource_id}' not found"
    )


def bad_request_exception(message: str) -> HTTPException:
    """Create a 400 Bad Request exception."""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=message
    )


def internal_error_exception(message: str = "An internal error occurred") -> HTTPException:
    """Create a 500 Internal Server Error exception."""
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=message
    )
