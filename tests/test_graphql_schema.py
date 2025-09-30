"""Test cases for GraphQL schema definition and type system."""

import pytest

from velithon.graphql import (
    Field,
    GraphQLSchema,
    Mutation,
    ObjectType,
    Query,
    Subscription,
    graphql_field,
    graphql_type,
)
from velithon.graphql.schema import _type_registry


class TestGraphQLTypeRegistry:
    """Test GraphQL type registry functionality."""

    def test_type_registry_registration(self):
        """Test type registration in the registry."""
        from velithon.graphql.schema import GraphQLTypeRegistry

        registry = GraphQLTypeRegistry()
        
        # Test type registration
        from graphql import GraphQLString
        test_type = GraphQLString
        registry.register_type("TestType", test_type)
        assert "TestType" in registry.types
        assert registry.types["TestType"] == test_type

    def test_resolver_registry_registration(self):
        """Test resolver registration in the registry."""
        from velithon.graphql.schema import GraphQLTypeRegistry

        registry = GraphQLTypeRegistry()
        
        def test_resolver():
            return "test"
        
        # Test resolver registration
        registry.register_resolver("Query", "testField", test_resolver)
        assert "Query" in registry.resolvers
        assert "testField" in registry.resolvers["Query"]
        assert registry.resolvers["Query"]["testField"] == test_resolver

    def test_field_registry_registration(self):
        """Test field registration in the registry."""
        from velithon.graphql.schema import GraphQLTypeRegistry

        registry = GraphQLTypeRegistry()
        
        test_field = Field(type_=str, description="Test field")
        
        # Test field registration
        registry.register_field("Query", "testField", test_field)
        assert "Query" in registry.fields
        assert "testField" in registry.fields["Query"]
        assert registry.fields["Query"]["testField"] == test_field


class TestField:
    """Test GraphQL field functionality."""

    def test_field_creation(self):
        """Test field creation with various parameters."""
        field = Field(
            type_=str,
            description="Test field",
            resolver=lambda: "test",
            deprecation_reason="Deprecated for testing",
            args={"input": {"type": str, "description": "Test input"}},
        )
        
        assert field.type_ is str
        assert field.description == "Test field"
        assert field.resolver() == "test"
        assert field.deprecation_reason == "Deprecated for testing"
        assert "input" in field.args

    def test_field_to_graphql_field(self):
        """Test conversion of Field to GraphQL field."""
        def test_resolver():
            return "test_result"

        field = Field(
            type_=str,
            description="Test field",
            resolver=test_resolver,
        )
        
        graphql_field = field.to_graphql_field()
        assert graphql_field is not None
        assert graphql_field.description == "Test field"

    def test_field_with_arguments(self):
        """Test field with arguments."""
        field = Field(
            type_=str,
            description="Test field with args",
            args={
                "name": {"type": str, "description": "Name argument"},
                "age": {"type": int, "description": "Age argument"},
            },
        )
        
        graphql_field = field.to_graphql_field()
        assert graphql_field is not None
        assert len(graphql_field.args) == 2
        assert "name" in graphql_field.args
        assert "age" in graphql_field.args


class TestGraphQLDecorators:
    """Test GraphQL decorators."""

    def test_graphql_type_decorator(self):
        """Test @graphql_type decorator."""
        @graphql_type
        class User(ObjectType):
            """A user in the system."""
            pass
        
        # Verify the class has been decorated and registered
        assert User.__name__ in _type_registry.types
        assert hasattr(User, 'to_graphql_type')
        graphql_type_obj = User.to_graphql_type()
        assert graphql_type_obj.name == "User"

    def test_graphql_field_decorator(self):
        """Test @graphql_field decorator."""
        class TestType:
            @graphql_field(str, description="Test field")
            def test_field(self) -> str:
                """Test field method."""
                return "test"
        
        # Verify the method has been decorated
        assert hasattr(TestType.test_field, '_graphql_field')
        field_info = TestType.test_field._graphql_field
        assert field_info.description == "Test field"

    def test_graphql_field_with_args(self):
        """Test @graphql_field decorator with arguments."""
        class TestType:
            @graphql_field(
                str,
                description="Test field with arguments",
                args={"name": {"type": str, "description": "Name parameter"}}
            )
            def test_field_with_args(self, name: str) -> str:
                """Test field with arguments."""
                return f"Hello, {name}!"
        
        field_info = TestType.test_field_with_args._graphql_field
        assert field_info.description == "Test field with arguments"
        assert "name" in field_info.args


class TestObjectType:
    """Test ObjectType functionality."""

    def test_object_type_creation(self):
        """Test ObjectType creation."""
        class User(ObjectType):
            """User type."""
            name: str = Field(type_=str, description="User name")
            age: int = Field(type_=int, description="User age")
        
        assert User.__name__ == "User"
        assert hasattr(User, '_graphql_fields')
        assert 'name' in User._graphql_fields
        assert 'age' in User._graphql_fields

    def test_object_type_with_methods(self):
        """Test ObjectType with method fields."""
        class User(ObjectType):
            """User type with methods."""
            
            def __init__(self, name: str, age: int):
                self.name = name
                self.age = age
            
            @graphql_field(str, description="Get user's full name")
            def full_name(self) -> str:
                return f"Mr/Ms {self.name}"
            
            @graphql_field(str, description="Check if user is adult")
            def is_adult(self) -> bool:
                return self.age >= 18
        
        user = User("John", 25)
        assert user.full_name() == "Mr/Ms John"
        assert user.is_adult() is True


class TestQuery:
    """Test Query type functionality."""

    def test_query_creation(self):
        """Test Query type creation."""
        class TestQuery(Query):
            """Test query type."""
            
            @graphql_field(str, description="Get hello message")
            def hello(self) -> str:
                return "Hello, World!"
            
            @graphql_field(str, description="Get user by ID")
            def user(self, user_id: int) -> str:
                return f"User {user_id}"
        
        query = TestQuery()
        assert query.hello() == "Hello, World!"
        assert query.user(123) == "User 123"


class TestMutation:
    """Test Mutation type functionality."""

    def test_mutation_creation(self):
        """Test Mutation type creation."""
        class TestMutation(Mutation):
            """Test mutation type."""
            
            @graphql_field(str, description="Create a user")
            def create_user(self, name: str) -> str:
                return f"Created user: {name}"
            
            @graphql_field(str, description="Delete a user")
            def delete_user(self, user_id: int) -> bool:
                return True
        
        mutation = TestMutation()
        assert mutation.create_user("John") == "Created user: John"
        assert mutation.delete_user(123) is True


class TestSubscription:
    """Test Subscription type functionality."""

    def test_subscription_creation(self):
        """Test Subscription type creation."""
        class TestSubscription(Subscription):
            """Test subscription type."""
            
            @graphql_field(str, description="Subscribe to user updates")
            async def user_updated(self, user_id: int):
                # Simulate async generator
                for i in range(3):
                    yield f"Update {i} for user {user_id}"
        
        subscription = TestSubscription()
        # Verify the method exists
        assert hasattr(subscription, 'user_updated')


class TestGraphQLSchema:
    """Test GraphQLSchema functionality."""

    def test_schema_creation(self):
        """Test GraphQL schema creation."""
        class TestQuery(Query):
            @graphql_field(str, description="Get hello message")
            def hello(self) -> str:
                return "Hello, World!"
        
        schema = GraphQLSchema(query=TestQuery)
        assert schema.query == TestQuery
        assert schema.mutation is None
        assert schema.subscription is None

    def test_schema_with_all_types(self):
        """Test GraphQL schema with query, mutation, and subscription."""
        class TestQuery(Query):
            @graphql_field(str, description="Get hello message")
            def hello(self) -> str:
                return "Hello, World!"
        
        class TestMutation(Mutation):
            @graphql_field(str, description="Create something")
            def create(self, name: str) -> str:
                return f"Created: {name}"
        
        class TestSubscription(Subscription):
            @graphql_field(str, description="Subscribe to updates")
            async def updates(self):
                yield "Update 1"
        
        schema = GraphQLSchema(
            query=TestQuery,
            mutation=TestMutation,
            subscription=TestSubscription,
        )
        
        assert schema.query == TestQuery
        assert schema.mutation == TestMutation
        assert schema.subscription == TestSubscription

    def test_schema_build(self):
        """Test building GraphQL schema."""
        class TestQuery(Query):
            @graphql_field(str, description="Get hello message")
            def hello(self) -> str:
                return "Hello, World!"
        
        schema = GraphQLSchema(query=TestQuery)
        built_schema = schema.build()
        
        # Verify it's a proper GraphQL schema
        assert built_schema is not None
        assert hasattr(built_schema, 'query_type')

    def test_schema_validation(self):
        """Test GraphQL schema validation."""
        class TestQuery(Query):
            @graphql_field(str, description="Get hello message")
            def hello(self) -> str:
                return "Hello, World!"
        
        schema = GraphQLSchema(query=TestQuery)
        built_schema = schema.build()
        
        # Should not raise any validation errors
        from graphql import validate_schema
        errors = validate_schema(built_schema)
        assert len(errors) == 0

    def test_schema_string_generation(self):
        """Test generating schema string."""
        class TestQuery(Query):
            @graphql_field(str, description="Get hello message")
            def hello(self) -> str:
                return "Hello, World!"

        schema = GraphQLSchema(query=TestQuery)
        schema_str = schema.get_schema_sdl()

        assert isinstance(schema_str, str)
        assert "type TestQuery" in schema_str
        assert "hello: String" in schema_str
class TestTypeConversion:
    """Test type conversion functionality."""

    def test_python_to_graphql_type_conversion(self):
        """Test conversion of Python types to GraphQL types."""
        from velithon.graphql.schema import Field

        # Test basic types
        str_field = Field(type_=str)
        graphql_field = str_field.to_graphql_field()
        assert graphql_field is not None

        int_field = Field(type_=int)
        graphql_field = int_field.to_graphql_field()
        assert graphql_field is not None

        float_field = Field(type_=float)
        graphql_field = float_field.to_graphql_field()
        assert graphql_field is not None

        bool_field = Field(type_=bool)
        graphql_field = bool_field.to_graphql_field()
        assert graphql_field is not None

    def test_list_type_conversion(self):
        """Test conversion of list types."""
        list_field = Field(type_=list[str])
        graphql_field = list_field.to_graphql_field()
        assert graphql_field is not None

    def test_optional_type_conversion(self):
        """Test conversion of optional types."""
        optional_field = Field(type_=str | None)
        graphql_field = optional_field.to_graphql_field()
        assert graphql_field is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
