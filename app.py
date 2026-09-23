import os
import json
from datetime import datetime, timedelta
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from supabase import create_client, Client
from dotenv import load_dotenv
from auth import (
    create_session, get_current_user, COOKIE_NAME,
    verify_login, get_user_info, is_admin
)

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


def page(title, body, user=None, role=None):
    # Menu items — admin sees all, cashier sees limited
    if user and role == "admin":
        menu = ("<a href='/'>Home</a>"
                "<a href='/products'>Materials</a>"
                "<a href='/add'>Add</a>"
                "<a href='/sell'>New Sale</a>"
                "<a href='/cart'>Cart</a>"
                "<a href='/categories'>Categories</a>"
                "<a href='/reports'>Reports</a>"
                "<a href='/users'>Users</a>")
    elif user and role == "cashier":
        menu = ("<a href='/'>Home</a>"
                "<a href='/products'>Materials</a>"
                "<a href='/sell'>New Sale</a>"
                "<a href='/cart'>Cart</a>")
    else:
        menu = ""

    user_bar = ""
    if user:
        role_display = f" ({role})" if role else ""
        user_bar = f'<span style="margin-left:15px;font-size:13px;">👤 {user}{role_display} · <a href="/logout">Logout</a></span>'

    return f"""<!DOCTYPE html>
<html>
<head>
<title>{title} - {SHOP_NAME}</title>
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
<h1>🏗️ {SHOP_NAME}</h1>
<div>
{menu}
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
    user_info = verify_login(username, password)
    if user_info:
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
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    role = info.get("role", "cashier") if info else "cashier"

    products = supabase.table("products").select("*").eq("is_active", True).execute().data
    total_products = len(products)
    total_value = sum(float(p.get("quantity_in_stock", 0)) * float(p.get("cost_price", 0)) for p in products)
    low_stock = [p for p in products if float(p.get("quantity_in_stock", 0)) <= float(p.get("reorder_level", 0))]
    low_rows = "".join(f"<tr><td>{p['name']}</td><td class='low'>{p['quantity_in_stock']} {p['unit']}</td></tr>" for p in low_stock)

    admin_actions = ""
    if role == "admin":
        admin_actions = ("<a href='/add' class='btn'>Add Material</a>"
                         "<a href='/reports' class='btn'>📊 Reports</a>")

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
        {admin_actions}
        <a href="/products" class="btn">View All</a>
        <a href="/sell" class="btn btn-success">New Sale</a>
        <a href="/cart" class="btn">🛒 Cart</a>
    </div>
    """
    return HTMLResponse(content=page("Dashboard", body, username, role))


# ============ PRODUCTS ============

@app.get("/products", response_class=HTMLResponse)
def products_list(request: Request, search: str = ""):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    role = info.get("role", "cashier") if info else "cashier"

    query = supabase.table("products").select("*").eq("is_active", True)
    if search:
        query = query.ilike("name", f"%{search}%")
    products = query.order("name").execute().data

    show_actions = role == "admin"
    rows = ""
    for p in products:
        qty = float(p.get("quantity_in_stock", 0))
        reorder = float(p.get("reorder_level", 0))
        status = "low" if qty <= reorder else "ok"
        actions = ""
        if show_actions:
            actions = (f"<a href='/edit/{p['id']}' class='btn btn-warn btn-small'>✏️</a> "
                       f"<a href='/delete/{p['id']}' class='btn btn-danger btn-small' onclick=\"return confirm('Delete {p['name']}?')\">🗑️</a>")
        rows += f"""<tr>
            <td><strong>{p['name']}</strong><br><small>{p.get('sku','')}</small></td>
            <td>{p.get('unit','')}</td>
            <td class='{status}'>{qty}</td>
            <td>GHS {float(p['selling_price']):,.2f}</td>
            {f"<td>{actions}</td>" if show_actions else ""}
        </tr>"""

    headers = "<tr><th>Material</th><th>Unit</th><th>Stock</th><th>Price</th>"
    if show_actions:
        headers += "<th>Actions</th>"
    headers += "</tr>"

    add_button = "<a href='/add' class='btn'>➕ Add Material</a>" if role == "admin" else ""

    body = f"""
    <h2>All Materials</h2>
    <div class="card">
        {add_button}
        <form method="get" style="display:flex;gap:10px;margin-top:10px;">
            <input type="text" name="search" placeholder="Search..." value="{search}">
            <button>Search</button>
        </form>
    </div>
    <div class="card"><table>
        {headers}
        {rows if rows else f"<tr><td colspan='5'>No materials yet.</td></tr>"}
    </table></div>
    """
    return HTMLResponse(content=page("Materials", body, username, role))


@app.get("/add", response_class=HTMLResponse)
def add_form(request: Request):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can add materials")

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
    return HTMLResponse(content=page("Add", body, username, info.get("role")))


@app.post("/add")
async def add_product(request: Request, name: str = Form(...), sku: str = Form(...), category_id: str = Form(...), unit: str = Form(...), location: str = Form(""), cost_price: float = Form(...), selling_price: float = Form(...), quantity_in_stock: float = Form(...), reorder_level: float = Form(10)):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can add materials")

    data = {"name": name, "sku": sku, "category_id": int(category_id), "unit": unit, "location": location or None, "cost_price": cost_price, "selling_price": selling_price, "quantity_in_stock": quantity_in_stock, "reorder_level": reorder_level, "is_active": True}
    result = supabase.table("products").insert(data).execute()
    if result.data and quantity_in_stock > 0:
        supabase.table("stock_movements").insert({"product_id": result.data[0]["id"], "movement_type": "IN", "quantity": quantity_in_stock, "unit_cost": cost_price, "note": "Opening stock"}).execute()
    return RedirectResponse("/products", status_code=303)


@app.get("/edit/{product_id}", response_class=HTMLResponse)
def edit_form(request: Request, product_id: int):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can edit materials")

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
    return HTMLResponse(content=page("Edit", body, username, info.get("role")))


@app.post("/edit/{product_id}")
async def edit_product(request: Request, product_id: int, name: str = Form(...), sku: str = Form(...), category_id: str = Form(...), unit: str = Form(...), location: str = Form(""), cost_price: float = Form(...), selling_price: float = Form(...), quantity_in_stock: float = Form(...), reorder_level: float = Form(10)):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can edit materials")

    old = supabase.table("products").select("*").eq("id", product_id).single().execute().data
    old_qty = float(old.get("quantity_in_stock", 0))
    data = {"name": name, "sku": sku, "category_id": int(category_id), "unit": unit, "location": location or None, "cost_price": cost_price, "selling_price": selling_price, "quantity_in_stock": quantity_in_stock, "reorder_level": reorder_level}
    supabase.table("products").update(data).eq("id", product_id).execute()
    if abs(quantity_in_stock - old_qty) > 0.001:
        supabase.table("stock_movements").insert({"product_id": product_id, "movement_type": "ADJUSTMENT", "quantity": quantity_in_stock - old_qty, "note": f"Manual edit by {username}"}).execute()
    return RedirectResponse("/products", status_code=303)


@app.get("/delete/{product_id}")
def delete_product(request: Request, product_id: int):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can delete materials")

    supabase.table("products").update({"is_active": False}).eq("id", product_id).execute()
    return RedirectResponse("/products", status_code=303)


# ============ CART & SALES ============

@app.get("/sell", response_class=HTMLResponse)
def sell_page(request: Request):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    role = info.get("role", "cashier") if info else "cashier"

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
            {rows if rows else "<tr><td colspan='4'>No materials.</td></tr>"}
        </table>
    </div>
    """
    return HTMLResponse(content=page("Sell", body, username, role))


@app.post("/cart/add")
async def cart_add(request: Request, product_id: int = Form(...), quantity: float = Form(...)):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)

    cart = get_cart(request)
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
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    role = info.get("role", "cashier") if info else "cashier"

    cart = get_cart(request)
    if not cart:
        body = """
        <h2>🛒 Your Cart</h2>
        <div class="card">
            <p>Your cart is empty.</p>
            <a href="/sell" class="btn">Start Adding Items</a>
        </div>
        """
        return HTMLResponse(content=page("Cart", body, username, role))

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
            <strong>Subtotal: GHS {total:,.2f}</strong>
        </div>
        <br>
        <form method="post" action="/cart/checkout">
            <label>Discount Type</label>
            <select name="discount_type">
                <option value="none">No Discount</option>
                <option value="percent">Percentage (%)</option>
                <option value="fixed">Fixed Amount (GHS)</option>
            </select>
            <label>Discount Value (0 if none)</label>
            <input type="number" step="0.01" name="discount_value" value="0" min="0">
            <label>Payment Method</label>
            <select name="payment_method">
                <option value="Cash">💵 Cash</option>
                <option value="Mobile Money">📱 Mobile Money</option>
                <option value="Bank Transfer">🏦 Bank Transfer</option>
                <option value="Card">💳 Card</option>
            </select>
            <br>
            <button type="submit" class="btn btn-success">✅ Complete Sale</button>
            <a href="/sell" class="btn">+ Add More</a>
            <a href="/cart/clear" class="btn btn-danger">Clear Cart</a>
        </form>
    </div>
    """
    return HTMLResponse(content=page("Cart", body, username, role))


@app.post("/cart/remove")
async def cart_remove(request: Request, product_id: int = Form(...)):
    username = get_current_user(request)
    if not username:
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
async def cart_checkout(
    request: Request,
    discount_type: str = Form("none"),
    discount_value: float = Form(0),
    payment_method: str = Form("Cash")
):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)

    cart = get_cart(request)
    if not cart:
        return RedirectResponse("/sell", status_code=303)

    ids = [c["product_id"] for c in cart]
    products = supabase.table("products").select("*").in_("id", ids).execute().data
    product_map = {p["id"]: p for p in products}

    for item in cart:
        p = product_map.get(item["product_id"])
        if not p:
            continue
        if float(p["quantity_in_stock"]) < item["quantity"]:
            raise HTTPException(400, f"Not enough stock for {p['name']}")

    invoice_no = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    subtotal = 0.0
    for item in cart:
        p = product_map[item["product_id"]]
        subtotal += float(p["selling_price"]) * item["quantity"]

    discount_amount = 0.0
    if discount_type == "percent":
        discount_amount = subtotal * (discount_value / 100)
    elif discount_type == "fixed":
        discount_amount = discount_value
    if discount_amount > subtotal:
        discount_amount = subtotal
    final_total = subtotal - discount_amount

    sale_data = {
        "invoice_no": invoice_no,
        "subtotal": subtotal,
        "discount": discount_amount,
        "total": final_total,
        "payment_method": payment_method,
        "amount_paid": final_total,
        "status": "completed",
        "user_id": username,
        "cashier_name": username
    }
    sale_result = supabase.table("sales").insert(sale_data).execute()
    sale_id = sale_result.data[0]["id"]

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
            "note": f"{invoice_no} — {p['name']} x {qty} — {username}"
        }).execute()

    response = RedirectResponse(f"/receipt/{sale_id}", status_code=303)
    response.delete_cookie("cart")
    return response


# ============ RECEIPT ============

@app.get("/receipt/{sale_id}", response_class=HTMLResponse)
def receipt(request: Request, sale_id: int):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    role = info.get("role", "cashier") if info else "cashier"

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
        <p><strong>Invoice:</strong> {sale['invoice_no']}</p>
        <p><strong>Date:</strong> {sale['created_at'][:16]}</p>
        <p><strong>Cashier:</strong> {sale.get('cashier_name') or sale.get('user_id','')}</p>
        <hr>
        <table>
            <tr><th>Item</th><th>Qty</th><th>Price</th><th>Total</th></tr>
            {rows}
        </table>
        <hr>
        <p style="text-align:right;">Subtotal: GHS {float(sale['subtotal']):,.2f}</p>
        {f'<p style="text-align:right;">Discount: -GHS {float(sale.get("discount", 0)):,.2f}</p>' if float(sale.get("discount", 0)) > 0 else ''}
        <h3 style="text-align:right;">Total: GHS {float(sale['total']):,.2f}</h3>
        <p style="text-align:right;">Payment: {sale.get('payment_method','Cash')}</p>
        <hr>
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
    return HTMLResponse(content=page("Receipt", body, username, role))


# ============ CATEGORIES ============

@app.get("/categories", response_class=HTMLResponse)
def categories_list(request: Request):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can manage categories")

    cats = supabase.table("categories").select("*").order("name").execute().data
    products = supabase.table("products").select("*").eq("is_active", True).execute().data
    counts = {}
    for p in products:
        cid = p.get("category_id")
        counts[cid] = counts.get(cid, 0) + 1

    rows = ""
    for c in cats:
        count = counts.get(c["id"], 0)
        rows += f"""<tr>
           