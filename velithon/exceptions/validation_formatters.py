"""Custom validation error formatters for Velithon.

This module provides base classes and implementations for custom validation
error formatting to allow users to control how validation errors are presented.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError


class ValidationErrorFormatter(ABC):
    """Abstract base class for custom validation error formatters.

    Users can inherit from this class to create custom validation error formatters
    that control how validation errors are presented in API responses.
    """

    @abstractmethod
    def format_validation_error(
        self, error: ValidationError, field_name: str | None = None
    ) -> dict[str, Any]:
        """Format a validation error into a structured response.

        Args:
            error: The Pydantic ValidationError instance
            field_name: Optional field name where the error occurred

        Returns:
            Dictionary containing the formatted error response

        """
        pass

    def format_validation_errors(self, errors: list[dict[str, Any]]) -> dict[str, Any]:
        """Format multiple validation errors into a structured response.

        Args:
            errors: List of individual error dictionaries

        Returns:
            Dictionary containing the formatted errors response

        """
        # Default implementation: merge all errors into a single response
        all_errors = []
        for error_dict in errors:
            if isinstance(error_dict, dict):
                all_errors.append(error_dict)
        return {"errors": all_errors}


class DefaultValidationErrorFormatter(ValidationErrorFormatter):
    """Default validation error formatter that matches Velithon's standard format."""

    def format_validation_error(
        self, error: ValidationError, field_name: str | None = None
    ) -> dict[str, Any]:
        """Format a single validation error."""
        errors = []
        for err in error.errors():
            errors.append({
                'field': (
                    '.'.join(str(x) for x in err['loc'])
                    if err.get('loc') else field_name
                ),
                'message': err['msg'],
                'type': err['type'],
                'input': err.get('input')
            })

        return {
            'error': {
                'type': 'validation_error',
                'details': errors
            }
        }

    def format_validation_errors(self, errors: list[dict[str, Any]]) -> dict[str, Any]:
        """Format multiple validation errors."""
        all_details = []
        for error_dict in errors:
            if 'error' in error_dict and 'details' in error_dict['error']:
                all_details.extend(error_dict['error']['details'])
            else:
                all_details.append(error_dict)

        return {
            'error': {
                'type': 'validation_error',
                'details': all_details
            }
        }


class SimpleValidationErrorFormatter(ValidationErrorFormatter):
    """Simple validation error formatter with minimal structure."""

    def format_validation_error(
        self, error: ValidationError, field_name: str | None = None
    ) -> dict[str, Any]:
        """Format a single validation error in simple format."""
        errors = []
        for err in error.errors():
            field = (
                '.'.join(str(x) for x in err['loc'])
                if err.get('loc') else field_name
            )
            errors.append(f"{field}: {err['msg']}")

        return {
            'error': 'Validation failed',
            'messages': errors
        }

    def format_validation_errors(self, errors: list[dict[str, Any]]) -> dict[str, Any]:
        """Format multiple validation errors in simple format."""
        all_messages = []
        for error_dict in errors:
            if 'messages' in error_dict:
                all_messages.extend(error_dict['messages'])
            elif 'error' in error_dict:
                all_messages.append(str(error_dict['error']))

        return {
            'error': 'Multiple validation errors',
            'messages': all_messages
        }


class DetailedValidationErrorFormatter(ValidationErrorFormatter):
    """Detailed validation error formatter with comprehensive error information."""

    def format_validation_error(
        self, error: ValidationError, field_name: str | None = None
    ) -> dict[str, Any]:
        """Format a single validation error with detailed information."""
        errors = []
        for err in error.errors():
            error_detail = {
                'field': (
                    '.'.join(str(x) for x in err['loc'])
                    if err.get('loc') else field_name
                ),
                'message': err['msg'],
                'type': err['type'],
                'input': err.get('input'),
                'context': err.get('ctx', {}),
                'url': err.get('url'),
                'help': self._get_help_text(err)
            }
            errors.append(error_detail)

        return {
            'status': 'error',
            'error_type': 'validation_error',
            'message': 'Request validation failed',
            'validation_errors': errors,
            'error_count': len(errors),
            'timestamp': datetime.now(tz=timezone.utc).isoformat()
        }

    def format_validation_errors(self, errors: list[dict[str, Any]]) -> dict[str, Any]:
        """Format multiple validation errors with detailed information."""
        all_errors = []
        total_count = 0

        for error_dict in errors:
            if 'validation_errors' in error_dict:
                all_errors.extend(error_dict['validation_errors'])
                total_count += len(error_dict['validation_errors'])
            else:
                all_errors.append(error_dict)
                total_count += 1

        return {
            'status': 'error',
            'error_type': 'validation_error',
            'message': 'Multiple validation errors occurred',
            'validation_errors': all_errors,
            'error_count': total_count,
            'timestamp': datetime.now(tz=timezone.utc).isoformat(),
            'help': (
                'Multiple fields have validation errors. '
                'Please review all highlighted issues.'
            )
        }

    def _get_help_text(self, error: dict[str, Any]) -> str | None:
        """Generate helpful text for specific error types."""
        error_type = error.get('type', '')
        ctx = error.get('ctx', {})

        if 'min_length' in error_type:
            return f"minimum length: {ctx.get('limit_value', 'N/A')}"
        elif 'max_length' in error_type:
            return f"maximum length: {ctx.get('limit_value', 'N/A')}"
        elif 'greater_than' in error_type:
            return f"must be greater than: {ctx.get('gt', 'N/A')}"
        elif 'less_than' in error_type:
            return f"must be less than: {ctx.get('lt', 'N/A')}"
        elif 'string_pattern_mismatch' in error_type:
            return f"pattern: {ctx.get('pattern', 'N/A')}"
        elif 'missing' in error_type:
            return "this field is required"
        elif 'value_error' in error_type:
            return "invalid value provided"
        else:
            return None


class JSONSchemaValidationErrorFormatter(ValidationErrorFormatter):
    """JSON Schema compatible validation error formatter."""

    def format_validation_error(
        self, error: ValidationError, field_name: str | None = None
    ) -> dict[str, Any]:
        """Format validation error in JSON Schema style."""
        errors = []
        for err in error.errors():
            json_pointer = (
                '/' + '/'.join(str(x) for x in err['loc'])
                if err.get('loc') else f'/{field_name}'
            )
            field_key = (
                err.get('loc', [field_name])[0] if err.get('loc') else field_name
            )
            errors.append({
                'instancePath': json_pointer,
                'schemaPath': f"#/properties/{field_key}",
                'keyword': err['type'],
                'params': err.get('ctx', {}),
                'message': err['msg'],
                'data': err.get('input')
            })

        return {
            'valid': False,
            'errors': errors
        }

    def format_validation_errors(self, errors: list[dict[str, Any]]) -> dict[str, Any]:
        """Format multiple validation errors in JSON Schema style."""
        all_errors = []
        for error_dict in errors:
            if 'errors' in error_dict:
                all_errors.extend(error_dict['errors'])

        return {
            'valid': False,
            'errors': all_errors
        }
