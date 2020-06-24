class Error(Exception):
    """The base error for all formaldict errors"""


class SchemaError(Error):
    """When an issue is found in the user-supplied schema"""


class ValidationError(Error):
    """When a schema validation error happens"""
