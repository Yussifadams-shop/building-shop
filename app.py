import os
import json
from datetime import datetime, timedelta
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from supabase import create_client, Client
from dotenv import load_dotenv
from auth import create_session, get_current_user, COOKIE_NAME

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Missing SUPABASE_URL or SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="Building Materials Shop")
SHOP_NAME = "OBOLO TILES & CEMENT"
SHOP_PHONE = "053500108"
SHOP_ADDRESS = "MENZEZOR, GHANA"

USERS = {
    "admin": "CementShop2026!",
}


def page(title, body, user=None):
    user_bar = ""
    if user:
        user_bar = f'<span style="margin-left:15px;font-size:13px;">👤 {user} · <a href="/logout">Logout</a></span>'

    return f"""<!DOCTYPE html>
<html>
<head>
<title>{title} - Building Shop</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
* {{ box-sizing: border-box; }}
body {{ font-family: Arial, sans-serif; margin: 0; background: #f4f4f7; color: #222; }}
.header {{ background: #1e40af; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; }}
.header h1 {{ margin: 0; font-size: 20px; display: inline-block; }}
.header a {{ color: white; text-decoration: none; margin-left: 15px; font-size: 14px; }}
.container {{ max-width: 1000px; margin: 20px auto; padding: 0 15px; }}
.card {{ background: white; border-radius: 8px; padding: 20px; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
h2 {{ color: #1e40af; margin-top: 0; }}
h3 {{ color: #1e40af; margin-top: 15px; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #eee; }}
th {{ background: #f9fafb; }}
input, select {{ width: 100%; padding: 10px; margin: 5px 0 15px; border: 1px solid #ddd; border-radius: 5px; font-size: 15px; }}
button, .btn {{ background: #1e40af; color: white; padding: 10px 16px; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; text-decoration: none; display: inline-block; }}
button:hover, .btn:hover {{ background: #1e3a8a; }}
.btn-success {{ background: #16a34a; }}
.btn-danger {{ background: #dc2626; }}
.btn-warn {{ background: #d97706; }}
.btn-small {{ padding: 6px 12px; font-size: 13px; }}
.low {{ color: #dc2626; font-weight: bold; }}
.ok {{ color: #16a34a; font-weight: bold; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
@media (max-width: 600px) {{ .grid {{ grid-template-columns: 1fr; }} }}
.stat {{ text-align: center; padding: 15px; }}
.stat .num {{ font-size: 28px; font-weight: bold; color: #1e40af; }}
.stat .label {{ color: #666; font-size: 13px; }}
.login-box {{ max-width: 400px; margin: 80px auto; }}
.cart-total {{ background: #fef3c7; padding: 15px; border-radius: 8px; margin-top: 10px; font-size: 18px; }}
</style>
</head>
<body>
<div class="header">
<h1>🏗️ <h1>🏗️ {SHOP_NAME}</h1></h1>
<div>
{"<a href='/' >Home</a><a href='/products'>Materials</a><a href='/add'>Add</a><a href='/sell'>New Sale</a><a href='/cart'>Cart</a><a href='/categories'>Categories</a><a href='/reports'>Reports</a>" if user else ""}
{user_bar}
</div>
</div>
<div class="container">{body}</div>
</body>
</html>"""


# ============ AUTH ============

@app.get("/login", response_class=HTMLResponse)
def login_page(error: str = ""):
    err = f'<p style="color:#dc2626;">{error}</p>' if error else ""
    body = f"""
    <div class="login-box">
        <div class="card">
            <h2>🔐 Login</h2>
            {err}
            <form method="post" action="/login">
                <label>Username</label>
                <input type="text" name="username" required autofocus>
                <label>Password</label>
                <input type="password" name="password" required>
                <button type="submit" style="width:100%;">Login</button>
            </form>
        </div>
    </div>
    """
    return HTMLResponse(content=page("Login", body))


@app.post("/login")
async def do_login(username: str = Form(...), password: str = Form(...)):
    if username in USERS and USERS[username] == password:
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(COOKIE_NAME, create_session(username), httponly=True, max_age=60*60*24*7)
        return response
    return RedirectResponse("/login?error=Wrong+username+or+password", status_code=303)


@app.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response


# ============ CART HELPERS ============

def get_cart(request: Request):
    raw = request.cookies.get("cart", "[]")
    try:
        return json.loads(raw)
    except Exception:
        return []


def save_cart(cart):
    response = RedirectResponse("/cart", status_code=303)
    response.set_cookie("cart", json.dumps(cart), max_age=60*60*6)
    return response


# ============ DASHBOARD ============

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    products = supabase.table("products").select("*").eq("is_active", True).execute().data
    total_products = len(products)
    total_value = sum(float(p.get("quantity_in_stock", 0)) * float(p.get("cost_price", 0)) for p in products)
    low_stock = [p for p in products if float(p.get("quantity_in_stock", 0)) <= float(p.get("reorder_level", 0))]
    low_rows = "".join(f"<tr><td>{p['name']}</td><td class='low'>{p['quantity_in_stock']} {p['unit']}</td></tr>" for p in low_stock)
    body = f"""
    <h2>Dashboard</h2>
    <div class="grid">
        <div class="card stat"><div class="num">{total_products}</div><div class="label">Materials</div></div>
        <div class="card stat"><div class="num">GHS {total_value:,.2f}</div><div class="label">Inventory Value</div></div>
    </div>
    <div class="card">
        <h2>Low Stock ({len(low_stock)})</h2>
        {f"<table><tr><th>Material</th><th>In Stock</th></tr>{low_rows}</table>" if low_stock else "<p>All good!</p>"}
    </div>
    <div class="card">
        <a href="/add" class="btn">Add Material</a>
        <a href="/products" class="btn">View All</a>
        <a href="/sell" class="btn btn-success">New Sale</a>
        <a href="/cart" class="btn">🛒 Cart</a>
        <a href="/reports" class="btn">📊 Reports</a>
    </div>
    """
    return HTMLResponse(content=page("Dashboard", body, user))


# ============ PRODUCTS ============

@app.get("/products", response_class=HTMLResponse)
def products_list(request: Request, search: str = ""):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    query = supabase.table("products").select("*").eq("is_active", True)
    if search:
        query = query.ilike("name", f"%{search}%")
    products = query.order("name").execute().data
    rows = ""
    for p in products:
        qty = float(p.get("quantity_in_stock", 0))
        reorder = float(p.get("reorder_level", 0))
        status = "low" if qty <= reorder else "ok"
        rows += f"""<tr>
            <td><strong>{p['name']}</strong><br><small>{p.get('sku','')}</small></td>
            <td>{p.get('unit','')}</td>
            <td class='{status}'>{qty}</td>
            <td>GHS {float(p['selling_price']):,.2f}</td>
            <td>
                <a href='/edit/{p['id']}' class='btn btn-warn btn-small'>✏️ Edit</a>
                <a href='/delete/{p['id']}' class='btn btn-danger btn-small' onclick="return confirm('Delete {p['name']}?')">🗑️</a>
            </td>
        </tr>"""
    body = f"""
    <h2>All Materials</h2>
    <div class="card">
        <form method="get" style="display:flex;gap:10px;">
            <input type="text" name="search" placeholder="Search..." value="{search}">
            <button>Search</button>
        </form>
    </div>
    <div class="card"><table>
        <tr><th>Material</th><th>Unit</th><th>Stock</th><th>Price</th><th>Actions</th></tr>
        {rows if rows else "<tr><td colspan='5'>No materials. <a href='/add'>Add one</a>.</td></tr>"}
    </table></div>
    """
    return HTMLResponse(content=page("Materials", body, user))


@app.get("/add", response_class=HTMLResponse)
def add_form(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    cats = supabase.table("categories").select("*").order("name").execute().data
    cat_options = "".join(f"<option value='{c['id']}'>{c['name']}</option>" for c in cats)
    body = f"""
    <h2>Add Material</h2>
    <div class="card">
        <form method="post" action="/add">
            <label>Name</label><input type="text" name="name" required>
            <label>SKU</label><input type="text" name="sku" required>
            <label>Category</label><select name="category_id" required><option value="">--</option>{cat_options}</select>
            <label>Unit</label><input type="text" name="unit" required placeholder="bag">
            <label>Location</label><input type="text" name="location">
            <label>Cost Price</label><input type="number" step="0.01" name="cost_price" required>
            <label>Selling Price</label><input type="number" step="0.01" name="selling_price" required>
            <label>Quantity</label><input type="number" step="0.01" name="quantity_in_stock" required>
            <label>Reorder Level</label><input type="number" step="0.01" name="reorder_level" value="10">
            <button type="submit">Save</button>
            <a href="/products" class="btn">Cancel</a>
        </form>
    </div>
    """
    return HTMLResponse(content=page("Add", body, user))


@app.post("/add")
async def add_product(request: Request, name: str = Form(...), sku: str = Form(...), category_id: str = Form(...), unit: str = Form(...), location: str = Form(""), cost_price: float = Form(...), selling_price: float = Form(...), quantity_in_stock: float = Form(...), reorder_level: float = Form(10)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    data = {"name": name, "sku": sku, "category_id": int(category_id), "unit": unit, "location": location or None, "cost_price": cost_price, "selling_price": selling_price, "quantity_in_stock": quantity_in_stock, "reorder_level": reorder_level, "is_active": True}
    result = supabase.table("products").insert(data).execute()
    if result.data and quantity_in_stock > 0:
        supabase.table("stock_movements").insert({"product_id": result.data[0]["id"], "movement_type": "IN", "quantity": quantity_in_stock, "unit_cost": cost_price, "note": "Opening stock"}).execute()
    return RedirectResponse("/products", status_code=303)


@app.get("/edit/{product_id}", response_class=HTMLResponse)
def edit_form(request: Request, product_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    p = supabase.table("products").select("*").eq("id", product_id).single().execute().data
    cats = supabase.table("categories").select("*").order("name").execute().data
    cat_options = "".join(
        f"<option value='{c['id']}' {'selected' if c['id']==p.get('category_id') else ''}>{c['name']}</option>"
        for c in cats
    )
    body = f"""
    <h2>Edit Material</h2>
    <div class="card">
        <form method="post" action="/edit/{product_id}">
            <label>Name</label><input type="text" name="name" value="{p['name']}" required>
            <label>SKU</label><input type="text" name="sku" value="{p.get('sku','')}" required>
            <label>Category</label><select name="category_id" required>{cat_options}</select>
            <label>Unit</label><input type="text" name="unit" value="{p.get('unit','')}" required>
            <label>Location</label><input type="text" name="location" value="{p.get('location','') or ''}">
            <label>Cost Price</label><input type="number" step="0.01" name="cost_price" value="{p['cost_price']}" required>
            <label>Selling Price</label><input type="number" step="0.01" name="selling_price" value="{p['selling_price']}" required>
            <label>Current Stock</label><input type="number" step="0.01" name="quantity_in_stock" value="{p['quantity_in_stock']}" required>
            <label>Reorder Level</label><input type="number" step="0.01" name="reorder_level" value="{p['reorder_level']}">
            <button type="submit">Save Changes</button>
            <a href="/products" class="btn">Cancel</a>
        </form>
    </div>
    """
    return HTMLResponse(content=page("Edit", body, user))


@app.post("/edit/{product_id}")
async def edit_product(request: Request, product_id: int, name: str = Form(...), sku: str = Form(...), category_id: str = Form(...), unit: str = Form(...), location: str = Form(""), cost_price: float = Form(...), selling_price: float = Form(...), quantity_in_stock: float = Form(...), reorder_level: float = Form(10)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    old = supabase.table("products").select("*").eq("id", product_id).single().execute().data
    old_qty = float(old.get("quantity_in_stock", 0))

    data = {"name": name, "sku": sku, "category_id": int(category_id), "unit": unit, "location": location or None, "cost_price": cost_price, "selling_price": selling_price, "quantity_in_stock": quantity_in_stock, "reorder_level": reorder_level}
    supabase.table("products").update(data).eq("id", product_id).execute()

    if abs(quantity_in_stock - old_qty) > 0.001:
        supabase.table("stock_movements").insert({
            "product_id": product_id,
            "movement_type": "ADJUSTMENT",
            "quantity": quantity_in_stock - old_qty,
            "note": f"Manual edit by {user}"
        }).execute()

    return RedirectResponse("/products", status_code=303)


@app.get("/delete/{product_id}")
def delete_product(request: Request, product_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    supabase.table("products").update({"is_active": False}).eq("id", product_id).execute()
    return RedirectResponse("/products", status_code=303)


# ============ CART & SALES ============

@app.get("/sell", response_class=HTMLResponse)
def sell_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    products = supabase.table("products").select("*").eq("is_active", True).order("name").execute().data
    rows = ""
    for p in products:
        qty = float(p.get("quantity_in_stock", 0))
        rows += f"""<tr>
            <td><strong>{p['name']}</strong><br><small>{p.get('sku','')}</small></td>
            <td>{qty} {p.get('unit','')}</td>
            <td>GHS {float(p['selling_price']):,.2f}</td>
            <td>
                <form method="post" action="/cart/add" style="display:flex;gap:5px;align-items:center;">
                    <input type="hidden" name="product_id" value="{p['id']}">
                    <input type="number" step="0.01" name="quantity" value="1" min="0.01" max="{qty}" style="width:70px;margin:0;padding:6px;">
                    <button type="submit" class="btn btn-success btn-small">+ Add</button>
                </form>
            </td>
        </tr>"""
    body = f"""
    <h2>New Sale — Add Items to Cart</h2>
    <div class="card">
        <a href="/cart" class="btn btn-success" style="margin-bottom:15px;">🛒 View Cart & Checkout</a>
        <table>
            <tr><th>Material</th><th>Stock</th><th>Price</th><th>Add to Cart</th></tr>
            {rows if rows else "<tr><td colspan='4'>No materials. <a href='/add'>Add one</a>.</td></tr>"}
        </table>
    </div>
    """
    return HTMLResponse(content=page("Sell", body, user))


@app.post("/cart/add")
async def cart_add(request: Request, product_id: int = Form(...), quantity: float = Form(...)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    cart = get_cart(request)

    # check if product already in cart
    found = False
    for item in cart:
        if item["product_id"] == product_id:
            item["quantity"] += quantity
            found = True
            break

    if not found:
        cart.append({"product_id": product_id, "quantity": quantity})

    return save_cart(cart)


@app.get("/cart", response_class=HTMLResponse)
def cart_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    cart = get_cart(request)

    if not cart:
        body = """
        <h2>🛒 Your Cart</h2>
        <div class="card">
            <p>Your cart is empty.</p>
            <a href="/sell" class="btn">Start Adding Items</a>
        </div>
        """
        return HTMLResponse(content=page("Cart", body, user))

    # fetch product details
    ids = [c["product_id"] for c in cart]
    products = supabase.table("products").select("*").in_("id", ids).execute().data
    product_map = {p["id"]: p for p in products}

    rows = ""
    total = 0
    for item in cart:
        p = product_map.get(item["product_id"])
        if not p:
            continue
        line = float(p["selling_price"]) * item["quantity"]
        total += line
        rows += f"""<tr>
            <td>{p['name']}</td>
            <td>{item['quantity']} {p.get('unit','')}</td>
            <td>GHS {float(p['selling_price']):,.2f}</td>
            <td>GHS {line:,.2f}</td>
            <td>
                <form method="post" action="/cart/remove" style="display:inline;">
                    <input type="hidden" name="product_id" value="{p['id']}">
                    <button type="submit" class="btn btn-danger btn-small">Remove</button>
                </form>
            </td>
        </tr>"""

    body = f"""
    <h2>🛒 Your Cart</h2>
    <div class="card">
        <table>
            <tr><th>Material</th><th>Qty</th><th>Price</th><th>Subtotal</th><th></th></tr>
            {rows}
        </table>
        <div class="cart-total">
            <strong>Total: GHS {total:,.2f}</strong>
        </div>
        <br>
        <form method="post" action="/cart/checkout">
            <button type="submit" class="btn btn-success">✅ Complete Sale</button>
            <a href="/sell" class="btn">+ Add More Items</a>
            <a href="/cart/clear" class="btn btn-danger">Clear Cart</a>
        </form>
    </div>
    """
    return HTMLResponse(content=page("Cart", body, user))


@app.post("/cart/remove")
async def cart_remove(request: Request, product_id: int = Form(...)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    cart = get_cart(request)
    cart = [item for item in cart if item["product_id"] != product_id]
    return save_cart(cart)


@app.get("/cart/clear")
def cart_clear(request: Request):
    response = RedirectResponse("/sell", status_code=303)
    response.delete_cookie("cart")
    return response


@app.post("/cart/checkout")
async def cart_checkout(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    cart = get_cart(request)
    if not cart:
        return RedirectResponse("/sell", status_code=303)

    ids = [c["product_id"] for c in cart]
    products = supabase.table("products").select("*").in_("id", ids).execute().data
    product_map = {p["id"]: p for p in products}

    # validate stock
    for item in cart:
        p = product_map.get(item["product_id"])
        if not p:
            continue
        if float(p["quantity_in_stock"]) < item["quantity"]:
            raise HTTPException(400, f"Not enough stock for {p['name']}")

    # create sale
    invoice_no = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    subtotal = 0.0
    for item in cart:
        p = product_map[item["product_id"]]
        subtotal += float(p["selling_price"]) * item["quantity"]

    sale_data = {
        "invoice_no": invoice_no,
        "subtotal": subtotal,
        "total": subtotal,
        "payment_method": "cash",
        "amount_paid": subtotal,
        "status": "completed",
        "user_id": user
    }
    sale_result = supabase.table("sales").insert(sale_data).execute()
    sale_id = sale_result.data[0]["id"]

    # create sale items, reduce stock, log movements
    for item in cart:
        p = product_map[item["product_id"]]
        qty = item["quantity"]
        unit_price = float(p["selling_price"])
        cost_price = float(p["cost_price"])
        line_total = qty * unit_price

        supabase.table("sale_items").insert({
            "sale_id": sale_id,
            "product_id": p["id"],
            "product_name": p["name"],
            "quantity": qty,
            "unit_price": unit_price,
            "cost_price": cost_price,
            "line_total": line_total
        }).execute()

        new_qty = float(p["quantity_in_stock"]) - qty
        supabase.table("products").update({"quantity_in_stock": new_qty}).eq("id", p["id"]).execute()

        supabase.table("stock_movements").insert({
            "product_id": p["id"],
            "movement_type": "OUT",
            "quantity": qty,
            "note": f"{invoice_no} — {p['name']} x {qty} — {user}"
        }).execute()

    # clear cart
    response = RedirectResponse(f"/receipt/{sale_id}", status_code=303)
    response.delete_cookie("cart")
    return response


# ============ RECEIPT ============

@app.get("/receipt/{sale_id}", response_class=HTMLResponse)
def receipt(request: Request, sale_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    sale = supabase.table("sales").select("*").eq("id", sale_id).single().execute().data
    items = supabase.table("sale_items").select("*").eq("sale_id", sale_id).execute().data

    rows = ""
    for it in items:
        rows += f"<tr><td>{it['product_name']}</td><td>{it['quantity']}</td><td>GHS {float(it['unit_price']):,.2f}</td><td>GHS {float(it['line_total']):,.2f}</td></tr>"

    body = f"""
        <div class="card" id="receipt">
        <h2 style="text-align:center;">🏗️ {SHOP_NAME}</h2>
        <p style="text-align:center;">{SHOP_ADDRESS}</p>
        <p style="text-align:center;">📞 {SHOP_PHONE}</p>
        <hr>
        <table>
            <tr><th>Item</th><th>Qty</th><th>Price</th><th>Total</th></tr>
            {rows}
        </table>
        <hr>
        <h3 style="text-align:right;">Total: GHS {float(sale['total']):,.2f}</h3>
        <p style="text-align:center;">Thank you for your business!</p>
    </div>
    <div style="text-align:center;margin-top:15px;">
        <button onclick="window.print()" class="btn btn-success">🖨️ Print Receipt</button>
        <a href="/sell" class="btn">New Sale</a>
        <a href="/" class="btn">Dashboard</a>
    </div>
    <style>
    @media print {{
        .header, .btn, button {{ display: none !important; }}
        body {{ background: white; }}
        .card {{ box-shadow: none; }}
    }}
    </style>
    """
    return HTMLResponse(content=page("Receipt", body, user))


# ============ CATEGORIES ============
# ============ CATEGORIES ============

@app.get("/categories", response_class=HTMLResponse)
def categories_list(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    cats = supabase.table("categories").select("*").order("name").execute().data

    # count products per category
    products = supabase.table("products").select("*").eq("is_active", True).execute().data
    counts = {}
    for p in products:
        cid = p.get("category_id")
        counts[cid] = counts.get(cid, 0) + 1

    rows = ""
    for c in cats:
        count = counts.get(c["id"], 0)
        rows += f"""<tr>
            <td><strong>{c['name']}</strong></td>
            <td>{c.get('description','')}</td>
            <td>{count} material{'s' if count != 1 else ''}</td>
            <td>
                <a href='/categories/delete/{c['id']}' class='btn btn-danger btn-small' onclick="return confirm('Delete category {c['name']}? Materials will be moved to Others.')">🗑️ Delete</a>
            </td>
        </tr>"""

    body = f"""
    <h2>Categories</h2>

    <div class="card">
        <h3>➕ Add New Category</h3>
        <form method="post" action="/categories/add">
            <label>Name</label>
            <input type="text" name="name" required placeholder="e.g. Roofing">
            <label>Description (optional)</label>
            <input type="text" name="description" placeholder="e.g. Roofing sheets and accessories">
            <button type="submit" class="btn btn-success">Add Category</button>
        </form>
    </div>

    <div class="card">
        <h3>All Categories ({len(cats)})</h3>
        <table>
            <tr><th>Category</th><th>Description</th><th>Materials</th><th></th></tr>
            {rows if rows else "<tr><td colspan='4'>No categories yet.</td></tr>"}
        </table>
    </div>
    """
    return HTMLResponse(content=page("Categories", body, user))


@app.post("/categories/add")
async def category_add(request: Request, name: str = Form(...), description: str = Form("")):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    existing = supabase.table("categories").select("*").eq("name", name).execute().data
    if not existing:
        supabase.table("categories").insert({"name": name, "description": description or None}).execute()

    return RedirectResponse("/categories", status_code=303)


@app.get("/categories/delete/{category_id}")
def category_delete(request: Request, category_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    # find or create "Others" category
    others = supabase.table("categories").select("*").eq("name", "Others").execute().data
    if others:
        others_id = others[0]["id"]
    else:
        new_others = supabase.table("categories").insert({"name": "Others", "description": "Anything that does not fit above"}).execute()
        others_id = new_others.data[0]["id"]

    # move any products from this category to Others
    supabase.table("products").update({"category_id": others_id}).eq("category_id", category_id).execute()

    # delete the category
    supabase.table("categories").delete().eq("id", category_id).execute()

    return RedirectResponse("/categories", status_code=303)
# ============ REPORTS ============

@app.get("/reports", response_class=HTMLResponse)
def reports(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    sales = supabase.table("sales").select("*").order("created_at", desc=True).execute().data

    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)

    def parse_date(s):
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            return None

    today_total = 0.0
    week_total = 0.0
    month_total = 0.0
    total_all = 0.0

    for s in sales:
        amount = float(s.get("total", 0))
        total_all += amount
        d = parse_date(s.get("created_at", ""))
        if d:
            if d >= today_start:
                today_total += amount
            if d >= week_start:
                week_total += amount
            if d >= month_start:
                month_total += amount

    items = supabase.table("sale_items").select("*").execute().data
    product_stats = {}
    for it in items:
        name = it.get("product_name", "Unknown")
        qty = float(it.get("quantity", 0))
        revenue = float(it.get("line_total", 0))
        cost = float(it.get("cost_price", 0)) * qty
        profit = revenue - cost
        if name not in product_stats:
            product_stats[name] = {"qty": 0, "revenue": 0, "profit": 0}
        product_stats[name]["qty"] += qty
        product_stats[name]["revenue"] += revenue
        product_stats[name]["profit"] += profit

    top = sorted(product_stats.items(), key=lambda x: x[1]["qty"], reverse=True)[:10]
    top_rows = "".join(
        f"<tr><td>{name}</td><td>{data['qty']:.0f}</td><td>GHS {data['revenue']:,.2f}</td><td>GHS {data['profit']:,.2f}</td></tr>"
        for name, data in top
    )

    recent_rows = ""
    for s in sales[:20]:
        recent_rows += f"<tr><td>{s.get('created_at','')[:16]}</td><td>{s.get('invoice_no','')}</td><td>GHS {float(s.get('total',0)):,.2f}</td><td>{s.get('user_id','')}</td><td><a href='/receipt/{s['id']}' class='btn btn-small'>View</a></td></tr>"

    body = f"""
    <h2>Reports</h2>

    <div class="grid">
        <div class="card stat"><div class="num">GHS {today_total:,.2f}</div><div class="label">Today</div></div>
        <div class="card stat"><div class="num">GHS {week_total:,.2f}</div><div class="label">Last 7 days</div></div>
        <div class="card stat"><div class="num">GHS {month_total:,.2f}</div><div class="label">Last 30 days</div></div>
        <div class="card stat"><div class="num">GHS {total_all:,.2f}</div><div class="label">All time</div></div>
    </div>

    <div class="card">
        <h3>🏆 Top Selling Materials</h3>
        <table>
            <tr><th>Material</th><th>Qty Sold</th><th>Revenue</th><th>Profit</th></tr>
            {top_rows if top_rows else "<tr><td colspan='4'>No sales yet.</td></tr>"}
        </table>
    </div>

    <div class="card">
        <h3>🧾 Recent Sales (last 20)</h3>
        <table>
            <tr><th>Date</th><th>Invoice</th><th>Total</th><th>User</th><th></th></tr>
            {recent_rows if recent_rows else "<tr><td colspan='5'>No sales yet.</td></tr>"}
        </table>
    </div>
    """
    return HTMLResponse(content=page("Reports", body, user))


@app.get("/health")
def health():
    return {"status": "ok"}