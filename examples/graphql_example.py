#!/usr/bin/env python3
"""
GraphQL Example for Velithon Framework

This example demonstrates how to use the high-performance GraphQL feature 
in the Velithon framework with Rust-powered backend.
"""

from velithon import GraphQLSchema, GraphQLQueryBuilder

def main():
    """Demonstrate GraphQL functionality."""
    print("🚀 Velithon GraphQL Example")
    print("=" * 50)
    
    # Create a new GraphQL schema
    schema = GraphQLSchema()
    print("✅ GraphQL Schema created successfully")
    
    # Example 1: Simple hello query
    print("\n📝 Example 1: Simple Hello Query")
    query1 = "query { hello }"
    result1 = schema.execute(query1)
    print(f"Query: {query1}")
    print(f"Result: {result1.data}")
    
    # Example 2: Hello query with parameters
    print("\n📝 Example 2: Hello Query with Parameters")
    query2 = 'query { hello(name: "Rust+Python") }'
    result2 = schema.execute(query2)
    print(f"Query: {query2}")
    print(f"Result: {result2.data}")
    
    # Example 3: Server time query
    print("\n📝 Example 3: Server Time Query")
    query3 = "query { serverTime }"
    result3 = schema.execute(query3)
    print(f"Query: {query3}")
    print(f"Result: {result3.data}")
    
    # Example 4: Multi-field query
    print("\n📝 Example 4: Multi-field Query")
    query4 = '''
    query {
        hello(name: "Developer")
        serverTime
    }
    '''
    result4 = schema.execute(query4)
    print(f"Query: {query4.strip()}")
    print(f"Result: {result4.data}")
    
    # Example 5: Query Builder
    print("\n📝 Example 5: Query Builder")
    builder = GraphQLQueryBuilder()
    builder.field("hello", {"name": "Builder"}, None)
    builder.field("serverTime", None, None)
    
    built_query = builder.build()
    result5 = schema.execute(built_query)
    print(f"Built Query: {built_query}")
    print(f"Result: {result5.data}")
    
    # Example 6: Batch execution
    print("\n📝 Example 6: Batch Query Execution")
    batch_queries = [
        {"query": "query { hello }"},
        {"query": 'query { hello(name: "Batch1") }'},
        {"query": 'query { hello(name: "Batch2") }'},
        {"query": "query { serverTime }"}
    ]
    
    batch_results = schema.execute_batch(batch_queries)
    print(f"Batch queries count: {len(batch_queries)}")
    for i, result in enumerate(batch_results):
        print(f"  Result {i+1}: {result.data}")
    
    # Example 7: Query validation
    print("\n📝 Example 7: Query Validation")
    valid_query = "query { hello }"
    invalid_query = "query { invalid_field"  # Missing closing brace
    
    print(f"Valid query '{valid_query}': {schema.validate(valid_query)}")
    print(f"Invalid query '{invalid_query}': {schema.validate(invalid_query)}")
    
    # Example 8: Schema introspection
    print("\n📝 Example 8: Schema SDL (Definition)")
    sdl = schema.get_schema_sdl()
    print(f"Schema SDL (first 200 chars): {sdl[:200]}...")
    
    print("\n" + "=" * 50)
    print("🎉 All GraphQL examples completed successfully!")
    print("   - High-performance Rust backend ✅")
    print("   - Python integration ✅") 
    print("   - Query execution ✅")
    print("   - Query building ✅")
    print("   - Batch operations ✅")
    print("   - Validation ✅")

if __name__ == "__main__":
    main()