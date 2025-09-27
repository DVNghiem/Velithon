"""GraphQL schema definition and type system for Velithon.

This module provides classes and decorators for defining GraphQL schemas,
types, fields, and resolvers following Velithon's performance-first approach.
"""

from __future__ import annotations

from typing import Any, Callable, ClassVar, Union, get_args, get_origin

from graphql import (
    GraphQLArgument,
    GraphQLBoolean,
    GraphQLField,
    GraphQLFloat,
    GraphQLInt,
    GraphQLList,
    GraphQLObjectType,
    GraphQLString,
    GraphQLType,
    print_schema,
    validate_schema,
)
from graphql import (
    GraphQLSchema as CoreGraphQLSchema,
)


class GraphQLTypeRegistry:
    """Registry for GraphQL types and resolvers."""

    def __init__(self):
        """Initialize the type registry."""
        self.types: dict[str, GraphQLType] = {}
        self.resolvers: dict[str, dict[str, Callable]] = {}
        self.fields: dict[str, dict[str, Field]] = {}

    def register_type(self, name: str, graphql_type: GraphQLType) -> None:
        """Register a GraphQL type."""
        self.types[name] = graphql_type

    def register_resolver(
        self, type_name: str, field_name: str, resolver: Callable
    ) -> None:
        """Register a field resolver."""
        if type_name not in self.resolvers:
            self.resolvers[type_name] = {}
        self.resolvers[type_name][field_name] = resolver

    def register_field(self, type_name: str, field_name: str, field: Field) -> None:
        """Register a field definition."""
        if type_name not in self.fields:
            self.fields[type_name] = {}
        self.fields[type_name][field_name] = field


# Global type registry
_type_registry = GraphQLTypeRegistry()


class Field:
    """Represents a GraphQL field definition."""

    def __init__(
        self,
        type_: str | type | GraphQLType,
        description: str | None = None,
        resolver: Callable | None = None,
        deprecation_reason: str | None = None,
        args: dict[str, Any] | None = None,
    ):
        """Initialize GraphQL field.

        Args:
            type_: The field type
            description: Field description
            resolver: Field resolver function
            deprecation_reason: Deprecation reason if field is deprecated
            args: Field arguments

        """
        self.type_ = type_
        self.description = description
        self.resolver = resolver
        self.deprecation_reason = deprecation_reason
        self.args = args or {}

    def to_graphql_field(self) -> GraphQLField:
        """Convert to GraphQL field."""
        # Convert args to GraphQL arguments
        graphql_args = {}
        if self.args:
            for arg_name, arg_info in self.args.items():
                if isinstance(arg_info, dict):
                    arg_type = arg_info.get('type', str)
                    arg_description = arg_info.get('description', None)
                    graphql_args[arg_name] = GraphQLArgument(
                        type_=self._convert_type(arg_type), description=arg_description
                    )
                else:
                    # Assume it's just a type
                    graphql_args[arg_name] = GraphQLArgument(
                        type_=self._convert_type(arg_info)
                    )

        return GraphQLField(
            type_=self._convert_type(self.type_),
            description=self.description,
            resolve=self.resolver,
            deprecation_reason=self.deprecation_reason,
            args=graphql_args,
        )

    def _convert_type(self, type_: Any) -> GraphQLType:
        """Convert Python type to GraphQL type."""
        if isinstance(type_, GraphQLType):
            return type_

        # Handle basic types
        if type_ is str:
            return GraphQLString
        elif type_ is int:
            return GraphQLInt
        elif type_ is float:
            return GraphQLFloat
        elif type_ is bool:
            return GraphQLBoolean

        # Handle Optional types
        origin = get_origin(type_)
        if origin is Union:
            args = get_args(type_)
            if len(args) == 2 and type(None) in args:
                # This is Optional[T]
                non_none_type = next(arg for arg in args if arg is not type(None))
                return self._convert_type(non_none_type)

        # Handle List types
        if origin is list:
            args = get_args(type_)
            if args:
                item_type = args[0]
                # Check if it's a registered ObjectType
                if (
                    hasattr(item_type, '__name__')
                    and item_type.__name__ in _type_registry.types
                ):
                    return GraphQLList(_type_registry.types[item_type.__name__])
                return GraphQLList(self._convert_type(item_type))
            return GraphQLList(GraphQLString)

        # Handle direct list type
        if type_ is list:
            return GraphQLList(GraphQLString)

        # Handle registered types (both class and string references)
        if isinstance(type_, str) and type_ in _type_registry.types:
            return _type_registry.types[type_]
        elif hasattr(type_, '__name__') and type_.__name__ in _type_registry.types:
            return _type_registry.types[type_.__name__]

        # Default to String for unknown types
        return GraphQLString


def graphql_field(
    type_: str | type | GraphQLType,
    description: str | None = None,
    deprecation_reason: str | None = None,
    args: dict[str, Any] | None = None,
) -> Callable:
    """Define a GraphQL field."""

    def decorator(func: Callable) -> Callable:
        field = Field(
            type_=type_,
            description=description,
            resolver=func,
            deprecation_reason=deprecation_reason,
            args=args,
        )

        # Store field information on the function
        func._graphql_field = field
        return func

    return decorator


class ObjectTypeMeta(type):
    """Metaclass for GraphQL object types."""

    def __new__(cls, name: str, bases: tuple, attrs: dict):
        """Create new object type class."""
        # Extract GraphQL fields from class attributes and methods
        fields = {}

        for attr_name, attr_value in attrs.items():
            if hasattr(attr_value, '_graphql_field'):
                fields[attr_name] = attr_value._graphql_field
            elif isinstance(attr_value, Field):
                fields[attr_name] = attr_value

        # Store fields on the class
        attrs['_graphql_fields'] = fields

        # Create the class
        new_class = super().__new__(cls, name, bases, attrs)

        # Register the type
        if name != 'ObjectType':  # Skip base class
            _type_registry.register_field(name, name, fields)

        return new_class


class ObjectType(metaclass=ObjectTypeMeta):
    """Base class for GraphQL object types."""

    _graphql_fields: ClassVar[dict[str, Field]] = {}

    @classmethod
    def to_graphql_type(cls) -> GraphQLObjectType:
        """Convert to GraphQL object type."""
        fields = {}

        for field_name, field in cls._graphql_fields.items():
            fields[field_name] = field.to_graphql_field()

        return GraphQLObjectType(
            name=cls.__name__,
            fields=fields,
            description=cls.__doc__,
        )


class Query(ObjectType):
    """Base class for GraphQL Query type."""

    pass


class Mutation(ObjectType):
    """Base class for GraphQL Mutation type."""

    pass


class Subscription(ObjectType):
    """Base class for GraphQL Subscription type."""

    pass


def graphql_type(cls: type) -> type:
    """Register a class as a GraphQL type."""
    graphql_object_type = cls.to_graphql_type()
    _type_registry.register_type(cls.__name__, graphql_object_type)
    return cls


class GraphQLSchema:
    """GraphQL schema builder for Velithon."""

    def __init__(
        self,
        query: type[Query] | None = None,
        mutation: type[Mutation] | None = None,
        subscription: type[Subscription] | None = None,
    ):
        """Initialize GraphQL schema.

        Args:
            query: Query root type
            mutation: Mutation root type
            subscription: Subscription root type

        """
        self.query = query
        self.mutation = mutation
        self.subscription = subscription
        self._schema: CoreGraphQLSchema | None = None

    def build(self) -> CoreGraphQLSchema:
        """Build the GraphQL schema."""
        if self._schema is None:
            schema_kwargs = {}

            if self.query:
                schema_kwargs['query'] = self.query.to_graphql_type()

            if self.mutation:
                schema_kwargs['mutation'] = self.mutation.to_graphql_type()

            if self.subscription:
                schema_kwargs['subscription'] = self.subscription.to_graphql_type()

            self._schema = CoreGraphQLSchema(**schema_kwargs)

            # Validate the schema
            errors = validate_schema(self._schema)
            if errors:
                raise ValueError(f'Schema validation failed: {errors}')

        return self._schema

    def to_graphql_schema(self) -> CoreGraphQLSchema:
        """Build the GraphQL schema (alias for build method)."""
        return self.build()

    def get_schema_sdl(self) -> str:
        """Get the schema definition language (SDL) representation."""
        return print_schema(self.build())
