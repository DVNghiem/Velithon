"""Constants for OpenAPI specification generation in Velithon framework.

This module defines constants used in OpenAPI/Swagger documentation generation
including HTTP methods, reference prefixes, and schema templates.
"""

METHODS_WITH_BODY = {'GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'PATCH'}
REF_PREFIX = '#/components/schemas/'
REF_TEMPLATE = '#/components/schemas/{model}'
