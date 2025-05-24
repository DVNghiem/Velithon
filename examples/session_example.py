"""
Session Middleware Example

This example demonstrates how to use session middleware in Velithon for:
- User authentication and login/logout
- Shopping cart functionality
- Session data persistence
- Both memory and cookie-based session backends
"""

from velithon import Velithon
from velithon.middleware import Middleware
from velithon.middleware.session import SessionMiddleware, SignedCookieSessionInterface
from velithon.requests import Request
from velithon.responses import JSONResponse, HTMLResponse

# Create app with memory-based sessions (default)
app = Velithon(
    middleware=[
        Middleware(
            SessionMiddleware,
            secret_key="super-secret-session-key-change-in-production"
        )
    ]
)

# Alternative: Cookie-based sessions
# app = Velithon(
#     middleware=[
#         Middleware(
#             SessionMiddleware,
#             secret_key="super-secret-session-key-change-in-production",
#             session_interface="cookie",  # Use signed cookies instead of memory
#             max_age=3600,  # 1 hour session expiry
#             cookie_name="velithon_session",
#             cookie_secure=False,  # Set to True in production with HTTPS
#             cookie_httponly=True,  # Prevent JavaScript access
#             cookie_samesite="lax"
#         )
#     ]
# )

# Mock user database
USERS = {
    "alice": {"password": "secret123", "email": "alice@example.com", "role": "admin"},
    "bob": {"password": "password456", "email": "bob@example.com", "role": "user"},
}

# Mock product database
PRODUCTS = {
    1: {"name": "Laptop", "price": 999.99},
    2: {"name": "Mouse", "price": 29.99},
    3: {"name": "Keyboard", "price": 79.99},
    4: {"name": "Monitor", "price": 299.99},
}


@app.get("/")
async def home(request: Request):
    """Home page showing session status."""
    user = request.session.get("user")
    cart = request.session.get("cart", {})
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Session Example</title></head>
    <body>
        <h1>Velithon Session Example</h1>
        
        <h2>Authentication</h2>
        {"<p>Logged in as: " + user["username"] + " (" + user["role"] + ")</p>" if user else "<p>Not logged in</p>"}
        
        <h2>Shopping Cart</h2>
        <p>Items in cart: {len(cart)}</p>
        
        <h2>Actions</h2>
        <ul>
            <li><a href="/login">Login</a></li>
            <li><a href="/logout">Logout</a></li>
            <li><a href="/profile">Profile</a></li>
            <li><a href="/cart">View Cart</a></li>
            <li><a href="/products">Products</a></li>
            <li><a href="/session">View Session Data</a></li>
        </ul>
    </body>
    </html>
    """
    
    return HTMLResponse(html)


@app.post("/login")
async def login(request: Request):
    """Login endpoint."""
    form = await request.form()
    username = form.get("username", "")
    password = form.get("password", "")
    
    # Validate credentials
    user = USERS.get(username)
    if not user or user["password"] != password:
        return JSONResponse(
            {"error": "Invalid username or password"}, 
            status_code=401
        )
    
    # Store user data in session
    request.session["user"] = {
        "username": username,
        "email": user["email"],
        "role": user["role"]
    }
    request.session["login_time"] = "2025-05-24T10:30:00Z"  # In real app, use datetime.now()
    
    return JSONResponse({
        "message": "Login successful",
        "user": request.session["user"]
    })


@app.get("/login")
async def login_form(request: Request):
    """Login form."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Login</title></head>
    <body>
        <h1>Login</h1>
        <form method="post" action="/login">
            <p>
                <label>Username:</label><br>
                <input type="text" name="username" placeholder="alice or bob" required>
            </p>
            <p>
                <label>Password:</label><br>
                <input type="password" name="password" placeholder="secret123 or password456" required>
            </p>
            <p>
                <button type="submit">Login</button>
            </p>
        </form>
        <p><a href="/">Back to Home</a></p>
    </body>
    </html>
    """
    return HTMLResponse(html)


@app.post("/logout")
async def logout(request: Request):
    """Logout endpoint."""
    if "user" not in request.session:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    
    username = request.session["user"]["username"]
    
    # Clear all session data
    request.session.clear()
    
    return JSONResponse({
        "message": f"Logged out successfully",
        "user": username
    })


@app.get("/profile")
async def profile(request: Request):
    """User profile (requires login)."""
    user = request.session.get("user")
    if not user:
        return JSONResponse({"error": "Please login first"}, status_code=401)
    
    return JSONResponse({
        "user": user,
        "login_time": request.session.get("login_time"),
        "session_id": getattr(request.session, "session_id", "unknown")
    })


@app.get("/products")
async def products(request: Request):
    """Product listing."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Products</title></head>
    <body>
        <h1>Products</h1>
        <div id="products">
    """
    
    for product_id, product in PRODUCTS.items():
        html += f"""
            <div style="border: 1px solid #ccc; margin: 10px; padding: 10px;">
                <h3>{product['name']}</h3>
                <p>Price: ${product['price']}</p>
                <button onclick="addToCart({product_id})">Add to Cart</button>
            </div>
        """
    
    html += """
        </div>
        
        <script>
        async function addToCart(productId) {
            const response = await fetch('/cart/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({product_id: productId})
            });
            const result = await response.json();
            alert(result.message || result.error);
        }
        </script>
        
        <p><a href="/">Back to Home</a> | <a href="/cart">View Cart</a></p>
    </body>
    </html>
    """
    
    return HTMLResponse(html)


@app.post("/cart/add")
async def add_to_cart(request: Request):
    """Add item to cart."""
    data = await request.json()
    product_id = data.get("product_id")
    
    if not product_id or product_id not in PRODUCTS:
        return JSONResponse({"error": "Invalid product"}, status_code=400)
    
    # Get or create cart
    cart = request.session.get("cart", {})
    product_key = str(product_id)
    
    # Add item to cart
    if product_key in cart:
        cart[product_key]["quantity"] += 1
    else:
        cart[product_key] = {
            "name": PRODUCTS[product_id]["name"],
            "price": PRODUCTS[product_id]["price"],
            "quantity": 1
        }
    
    # Save cart back to session
    request.session["cart"] = cart
    
    return JSONResponse({
        "message": f"Added {PRODUCTS[product_id]['name']} to cart",
        "cart_items": len(cart)
    })


@app.get("/cart")
async def view_cart(request: Request):
    """View shopping cart."""
    cart = request.session.get("cart", {})
    
    if not cart:
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Shopping Cart</title></head>
        <body>
            <h1>Shopping Cart</h1>
            <p>Your cart is empty.</p>
            <p><a href="/products">Browse Products</a> | <a href="/">Home</a></p>
        </body>
        </html>
        """
        return HTMLResponse(html)
    
    total = 0
    cart_html = ""
    
    for product_id, item in cart.items():
        item_total = item["price"] * item["quantity"]
        total += item_total
        
        cart_html += f"""
            <tr>
                <td>{item['name']}</td>
                <td>${item['price']:.2f}</td>
                <td>{item['quantity']}</td>
                <td>${item_total:.2f}</td>
                <td>
                    <button onclick="removeFromCart('{product_id}')">Remove</button>
                </td>
            </tr>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Shopping Cart</title></head>
    <body>
        <h1>Shopping Cart</h1>
        
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr>
                <th>Product</th>
                <th>Price</th>
                <th>Quantity</th>
                <th>Total</th>
                <th>Action</th>
            </tr>
            {cart_html}
            <tr>
                <td colspan="3"><strong>Total:</strong></td>
                <td><strong>${total:.2f}</strong></td>
                <td></td>
            </tr>
        </table>
        
        <p>
            <button onclick="clearCart()">Clear Cart</button>
            <button onclick="checkout()">Checkout</button>
        </p>
        
        <script>
        async function removeFromCart(productId) {{
            const response = await fetch('/cart/remove', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{product_id: productId}})
            }});
            const result = await response.json();
            alert(result.message || result.error);
            location.reload();
        }}
        
        async function clearCart() {{
            const response = await fetch('/cart/clear', {{method: 'POST'}});
            const result = await response.json();
            alert(result.message || result.error);
            location.reload();
        }}
        
        async function checkout() {{
            alert('Checkout functionality would be implemented here!');
        }}
        </script>
        
        <p><a href="/products">Continue Shopping</a> | <a href="/">Home</a></p>
    </body>
    </html>
    """
    
    return HTMLResponse(html)


@app.post("/cart/remove")
async def remove_from_cart(request: Request):
    """Remove item from cart."""
    data = await request.json()
    product_id = str(data.get("product_id"))
    
    cart = request.session.get("cart", {})
    
    if product_id in cart:
        product_name = cart[product_id]["name"]
        del cart[product_id]
        request.session["cart"] = cart
        return JSONResponse({"message": f"Removed {product_name} from cart"})
    
    return JSONResponse({"error": "Item not in cart"}, status_code=400)


@app.post("/cart/clear")
async def clear_cart(request: Request):
    """Clear shopping cart."""
    request.session["cart"] = {}
    return JSONResponse({"message": "Cart cleared"})


@app.get("/session")
async def view_session(request: Request):
    """View all session data (for debugging)."""
    session_data = dict(request.session)
    
    # Don't expose sensitive data in production
    return JSONResponse({
        "session_id": getattr(request.session, "session_id", "unknown"),
        "session_data": session_data,
        "modified": getattr(request.session, "modified", False),
        "new": getattr(request.session, "new", False)
    })


@app.get("/admin")
async def admin_only(request: Request):
    """Admin-only endpoint."""
    user = request.session.get("user")
    
    if not user:
        return JSONResponse({"error": "Please login first"}, status_code=401)
    
    if user.get("role") != "admin":
        return JSONResponse({"error": "Admin access required"}, status_code=403)
    
    return JSONResponse({
        "message": "Welcome to admin area!",
        "user": user,
        "admin_data": "Secret admin information"
    })


if __name__ == "__main__":
    import uvicorn
    print("Starting Velithon Session Example...")
    print("Visit http://localhost:8000 to try the session features")
    print("\nTest accounts:")
    print("- Username: alice, Password: secret123 (admin)")
    print("- Username: bob, Password: password456 (user)")
    
    uvicorn.run(app, host="127.0.0.1", port=8000)
