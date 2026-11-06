class NetArchitectError(Exception):
    """Base class for all NetArchitect errors."""


class PhysicalDistanceViolationError(NetArchitectError):
    """Raised when a medium is requested beyond its physical reach."""


class AddressSpaceExhaustedError(NetArchitectError):
    """Raised when the root prefix cannot satisfy all host requests."""


class InvalidParameterError(NetArchitectError):
    """Raised for malformed or out-of-range input parameters."""