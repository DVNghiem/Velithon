# CRUD API Example

A complete Create, Read, Update, Delete API example using Velithon.

## Overview

This example demonstrates building a RESTful API for managing a collection of items with full CRUD operations.

## Complete CRUD Application

```python
from velithon import Velithon
from velithon.responses import JSONResponse
from velithon.exceptions import HTTPException
from pydantic import BaseModel
from typing import List, Optional
import datetime

app = Velithon()

# Data Models
class ItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    category: str

class ItemCreate(ItemBase):
    pass

class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None

class Item(ItemBase):
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

# In-memory storage (use a database in production)
items_db = {}
next_item_id = 1

# Helper functions
def get_item_by_id(item_id: int) -> Optional[Item]:
    return items_db.get(item_id)

def create_item_in_db(item_data: ItemCreate) -> Item:
    global next_item_id
    now = datetime.datetime.now()
    item = Item(
        id=next_item_id,
        created_at=now,
        updated_at=now,
        **item_data.dict()
    )
    items_db[next_item_id] = item
    next_item_id += 1
    return item

# API Endpoints

@app.post("/items", response_model=Item, tags=["items"])
async def create_item(item: ItemCreate):
    """Create a new item"""
    created_item = create_item_in_db(item)
    return JSONResponse(created_item.dict(), status_code=201)

@app.get("/items", response_model=List[Item], tags=["items"])
async def list_items(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None
):
    """Get all items with optional filtering"""
    items = list(items_db.values())
    
    # Filter by category if provided
    if category:
        items = [item for item in items if item.category == category]
    
    # Apply pagination
    items = items[skip : skip + limit]
    
    return JSONResponse([item.dict() for item in items])

@app.get("/items/{item_id}", response_model=Item, tags=["items"])
async def get_item(item_id: int):
    """Get a specific item by ID"""
    item = get_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return JSONResponse(item.dict())

@app.put("/items/{item_id}", response_model=Item, tags=["items"])
async def update_item(item_id: int, item_update: ItemUpdate):
    """Update an existing item"""
    item = get_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Update only provided fields
    update_data = item_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    item.updated_at = datetime.datetime.now()
    items_db[item_id] = item
    
    return JSONResponse(item.dict())

@app.delete("/items/{item_id}", tags=["items"])
async def delete_item(item_id: int):
    """Delete an item"""
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    
    del items_db[item_id]
    return JSONResponse({"message": "Item deleted successfully"})

# Additional endpoints
@app.get("/items/category/{category}", response_model=List[Item], tags=["items"])
async def get_items_by_category(category: str):
    """Get all items in a specific category"""
    items = [item for item in items_db.values() if item.category == category]
    return JSONResponse([item.dict() for item in items])

@app.get("/stats", tags=["stats"])
async def get_stats():
    """Get API statistics"""
    categories = {}
    total_value = 0
    
    for item in items_db.values():
        categories[item.category] = categories.get(item.category, 0) + 1
        total_value += item.price
    
    return JSONResponse({
        "total_items": len(items_db),
        "categories": categories,
        "total_value": total_value,
        "average_price": total_value / len(items_db) if items_db else 0
    })

# Seed some data
if __name__ == "__main__":
    # Add some sample items
    sample_items = [
        ItemCreate(name="Laptop", description="Gaming laptop", price=1299.99, category="Electronics"),
        ItemCreate(name="Coffee Mug", description="Ceramic mug", price=12.99, category="Kitchenware"),
        ItemCreate(name="Book", description="Python programming guide", price=39.99, category="Books"),
    ]
    
    for item_data in sample_items:
        create_item_in_db(item_data)
    
    print("Sample data created!")
    app.run(debug=True)
```

## Usage Examples

### Create an Item

```bash
curl -X POST "http://localhost:8000/items" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Smartphone",
    "description": "Latest smartphone",
    "price": 699.99,
    "category": "Electronics"
  }'
```

### Get All Items

```bash
curl "http://localhost:8000/items"
```

### Get Items with Pagination

```bash
curl "http://localhost:8000/items?skip=0&limit=10"
```

### Get a Specific Item

```bash
curl "http://localhost:8000/items/1"
```

### Update an Item

```bash
curl -X PUT "http://localhost:8000/items/1" \
  -H "Content-Type: application/json" \
  -d '{
    "price": 1199.99,
    "description": "Updated gaming laptop"
  }'
```

### Delete an Item

```bash
curl -X DELETE "http://localhost:8000/items/1"
```

### Get Items by Category

```bash
curl "http://localhost:8000/items/category/Electronics"
```

### Get Statistics

```bash
curl "http://localhost:8000/stats"
```

## Key Features Demonstrated

- **Pydantic Models**: Input validation and serialization
- **Error Handling**: Proper HTTP status codes and error messages
- **Path Parameters**: Dynamic URL segments
- **Query Parameters**: Filtering and pagination
- **HTTP Methods**: GET, POST, PUT, DELETE
- **Response Models**: Type-safe response definitions
- **Tags**: API organization for documentation

## Next Steps

- Add database integration (PostgreSQL, MongoDB, etc.)
- Implement authentication and authorization
- Add input validation and sanitization
- Include logging and monitoring
- Add unit and integration tests
