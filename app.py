import os
import json
from datetime import datetime, timedelta
from io import BytesIO
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
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
    if user and role == "admin":
        menu = ("<a href='/'>Home</a>"
                "<a href='/products'>Materials</a>"
                "<a href='/customers'>Customers</a>"
                "<a href='/suppliers'>Suppliers</a>"
                "<a href='/add'>Add</a>"
                "<a href='/sell'>New Sale</a>"
                "<a href='/cart'>Cart</a>"
                "<a href='/expenses'>💰 Expenses</a>"
                "<a href='/alerts'>🚨 Alerts</a>"
                "<a href='/summary'>📅 Daily</a>"
                "<a href='/reports'>Reports</a>"
                "<a href='/users'>Users</a>")
    elif user and role == "cashier":
        menu = ("<a href='/'>Home</a>"
                "<a href='/products'>Materials</a>"
                "<a href='/customers'>Customers</a>"
                "<a href='/suppliers'>Suppliers</a>"
                "<a href='/sell'>New Sale</a>"
                "<a href='/cart'>Cart</a>")
    else:
        menu = ""

    user_bar = ""
    if user:
        role_display = f" ({role})" if role else ""
        user_bar = f'<span class="user-bar">👤 {user}{role_display} · <a href="/logout">Logout</a></span>'

    return f"""<!DOCTYPE html>
<html>
<head>
<title>{title} - {SHOP_NAME}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
* {{ box-sizing: border-box; }}
body {{ font-family: Arial, sans-serif; margin: 0; background: #f4f4f7; color: #222; }}
.header {{ background: #1e40af; color: white; padding: 15px 20px; }}
.header-top {{ display: flex; justify-content: space-between; align-items: center; }}
.header h1 {{ margin: 0; font-size: 20px; }}
.menu-toggle {{ display: none; background: transparent; border: 2px solid white; color: white; font-size: 22px; padding: 5px 12px; border-radius: 5px; cursor: pointer; }}
.menu-links {{ display: flex; flex-wrap: wrap; align-items: center; margin-top: 8px; }}
.menu-links a {{ color: white; text-decoration: none; margin-right: 15px; font-size: 14px; padding: 4px 0; }}
.menu-links a:hover {{ text-decoration: underline; }}
.user-bar {{ color: white; font-size: 13px; margin-left: auto; }}
.user-bar a {{ color: white; text-decoration: underline; }}
.container {{ max-width: 1100px; margin: 20px auto; padding: 0 15px; }}
.card {{ background: white; border-radius: 8px; padding: 20px; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
h2 {{ color: #1e40af; margin-top: 0; }}
h3 {{ color: #1e40af; margin-top: 15px; }}
.table-wrap {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
table {{ width: 100%; border-collapse: collapse; min-width: 500px; }}
th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #eee; }}
th {{ background: #f9fafb; }}
input {{ width: 100%; padding: 8px 10px; margin: 4px 0 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; background: white; }}
select {{ width: 100%; padding: 6px 8px; margin: 4px 0 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; background: white; line-height: 1.2; }}
label {{ font-size: 14px; color: #333; font-weight: bold; }}
button, .btn {{ background: #1e40af; color: white; padding: 10px 16px; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; text-decoration: none; display: inline-block; margin: 3px 0; }}
button:hover, .btn:hover {{ background: #1e3a8a; }}
.btn-success {{ background: #16a34a; }}
.btn-danger {{ background: #dc2626; }}
.btn-warn {{ background: #d97706; }}
.btn-small {{ padding: 6px 12px; font-size: 13px; }}
.low {{ color: #dc2626; font-weight: bold; }}
.ok {{ color: #16a34a; font-weight: bold; }}
.owed {{ color: #dc2626; font-weight: bold; font-size: 16px; }}
.clear {{ color: #16a34a; font-weight: bold; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
.stat {{ text-align: center; padding: 15px; }}
.stat .num {{ font-size: 28px; font-weight: bold; color: #1e40af; }}
.stat .label {{ color: #666; font-size: 13px; }}
.login-box {{ max-width: 400px; margin: 80px auto; }}
.cart-total {{ background: #fef3c7; padding: 15px; border-radius: 8px; margin-top: 10px; font-size: 18px; }}
.alert-box {{ background: #fee2e2; border: 2px solid #dc2626; }}
.big-num {{ font-size: 42px; font-weight: bold; color: #1e40af; text-align: center; padding: 20px; }}
.profit-box {{ background: #dcfce7; border-left: 6px solid #16a34a; }}
.loss-box {{ background: #fee2e2; border-left: 6px solid #dc2626; }}
@media (max-width: 768px) {{
    .menu-toggle {{ display: block; }}
    .menu-links {{ display: none; flex-direction: column; align-items: stretch; margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.25); }}
    .menu-links.open {{ display: flex; }}
    .menu-links a {{ display: block; padding: 14px 5px; border-bottom: 1px solid rgba(255,255,255,0.15); margin: 0; font-size: 16px; }}
    .user-bar {{ display: block; margin: 12px 0 0 0; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.25); font-size: 14px; }}
    .container {{ margin: 10px auto; padding: 0 10px; }}
    .card {{ padding: 15px; }}
    .grid {{ grid-template-columns: 1fr; }}
    .stat .num {{ font-size: 24px; }}
    h2 {{ font-size: 20px; }}
    table {{ min-width: 450px; }}
    th, td {{ padding: 8px; font-size: 14px; }}
    button, .btn {{ width: 100%; text-align: center; margin: 5px 0; }}
    .btn-small {{ width: auto; }}
    .big-num {{ font-size: 32px; }}
}}
</style>
</head>
<body>
<div class="header">
<div class="header-top">
<h1>🏗️ {SHOP_NAME}</h1>
<button class="menu-toggle" onclick="document.getElementById('menuLinks').classList.toggle('open')">☰</button>
</div>
<div class="menu-links" id="menuLinks">
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

    customers = supabase.table("customers").select("*").eq("is_active", True).execute().data
    total_owed = sum(float(c.get("balance", 0)) for c in customers)

    admin_actions = ""
    if role == "admin":
        admin_actions = ("<a href='/add' class='btn'>Add Material</a>"
                         "<a href='/reports' class='btn'>📊 Reports</a>"
                         "<a href='/summary' class='btn'>📅 Daily Summary</a>")

    alert_card = ""
    if low_stock:
        alert_card = f"""<div class="card alert-box">
            <h3 style="color:#dc2626;margin-top:0;">🚨 Low Stock Alert</h3>
            <p><strong>{len(low_stock)}</strong> items need restocking. <a href="/alerts" class="btn btn-small btn-danger">View Alerts</a></p>
        </div>"""

    body = f"""
    <h2>Dashboard</h2>
    {alert_card}
    <div class="grid">
        <div class="card stat"><div class="num">{total_products}</div><div class="label">Materials</div></div>
        <div class="card stat"><div class="num">GHS {total_value:,.2f}</div><div class="label">Inventory Value</div></div>
    </div>
    <div class="grid">
        <div class="card stat"><div class="num">{len(customers)}</div><div class="label">Customers</div></div>
        <div class="card stat"><div class="num" style="color:#dc2626;">GHS {total_owed:,.2f}</div><div class="label">Total Owed</div></div>
    </div>
    <div class="card">
        <h2>Low Stock ({len(low_stock)})</h2>
        {f"<div class='table-wrap'><table><tr><th>Material</th><th>In Stock</th></tr>{low_rows}</table></div>" if low_stock else "<p>All good!</p>"}
    </div>
    <div class="card">
        {admin_actions}
        <a href="/products" class="btn">View All</a>
        <a href="/sell" class="btn btn-success">New Sale</a>
        <a href="/cart" class="btn">🛒 Cart</a>
        <a href="/customers" class="btn">👥 Customers</a>
        <a href="/suppliers" class="btn">🚚 Suppliers</a>
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
        <form method="get" style="display:flex;gap:10px;margin-top:10px;flex-wrap:wrap;">
            <input type="text" name="search" placeholder="Search..." value="{search}" style="flex:1;min-width:200px;">
            <button type="submit">Search</button>
        </form>
    </div>
    <div class="card"><div class="table-wrap"><table>{headers}{rows if rows else "<tr><td colspan='5'>No materials yet.</td></tr>"}</table></div></div>
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
    cat_options = "".join(f"<option value='{c['id']}' {'selected' if c['id']==p.get('category_id') else ''}>{c['name']}</option>" for c in cats)
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


# ============ CUSTOMERS ============

@app.get("/customers", response_class=HTMLResponse)
def customers_list(request: Request, search: str = ""):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    role = info.get("role", "cashier") if info else "cashier"

    query = supabase.table("customers").select("*").eq("is_active", True)
    if search:
        query = query.ilike("name", f"%{search}%")
    customers = query.order("name").execute().data

    rows = ""
    for c in customers:
        balance = float(c.get("balance", 0))
        balance_class = "owed" if balance > 0 else "clear"
        rows += f"""<tr>
            <td><strong>{c['name']}</strong><br><small>{c.get('phone','')}</small></td>
            <td>{c.get('address','') or ''}</td>
            <td class='{balance_class}'>GHS {balance:,.2f}</td>
            <td>
                <a href='/customers/view/{c['id']}' class='btn btn-small'>👁️ View</a>
                <a href='/customers/pay/{c['id']}' class='btn btn-success btn-small'>💰 Pay</a>
            </td>
        </tr>"""

    total_owed = sum(float(c.get("balance", 0)) for c in customers)

    body = f"""
    <h2>👥 Customers</h2>
    <div class="card">
        <h3>Total Owed: <span style="color:#dc2626;">GHS {total_owed:,.2f}</span></h3>
    </div>
    <div class="card">
        <a href="/customers/add" class="btn btn-success">➕ Add Customer</a>
    </div>
    <div class="card">
        <form method="get" style="display:flex;gap:10px;flex-wrap:wrap;">
            <input type="text" name="search" placeholder="Search by name..." value="{search}" style="flex:1;min-width:200px;">
            <button type="submit">Search</button>
        </form>
    </div>
    <div class="card">
        <div class="table-wrap">
        <table>
            <tr><th>Customer</th><th>Address</th><th>Balance Owed</th><th>Actions</th></tr>
            {rows if rows else "<tr><td colspan='4'>No customers yet.</td></tr>"}
        </table>
        </div>
    </div>
    """
    return HTMLResponse(content=page("Customers", body, username, role))


@app.get("/customers/add", response_class=HTMLResponse)
def customer_add_form(request: Request):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    role = info.get("role", "cashier") if info else "cashier"
    body = """
    <h2>➕ Add New Customer</h2>
    <div class="card">
        <form method="post" action="/customers/add">
            <label>Full Name</label>
            <input type="text" name="name" required>
            <label>Phone Number</label>
            <input type="text" name="phone" placeholder="e.g. 0244123456">
            <label>Address / Location</label>
            <input type="text" name="address" placeholder="e.g. Menzezor">
            <label>Notes (optional)</label>
            <input type="text" name="notes">
            <button type="submit" class="btn btn-success">Create Customer</button>
            <a href="/customers" class="btn">Cancel</a>
        </form>
    </div>
    """
    return HTMLResponse(content=page("Add Customer", body, username, role))


@app.post("/customers/add")
async def customer_add(request: Request, name: str = Form(...), phone: str = Form(""), address: str = Form(""), notes: str = Form("")):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    supabase.table("customers").insert({
        "name": name,
        "phone": phone or None,
        "address": address or None,
        "notes": notes or None,
        "balance": 0,
        "is_active": True
    }).execute()
    return RedirectResponse("/customers", status_code=303)


@app.get("/customers/view/{customer_id}", response_class=HTMLResponse)
def customer_view(request: Request, customer_id: int):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    role = info.get("role", "cashier") if info else "cashier"

    c = supabase.table("customers").select("*").eq("id", customer_id).single().execute().data
    balance = float(c.get("balance", 0))

    sales = supabase.table("sales").select("*").eq("customer_id", customer_id).order("created_at", desc=True).execute().data
    sales_rows = ""
    for s in sales:
        sales_rows += f"<tr><td>{s.get('created_at','')[:16]}</td><td>{s.get('invoice_no','')}</td><td>GHS {float(s.get('total',0)):,.2f}</td><td>GHS {float(s.get('amount_paid_now',0)):,.2f}</td><td>GHS {float(s.get('amount_on_credit',0)):,.2f}</td></tr>"

    payments = supabase.table("customer_payments").select("*").eq("customer_id", customer_id).order("created_at", desc=True).execute().data
    pay_rows = ""
    for p in payments:
        pay_rows += f"<tr><td>{p.get('created_at','')[:16]}</td><td>GHS {float(p.get('amount',0)):,.2f}</td><td>{p.get('payment_method','')}</td><td>{p.get('note','') or ''}</td></tr>"

    body = f"""
    <h2>👤 {c['name']}</h2>
    <div class="card">
        <p><strong>Phone:</strong> {c.get('phone','') or '—'}</p>
        <p><strong>Address:</strong> {c.get('address','') or '—'}</p>
        <p><strong>Notes:</strong> {c.get('notes','') or '—'}</p>
        <h3>Current Balance: <span class="{'owed' if balance > 0 else 'clear'}">GHS {balance:,.2f}</span></h3>
        <a href="/customers/pay/{customer_id}" class="btn btn-success">💰 Record Payment</a>
    </div>
    <div class="card">
        <h3>📋 Purchase History</h3>
        <div class="table-wrap">
        <table>
            <tr><th>Date</th><th>Invoice</th><th>Total</th><th>Paid</th><th>Credit</th></tr>
            {sales_rows if sales_rows else "<tr><td colspan='5'>No purchases yet.</td></tr>"}
        </table>
        </div>
    </div>
    <div class="card">
        <h3>💵 Payment History</h3>
        <div class="table-wrap">
        <table>
            <tr><th>Date</th><th>Amount</th><th>Method</th><th>Note</th></tr>
            {pay_rows if pay_rows else "<tr><td colspan='4'>No payments yet.</td></tr>"}
        </table>
        </div>
    </div>
    <div class="card">
        <a href="/customers" class="btn">← Back to Customers</a>
    </div>
    """
    return HTMLResponse(content=page("Customer", body, username, role))


@app.get("/customers/pay/{customer_id}", response_class=HTMLResponse)
def customer_pay_form(request: Request, customer_id: int):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    role = info.get("role", "cashier") if info else "cashier"
    c = supabase.table("customers").select("*").eq("id", customer_id).single().execute().data
    balance = float(c.get("balance", 0))
    body = f"""
    <h2>💰 Record Payment from {c['name']}</h2>
    <div class="card">
        <p>Current balance: <strong class="owed">GHS {balance:,.2f}</strong></p>
        <form method="post" action="/customers/pay/{customer_id}">
            <label>Amount Paid (GHS)</label>
            <input type="number" step="0.01" name="amount" required min="0.01" max="{balance}">
            <label>Payment Method</label>
            <select name="payment_method">
                <option value="Cash">💵 Cash</option>
                <option value="Mobile Money">📱 Mobile Money</option>
                <option value="Bank Transfer">🏦 Bank Transfer</option>
                <option value="Card">💳 Card</option>
            </select>
            <label>Note (optional)</label>
            <input type="text" name="note">
            <button type="submit" class="btn btn-success">Record Payment</button>
            <a href="/customers/view/{customer_id}" class="btn">Cancel</a>
        </form>
    </div>
    """
    return HTMLResponse(content=page("Record Payment", body, username, role))


@app.post("/customers/pay/{customer_id}")
async def customer_pay(request: Request, customer_id: int, amount: float = Form(...), payment_method: str = Form("Cash"), note: str = Form("")):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)

    c = supabase.table("customers").select("*").eq("id", customer_id).single().execute().data
    balance = float(c.get("balance", 0))
    if amount > balance:
        amount = balance
    new_balance = balance - amount

    supabase.table("customers").update({"balance": new_balance}).eq("id", customer_id).execute()
    supabase.table("customer_payments").insert({
        "customer_id": customer_id,
        "amount": amount,
        "payment_method": payment_method,
        "note": note or None,
        "recorded_by": username
    }).execute()

    return RedirectResponse(f"/customers/view/{customer_id}", status_code=303)


# ============ SUPPLIERS ============

@app.get("/suppliers", response_class=HTMLResponse)
def suppliers_list(request: Request, search: str = ""):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    role = info.get("role", "cashier") if info else "cashier"

    query = supabase.table("suppliers").select("*")
    try:
        query = query.eq("is_active", True)
    except Exception:
        pass
    if search:
        query = query.ilike("name", f"%{search}%")
    suppliers = query.order("name").execute().data

    purchase_data = supabase.table("purchase_orders").select("*").execute().data
    totals = {}
    counts = {}
    for po in purchase_data:
        sid = po.get("supplier_id")
        totals[sid] = totals.get(sid, 0) + float(po.get("total", 0))
        counts[sid] = counts.get(sid, 0) + 1

    rows = ""
    for s in suppliers:
        spent = totals.get(s["id"], 0)
        num_orders = counts.get(s["id"], 0)
        rows += f"""<tr>
            <td><strong>{s['name']}</strong><br><small>{s.get('phone','')}</small></td>
            <td>{s.get('address','') or ''}</td>
            <td>{num_orders} orders</td>
            <td>GHS {spent:,.2f}</td>
            <td>
                <a href='/suppliers/view/{s['id']}' class='btn btn-small'>👁️ View</a>
                <a href='/purchases/new?supplier_id={s['id']}' class='btn btn-success btn-small'>📦 Restock</a>
            </td>
        </tr>"""

    body = f"""
    <h2>🚚 Suppliers</h2>
    <div class="card">
        <a href="/suppliers/add" class="btn btn-success">➕ Add Supplier</a>
        <a href="/purchases" class="btn">📦 All Purchases</a>
    </div>
    <div class="card">
        <form method="get" style="display:flex;gap:10px;flex-wrap:wrap;">
            <input type="text" name="search" placeholder="Search suppliers..." value="{search}" style="flex:1;min-width:200px;">
            <button type="submit">Search</button>
        </form>
    </div>
    <div class="card">
        <div class="table-wrap">
        <table>
            <tr><th>Supplier</th><th>Address</th><th>Orders</th><th>Total Spent</th><th>Actions</th></tr>
            {rows if rows else "<tr><td colspan='5'>No suppliers yet. Add one to start tracking purchases.</td></tr>"}
        </table>
        </div>
    </div>
    """
    return HTMLResponse(content=page("Suppliers", body, username, role))


@app.get("/suppliers/add", response_class=HTMLResponse)
def supplier_add_form(request: Request):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can add suppliers")
    body = """
    <h2>➕ Add New Supplier</h2>
    <div class="card">
        <form method="post" action="/suppliers/add">
            <label>Supplier Name</label>
            <input type="text" name="name" required placeholder="e.g. Dangote Cement Depot">
            <label>Phone Number</label>
            <input type="text" name="phone" placeholder="e.g. 0244123456">
            <label>Email (optional)</label>
            <input type="text" name="email">
            <label>Address</label>
            <input type="text" name="address" placeholder="e.g. Accra">
            <label>Notes (optional)</label>
            <input type="text" name="notes">
            <button type="submit" class="btn btn-success">Create Supplier</button>
            <a href="/suppliers" class="btn">Cancel</a>
        </form>
    </div>
    """
    return HTMLResponse(content=page("Add Supplier", body, username, info.get("role")))


@app.post("/suppliers/add")
async def supplier_add(request: Request, name: str = Form(...), phone: str = Form(""), email: str = Form(""), address: str = Form(""), notes: str = Form("")):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can add suppliers")
    supabase.table("suppliers").insert({
        "name": name,
        "phone": phone or None,
        "email": email or None,
        "address": address or None,
        "notes": notes or None,
        "is_active": True
    }).execute()
    return RedirectResponse("/suppliers", status_code=303)


@app.get("/suppliers/view/{supplier_id}", response_class=HTMLResponse)
def supplier_view(request: Request, supplier_id: int):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    role = info.get("role", "cashier") if info else "cashier"

    s = supabase.table("suppliers").select("*").eq("id", supplier_id).single().execute().data
    purchases = supabase.table("purchase_orders").select("*").eq("supplier_id", supplier_id).order("created_at", desc=True).execute().data

    rows = ""
    total_spent = 0
    for po in purchases:
        total_spent += float(po.get("total", 0))
        rows += f"""<tr>
            <td>{po.get('created_at','')[:16]}</td>
            <td>{po.get('po_number','')}</td>
            <td>GHS {float(po.get('total',0)):,.2f}</td>
            <td>{po.get('payment_method','')}</td>
            <td><a href='/purchases/view/{po['id']}' class='btn btn-small'>View</a></td>
        </tr>"""

    body = f"""
    <h2>🚚 {s['name']}</h2>
    <div class="card">
        <p><strong>Phone:</strong> {s.get('phone','') or '—'}</p>
        <p><strong>Email:</strong> {s.get('email','') or '—'}</p>
        <p><strong>Address:</strong> {s.get('address','') or '—'}</p>
        <p><strong>Notes:</strong> {s.get('notes','') or '—'}</p>
        <h3>Total Purchased: <span style="color:#dc2626;">GHS {total_spent:,.2f}</span></h3>
        <a href="/purchases/new?supplier_id={supplier_id}" class="btn btn-success">📦 Record New Purchase</a>
    </div>
    <div class="card">
        <h3>📋 Purchase History ({len(purchases)})</h3>
        <div class="table-wrap">
        <table>
            <tr><th>Date</th><th>PO Number</th><th>Total</th><th>Payment</th><th></th></tr>
            {rows if rows else "<tr><td colspan='5'>No purchases yet.</td></tr>"}
        </table>
        </div>
    </div>
    <div class="card">
        <a href="/suppliers" class="btn">← Back to Suppliers</a>
    </div>
    """
    return HTMLResponse(content=page("Supplier", body, username, role))


# ============ PURCHASES ============

@app.get("/purchases", response_class=HTMLResponse)
def purchases_list(request: Request):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    role = info.get("role", "cashier") if info else "cashier"

    purchases = supabase.table("purchase_orders").select("*").order("created_at", desc=True).limit(100).execute().data
    rows = ""
    total_all = 0
    for po in purchases:
        total_all += float(po.get("total", 0))
        rows += f"""<tr>
            <td>{po.get('created_at','')[:16]}</td>
            <td>{po.get('po_number','')}</td>
            <td>{po.get('supplier_name','')}</td>
            <td>GHS {float(po.get('total',0)):,.2f}</td>
            <td>{po.get('payment_method','')}</td>
            <td><a href='/purchases/view/{po['id']}' class='btn btn-small'>View</a></td>
        </tr>"""

    body = f"""
    <h2>📦 Purchase Orders</h2>
    <div class="card">
        <a href="/purchases/new" class="btn btn-success">➕ Record New Purchase</a>
        <a href="/suppliers" class="btn">🚚 Suppliers</a>
    </div>
    <div class="card">
        <h3>Total Spent: <span style="color:#dc2626;">GHS {total_all:,.2f}</span> ({len(purchases)} orders)</h3>
    </div>
    <div class="card">
        <div class="table-wrap">
        <table>
            <tr><th>Date</th><th>PO Number</th><th>Supplier</th><th>Total</th><th>Payment</th><th></th></tr>
            {rows if rows else "<tr><td colspan='6'>No purchases yet.</td></tr>"}
        </table>
        </div>
    </div>
    """
    return HTMLResponse(content=page("Purchases", body, username, role))


@app.get("/purchases/new", response_class=HTMLResponse)
def purchase_new_form(request: Request, supplier_id: str = ""):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can record purchases")

    suppliers = supabase.table("suppliers").select("*").order("name").execute().data
    sup_options = "".join(
        f"<option value='{s['id']}' {'selected' if str(s['id'])==str(supplier_id) else ''}>{s['name']}</option>"
        for s in suppliers
    )

    products = supabase.table("products").select("*").eq("is_active", True).order("name").execute().data
    prod_options = "".join(
        f"<option value='{p['id']}' data-cost='{p.get('cost_price',0)}'>{p['name']} ({p.get('unit','')})</option>"
        for p in products
    )

    body = f"""
    <h2>📦 Record New Purchase</h2>
    <div class="card">
        <form method="post" action="/purchases/new">
            <label>Supplier</label>
            <select name="supplier_id" required>
                <option value="">-- Select supplier --</option>
                {sup_options}
            </select>

            <h3>Items Purchased</h3>
            <p style="color:#666;font-size:14px;">Add each item you bought. Stock will be updated automatically.</p>

            <div id="items-container">
                <div class="item-row" style="border:1px solid #ddd;padding:15px;border-radius:8px;margin-bottom:10px;">
                    <label>Material</label>
                    <select name="product_id[]" required>
                        <option value="">-- Select material --</option>
                        {prod_options}
                    </select>
                    <label>Quantity</label>
                    <input type="number" step="0.01" name="quantity[]" required min="0.01">
                    <label>Unit Cost (GHS)</label>
                    <input type="number" step="0.01" name="unit_cost[]" required min="0.01">
                </div>
            </div>

            <button type="button" onclick="addItem()" class="btn">➕ Add Another Item</button>

            <h3 style="margin-top:20px;">Payment</h3>
            <label>Payment Method</label>
            <select name="payment_method">
                <option value="Cash">💵 Cash</option>
                <option value="Mobile Money">📱 Mobile Money</option>
                <option value="Bank Transfer">🏦 Bank Transfer</option>
                <option value="Card">💳 Card</option>
                <option value="Credit">📝 Credit (I Owe Supplier)</option>
            </select>

            <label>Amount Paid Now</label>
            <input type="number" step="0.01" name="amount_paid" value="0" min="0">

            <label>Note (optional)</label>
            <input type="text" name="note">

            <button type="submit" class="btn btn-success">✅ Save Purchase</button>
            <a href="/purchases" class="btn">Cancel</a>
        </form>
    </div>

    <script>
    function addItem() {{
        var container = document.getElementById('items-container');
        var firstRow = container.querySelector('.item-row');
        var newRow = firstRow.cloneNode(true);
        newRow.querySelectorAll('input').forEach(function(inp) {{ inp.value = ''; }});
        newRow.querySelectorAll('select').forEach(function(sel) {{ sel.selectedIndex = 0; }});
        container.appendChild(newRow);
    }}
    </script>
    """
    return HTMLResponse(content=page("New Purchase", body, username, info.get("role")))


@app.post("/purchases/new")
async def purchase_new(request: Request):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can record purchases")

    form = await request.form()
    supplier_id = form.get("supplier_id")
    if not supplier_id:
        raise HTTPException(400, "Supplier is required")

    supplier = supabase.table("suppliers").select("*").eq("id", int(supplier_id)).single().execute().data
    supplier_name = supplier["name"] if supplier else "Unknown"

    product_ids = form.getlist("product_id[]")
    quantities = form.getlist("quantity[]")
    unit_costs = form.getlist("unit_cost[]")

    if not product_ids or len(product_ids) != len(quantities):
        raise HTTPException(400, "Invalid items")

    payment_method = form.get("payment_method", "Cash")
    amount_paid = float(form.get("amount_paid", 0) or 0)
    note = form.get("note", "")

    items = []
    total = 0.0
    for i in range(len(product_ids)):
        if not product_ids[i]:
            continue
        pid = int(product_ids[i])
        qty = float(quantities[i])
        cost = float(unit_costs[i])
        line = qty * cost
        total += line

        product = supabase.table("products").select("*").eq("id", pid).single().execute().data
        items.append({"product_id": pid, "product_name": product["name"], "quantity": qty, "unit_cost": cost, "line_total": line})

    if not items:
        raise HTTPException(400, "At least one item required")

    credit_amount = 0.0
    if payment_method == "Credit":
        credit_amount = total - amount_paid
        if credit_amount < 0:
            credit_amount = 0

    po_number = f"PO-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    po_data = {
        "po_number": po_number,
        "supplier_id": int(supplier_id),
        "supplier_name": supplier_name,
        "total": total,
        "amount_paid": amount_paid if payment_method == "Credit" else total,
        "amount_owed": credit_amount,
        "payment_method": payment_method,
        "status": "received",
        "note": note or None,
        "recorded_by": username
    }
    result = supabase.table("purchase_orders").insert(po_data).execute()
    purchase_id = result.data[0]["id"]

    for it in items:
        supabase.table("purchase_order_items").insert({
            "purchase_id": purchase_id,
            "product_id": it["product_id"],
            "product_name": it["product_name"],
            "quantity": it["quantity"],
            "unit_cost": it["unit_cost"],
            "line_total": it["line_total"]
        }).execute()

        p = supabase.table("products").select("*").eq("id", it["product_id"]).single().execute().data
        new_qty = float(p.get("quantity_in_stock", 0)) + it["quantity"]
        supabase.table("products").update({
            "quantity_in_stock": new_qty,
            "cost_price": it["unit_cost"]
        }).eq("id", it["product_id"]).execute()

        supabase.table("stock_movements").insert({
            "product_id": it["product_id"],
            "movement_type": "IN",
            "quantity": it["quantity"],
            "unit_cost": it["unit_cost"],
            "reference": po_number,
            "note": f"Purchase from {supplier_name} — {it['product_name']} x {it['quantity']}"
        }).execute()

    return RedirectResponse(f"/purchases/view/{purchase_id}", status_code=303)


@app.get("/purchases/view/{purchase_id}", response_class=HTMLResponse)
def purchase_view(request: Request, purchase_id: int):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    role = info.get("role", "cashier") if info else "cashier"

    po = supabase.table("purchase_orders").select("*").eq("id", purchase_id).single().execute().data
    items = supabase.table("purchase_order_items").select("*").eq("purchase_id", purchase_id).execute().data

    rows = ""
    for it in items:
        rows += f"<tr><td>{it['product_name']}</td><td>{it['quantity']}</td><td>GHS {float(it['unit_cost']):,.2f}</td><td>GHS {float(it['line_total']):,.2f}</td></tr>"

    body = f"""
    <div class="card">
        <h2>📦 Purchase Order {po['po_number']}</h2>
        <p><strong>Supplier:</strong> {po.get('supplier_name','')}</p>
        <p><strong>Date:</strong> {po.get('created_at','')[:16]}</p>
        <p><strong>Recorded by:</strong> {po.get('recorded_by','')}</p>
        <hr>
        <div class="table-wrap">
        <table>
            <tr><th>Item</th><th>Qty</th><th>Unit Cost</th><th>Total</th></tr>
            {rows}
        </table>
        </div>
        <hr>
        <h3 style="text-align:right;">Total: GHS {float(po['total']):,.2f}</h3>
        <p style="text-align:right;">Paid: GHS {float(po.get('amount_paid', 0)):,.2f}</p>
        {f'<p style="text-align:right;color:#dc2626;">Owed: GHS {float(po.get("amount_owed", 0)):,.2f}</p>' if float(po.get("amount_owed", 0)) > 0 else ''}
        <p style="text-align:right;">Payment: {po.get('payment_method','')}</p>
        {f'<p><strong>Note:</strong> {po.get("note","")}</p>' if po.get("note") else ''}
    </div>
    <div class="card">
        <a href="/purchases" class="btn">← Back to Purchases</a>
        <a href="/suppliers/view/{po['supplier_id']}" class="btn">View Supplier</a>
    </div>
    """
    return HTMLResponse(content=page("Purchase", body, username, role))


# ============ EXPENSES ============

@app.get("/expenses", response_class=HTMLResponse)
def expenses_list(request: Request, month: str = ""):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    role = info.get("role", "cashier") if info else "cashier"
    if role != "admin":
        raise HTTPException(403, "Only admins can view expenses")

    expenses = supabase.table("expenses").select("*").order("expense_date", desc=True).execute().data

    now = datetime.now()
    if not month:
        month = now.strftime("%Y-%m")

    filtered = []
    for e in expenses:
        d = str(e.get("expense_date", ""))[:7]
        if d == month:
            filtered.append(e)

    total_month = sum(float(e.get("amount", 0)) for e in filtered)

    cat_totals = {}
    for e in filtered:
        cat = e.get("category_name", "Unknown")
        cat_totals[cat] = cat_totals.get(cat, 0) + float(e.get("amount", 0))

    rows = ""
    for e in filtered:
        rows += f"""<tr>
            <td>{e.get('expense_date','')}</td>
            <td>{e.get('category_name','')}</td>
            <td>GHS {float(e.get('amount',0)):,.2f}</td>
            <td>{e.get('description','') or ''}</td>
            <td>{e.get('paid_to','') or ''}</td>
            <td>{e.get('payment_method','')}</td>
            <td><a href='/expenses/delete/{e['id']}' class='btn btn-danger btn-small' onclick="return confirm('Delete this expense?')">🗑️</a></td>
        </tr>"""

    cat_rows = ""
    for cat, amt in sorted(cat_totals.items(), key=lambda x: -x[1]):
        pct = (amt / total_month * 100) if total_month > 0 else 0
        cat_rows += f"<tr><td>{cat}</td><td>GHS {amt:,.2f}</td><td>{pct:.0f}%</td></tr>"

    body = f"""
    <h2>💰 Expenses</h2>
    <div class="card">
        <a href="/expenses/new" class="btn btn-success">➕ Add Expense</a>
        <a href="/expenses/export?month={month}" class="btn">📥 Export Month to Excel</a>
    </div>
    <div class="card">
        <form method="get" style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end;">
            <div style="flex:1;min-width:200px;">
                <label>Month (YYYY-MM)</label>
                <input type="text" name="month" value="{month}" placeholder="2026-09">
            </div>
            <button type="submit">Filter</button>
        </form>
    </div>
    <div class="card" style="background:#fef3c7;">
        <h3 style="margin:0;">Total for {month}: <span style="color:#dc2626;">GHS {total_month:,.2f}</span></h3>
        <p style="margin:5px 0 0 0;">{len(filtered)} expenses recorded</p>
    </div>
    <div class="card">
        <h3>📊 Breakdown by Category</h3>
        <div class="table-wrap">
        <table>
            <tr><th>Category</th><th>Amount</th><th>% of Total</th></tr>
            {cat_rows if cat_rows else "<tr><td colspan='3'>No expenses this month.</td></tr>"}
        </table>
        </div>
    </div>
    <div class="card">
        <h3>📋 All Expenses ({len(filtered)})</h3>
        <div class="table-wrap">
        <table>
            <tr><th>Date</th><th>Category</th><th>Amount</th><th>Description</th><th>Paid To</th><th>Method</th><th></th></tr>
            {rows if rows else "<tr><td colspan='7'>No expenses this month.</td></tr>"}
        </table>
        </div>
    </div>
    """
    return HTMLResponse(content=page("Expenses", body, username, role))


@app.get("/expenses/new", response_class=HTMLResponse)
def expense_new_form(request: Request):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can add expenses")

    cats = supabase.table("expense_categories").select("*").order("name").execute().data
    cat_options = "".join(f"<option value='{c['id']}' data-name='{c['name']}'>{c['name']}</option>" for c in cats)

    today = datetime.now().strftime("%Y-%m-%d")

    body = f"""
    <h2>➕ Add Expense</h2>
    <div class="card">
        <form method="post" action="/expenses/new">
            <label>Date</label>
            <input type="date" name="expense_date" value="{today}" required>

            <label>Category</label>
            <select name="category_id" required>
                <option value="">-- Select category --</option>
                {cat_options}
            </select>

            <label>Amount (GHS)</label>
            <input type="number" step="0.01" name="amount" required min="0.01">

            <label>Description</label>
            <input type="text" name="description" placeholder="e.g. September rent">

            <label>Paid To</label>
            <input type="text" name="paid_to" placeholder="e.g. Landlord name">

            <label>Payment Method</label>
            <select name="payment_method">
                <option value="Cash">💵 Cash</option>
                <option value="Mobile Money">📱 Mobile Money</option>
                <option value="Bank Transfer">🏦 Bank Transfer</option>
                <option value="Card">💳 Card</option>
            </select>

            <button type="submit" class="btn btn-success">Save Expense</button>
            <a href="/expenses" class="btn">Cancel</a>
        </form>
    </div>
    """
    return HTMLResponse(content=page("Add Expense", body, username, info.get("role")))


@app.post("/expenses/new")
async def expense_new(request: Request, expense_date: str = Form(...), category_id: str = Form(...), amount: float = Form(...), description: str = Form(""), paid_to: str = Form(""), payment_method: str = Form("Cash")):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can add expenses")

    cat = supabase.table("expense_categories").select("*").eq("id", int(category_id)).single().execute().data
    cat_name = cat["name"] if cat else "Unknown"

    supabase.table("expenses").insert({
        "expense_date": expense_date,
        "category_id": int(category_id),
        "category_name": cat_name,
        "amount": amount,
        "description": description or None,
        "paid_to": paid_to or None,
        "payment_method": payment_method,
        "recorded_by": username
    }).execute()

    return RedirectResponse("/expenses", status_code=303)


@app.get("/expenses/delete/{expense_id}")
def expense_delete(request: Request, expense_id: int):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can delete expenses")
    supabase.table("expenses").delete().eq("id", expense_id).execute()
    return RedirectResponse("/expenses", status_code=303)


@app.get("/expenses/export")
def expenses_export(request: Request, month: str = ""):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can export expenses")

    if not month:
        month = datetime.now().strftime("%Y-%m")

    all_expenses = supabase.table("expenses").select("*").order("expense_date", desc=True).execute().data
    expenses = [e for e in all_expenses if str(e.get("expense_date", ""))[:7] == month]

    wb = Workbook()
    ws = wb.active
    ws.title = "Expenses"
    headers = ["Date", "Category", "Amount", "Description", "Paid To", "Payment Method", "Recorded By"]
    style_header(ws, headers)
    for e in expenses:
        ws.append([
            str(e.get("expense_date", "")),
            e.get("category_name", ""),
            float(e.get("amount", 0)),
            e.get("description", "") or "",
            e.get("paid_to", "") or "",
            e.get("payment_method", ""),
            e.get("recorded_by", "") or "",
        ])

    widths = [15, 15, 12, 30, 20, 15, 15]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i)].width = w

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=OBOLO_expenses_{month}.xlsx"}
    )


# ============ LOW STOCK ALERTS ============

@app.get("/alerts", response_class=HTMLResponse)
def alerts_page(request: Request):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can view alerts")

    products = supabase.table("products").select("*").eq("is_active", True).execute().data
    low_stock = []
    out_of_stock = []
    for p in products:
        qty = float(p.get("quantity_in_stock", 0))
        reorder = float(p.get("reorder_level", 0))
        if qty <= 0:
            out_of_stock.append(p)
        elif qty <= reorder:
            low_stock.append(p)

    low_stock.sort(key=lambda p: float(p.get("quantity_in_stock", 0)))

    out_rows = ""
    for p in out_of_stock:
        out_rows += f"""<tr>
            <td><strong>{p['name']}</strong><br><small>{p.get('sku','')}</small></td>
            <td>{p.get('unit','')}</td>
            <td class='low'>0</td>
            <td>{p.get('reorder_level', 0)}</td>
            <td><a href='/purchases/new' class='btn btn-success btn-small'>📦 Restock</a></td>
        </tr>"""

    low_rows = ""
    for p in low_stock:
        qty = float(p.get("quantity_in_stock", 0))
        reorder = float(p.get("reorder_level", 0))
        low_rows += f"""<tr>
            <td><strong>{p['name']}</strong><br><small>{p.get('sku','')}</small></td>
            <td>{p.get('unit','')}</td>
            <td class='low'>{qty}</td>
            <td>{reorder}</td>
            <td><a href='/purchases/new' class='btn btn-success btn-small'>📦 Restock</a></td>
        </tr>"""

    body = f"""
    <h2>🚨 Low Stock Alerts</h2>
    <div class="card alert-box">
        <h3 style="color:#dc2626;margin:0;">⚠️ Summary</h3>
        <p style="font-size:18px;margin:10px 0 0 0;">
            <strong>{len(out_of_stock)}</strong> items OUT OF STOCK &nbsp;·&nbsp;
            <strong>{len(low_stock)}</strong> items running LOW
        </p>
    </div>
    <div class="card">
        <h3 style="color:#dc2626;">❌ Out of Stock ({len(out_of_stock)})</h3>
        <div class="table-wrap">
        <table>
            <tr><th>Material</th><th>Unit</th><th>In Stock</th><th>Reorder At</th><th></th></tr>
            {out_rows if out_rows else "<tr><td colspan='5'>None. Great!</td></tr>"}
        </table>
        </div>
    </div>
    <div class="card">
        <h3 style="color:#d97706;">⚠️ Running Low ({len(low_stock)})</h3>
        <div class="table-wrap">
        <table>
            <tr><th>Material</th><th>Unit</th><th>In Stock</th><th>Reorder At</th><th></th></tr>
            {low_rows if low_rows else "<tr><td colspan='5'>None. Great!</td></tr>"}
        </table>
        </div>
    </div>
    <div class="card">
        <a href="/products" class="btn">View All Materials</a>
        <a href="/" class="btn">Dashboard</a>
    </div>
    """
    return HTMLResponse(content=page("Alerts", body, username, info.get("role")))


# ============ DAILY SUMMARY ============

@app.get("/summary", response_class=HTMLResponse)
def daily_summary(request: Request):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can view the summary")

    today = datetime.now().date()

    sales = supabase.table("sales").select("*").order("created_at", desc=True).execute().data

    def parse_date(s):
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            return None

    today_sales = []
    for s in sales:
        d = parse_date(s.get("created_at", ""))
        if d and d.date() == today:
            today_sales.append(s)

    total_today = 0.0
    credit_today = 0.0
    payment_breakdown = {}
    cashier_breakdown = {}
    for s in today_sales:
        amount = float(s.get("total", 0))
        total_today += amount
        credit_today += float(s.get("amount_on_credit", 0))
        pm = s.get("payment_method", "Cash")
        payment_breakdown[pm] = payment_breakdown.get(pm, 0) + amount
        cashier = s.get("cashier_name") or s.get("user_id", "Unknown")
        cashier_breakdown[cashier] = cashier_breakdown.get(cashier, 0) + amount

    if today_sales:
        sale_ids = [s["id"] for s in today_sales]
        all_items = supabase.table("sale_items").select("*").execute().data
        today_items = [it for it in all_items if it.get("sale_id") in sale_ids]
    else:
        today_items = []

    product_totals = {}
    for it in today_items:
        name = it.get("product_name", "Unknown")
        qty = float(it.get("quantity", 0))
        rev = float(it.get("line_total", 0))
        if name not in product_totals:
            product_totals[name] = {"qty": 0, "revenue": 0}
        product_totals[name]["qty"] += qty
        product_totals[name]["revenue"] += rev

    top_today = sorted(product_totals.items(), key=lambda x: x[1]["qty"], reverse=True)[:5]
    top_rows = "".join(
        f"<tr><td>{name}</td><td>{data['qty']:.0f}</td><td>GHS {data['revenue']:,.2f}</td></tr>"
        for name, data in top_today
    )

    pay_rows = ""
    for method, amount in sorted(payment_breakdown.items(), key=lambda x: -x[1]):
        pct = (amount / total_today * 100) if total_today > 0 else 0
        pay_rows += f"<tr><td>{method}</td><td>GHS {amount:,.2f}</td><td>{pct:.0f}%</td></tr>"

    cashier_rows = ""
    for c, amount in sorted(cashier_breakdown.items(), key=lambda x: -x[1]):
        cashier_rows += f"<tr><td>{c}</td><td>GHS {amount:,.2f}</td></tr>"

    body = f"""
    <h2>📅 Daily Summary — {today.strftime('%A, %d %B %Y')}</h2>

    <div class="card" style="background:#dbeafe;border-left:6px solid #1e40af;">
        <div class="big-num">GHS {total_today:,.2f}</div>
        <div style="text-align:center;color:#666;font-size:16px;">Total Sales Today</div>
    </div>

    <div class="grid">
        <div class="card stat"><div class="num">{len(today_sales)}</div><div class="label">Sales Made</div></div>
        <div class="card stat"><div class="num">{len(today_items)}</div><div class="label">Items Sold</div></div>
    </div>

    <div class="grid">
        <div class="card stat"><div class="num" style="color:#dc2626;">GHS {credit_today:,.2f}</div><div class="label">On Credit Today</div></div>
        <div class="card stat"><div class="num" style="color:#16a34a;">GHS {total_today - credit_today:,.2f}</div><div class="label">Cash/Paid Today</div></div>
    </div>

    <div class="card">
        <h3>💳 Payment Breakdown</h3>
        <div class="table-wrap">
        <table>
            <tr><th>Method</th><th>Amount</th><th>%</th></tr>
            {pay_rows if pay_rows else "<tr><td colspan='3'>No sales today yet.</td></tr>"}
        </table>
        </div>
    </div>

    <div class="card">
        <h3>🏆 Top Materials Today</h3>
        <div class="table-wrap">
        <table>
            <tr><th>Material</th><th>Qty Sold</th><th>Revenue</th></tr>
            {top_rows if top_rows else "<tr><td colspan='3'>No materials sold today.</td></tr>"}
        </table>
        </div>
    </div>

    <div class="card">
        <h3>👤 Sales by Cashier</h3>
        <div class="table-wrap">
        <table>
            <tr><th>Cashier</th><th>Amount</th></tr>
            {cashier_rows if cashier_rows else "<tr><td colspan='2'>No sales today yet.</td></tr>"}
        </table>
        </div>
    </div>

    <div class="card" style="text-align:center;">
        <button onclick="window.print()" class="btn btn-success">🖨️ Print Summary</button>
        <a href="/" class="btn">Dashboard</a>
        <a href="/reports" class="btn">Full Reports</a>
    </div>

    <style>
    @media print {{
        .header, .btn, button {{ display: none !important; }}
        body {{ background: white; }}
        .card {{ box-shadow: none; border: 1px solid #ddd; }}
    }}
    </style>
    """
    return HTMLResponse(content=page("Daily Summary", body, username, info.get("role")))


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
                <form method="post" action="/cart/add" style="display:flex;gap:5px;align-items:center;flex-wrap:wrap;">
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
        <div class="table-wrap">
        <table>
            <tr><th>Material</th><th>Stock</th><th>Price</th><th>Add to Cart</th></tr>
            {rows if rows else "<tr><td colspan='4'>No materials.</td></tr>"}
        </table>
        </div>
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

    customers = supabase.table("customers").select("*").eq("is_active", True).order("name").execute().data
    cust_options = "".join(f"<option value='{c['id']}'>{c['name']} — {c.get('phone','') or ''}</option>" for c in customers)

    body = f"""
    <h2>🛒 Your Cart</h2>
    <div class="card">
        <div class="table-wrap">
        <table>
            <tr><th>Material</th><th>Qty</th><th>Price</th><th>Subtotal</th><th></th></tr>
            {rows}
        </table>
        </div>
        <div class="cart-total"><strong>Subtotal: GHS {total:,.2f}</strong></div>
        <br>
        <form method="post" action="/cart/checkout">
            <label>Customer (leave blank for walk-in)</label>
            <select name="customer_id">
                <option value="">— Walk-in customer —</option>
                {cust_options}
            </select>
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
                <option value="Credit">📝 Credit (Customer Owes)</option>
            </select>
            <label>Amount Paid Now (if credit)</label>
            <input type="number" step="0.01" name="amount_paid_now" value="0" min="0">
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
    customer_id: str = Form(""),
    discount_type: str = Form("none"),
    discount_value: float = Form(0),
    payment_method: str = Form("Cash"),
    amount_paid_now: float = Form(0)
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

    customer_name = None
    cust_obj = None
    if customer_id:
        try:
            cust_obj = supabase.table("customers").select("*").eq("id", int(customer_id)).single().execute().data
            customer_name = cust_obj["name"] if cust_obj else None
        except Exception:
            cust_obj = None

    credit_amount = 0.0
    if payment_method == "Credit" and cust_obj:
        credit_amount = final_total - amount_paid_now
        if credit_amount < 0:
            credit_amount = 0
    elif payment_method == "Credit" and not cust_obj:
        raise HTTPException(400, "Credit sales require a registered customer")

    sale_data = {
        "invoice_no": invoice_no,
        "customer_id": int(customer_id) if customer_id else None,
        "customer_name": customer_name,
        "subtotal": subtotal,
        "discount": discount_amount,
        "total": final_total,
        "payment_method": payment_method,
        "amount_paid": final_total - credit_amount if payment_method == "Credit" else final_total,
        "amount_paid_now": amount_paid_now if payment_method == "Credit" else final_total,
        "amount_on_credit": credit_amount,
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
        supabase.table("sale_items").insert({"sale_id": sale_id, "product_id": p["id"], "product_name": p["name"], "quantity": qty, "unit_price": unit_price, "cost_price": cost_price, "line_total": line_total}).execute()
        new_qty = float(p["quantity_in_stock"]) - qty
        supabase.table("products").update({"quantity_in_stock": new_qty}).eq("id", p["id"]).execute()
        supabase.table("stock_movements").insert({"product_id": p["id"], "movement_type": "OUT", "quantity": qty, "note": f"{invoice_no} — {p['name']} x {qty} — {username}"}).execute()

    if credit_amount > 0 and cust_obj:
        new_balance = float(cust_obj.get("balance", 0)) + credit_amount
        supabase.table("customers").update({"balance": new_balance}).eq("id", cust_obj["id"]).execute()

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

    customer_line = ""
    if sale.get("customer_name"):
        customer_line = f"<p><strong>Customer:</strong> {sale['customer_name']}</p>"

    credit_line = ""
    if float(sale.get("amount_on_credit", 0)) > 0:
        credit_line = f'<p style="text-align:right;color:#dc2626;">On Credit: GHS {float(sale.get("amount_on_credit", 0)):,.2f}</p>'

    body = f"""
    <div class="card" id="receipt">
        <h2 style="text-align:center;">🏗️ {SHOP_NAME}</h2>
        <p style="text-align:center;">{SHOP_ADDRESS}</p>
        <p style="text-align:center;">📞 {SHOP_PHONE}</p>
        <hr>
        <p><strong>Invoice:</strong> {sale['invoice_no']}</p>
        <p><strong>Date:</strong> {sale['created_at'][:16]}</p>
        <p><strong>Cashier:</strong> {sale.get('cashier_name') or sale.get('user_id','')}</p>
        {customer_line}
        <hr>
        <div class="table-wrap">
        <table>
            <tr><th>Item</th><th>Qty</th><th>Price</th><th>Total</th></tr>
            {rows}
        </table>
        </div>
        <hr>
        <p style="text-align:right;">Subtotal: GHS {float(sale['subtotal']):,.2f}</p>
        {f'<p style="text-align:right;">Discount: -GHS {float(sale.get("discount", 0)):,.2f}</p>' if float(sale.get("discount", 0)) > 0 else ''}
        <h3 style="text-align:right;">Total: GHS {float(sale['total']):,.2f}</h3>
        <p style="text-align:right;">Payment: {sale.get('payment_method','Cash')}</p>
        {credit_line}
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
            <td><strong>{c['name']}</strong></td>
            <td>{c.get('description','')}</td>
            <td>{count} material{'s' if count != 1 else ''}</td>
            <td><a href='/categories/delete/{c['id']}' class='btn btn-danger btn-small' onclick="return confirm('Delete {c['name']}?')">🗑️</a></td>
        </tr>"""
    body = f"""
    <h2>Categories</h2>
    <div class="card">
        <h3>➕ Add New Category</h3>
        <form method="post" action="/categories/add">
            <label>Name</label>
            <input type="text" name="name" required placeholder="e.g. Roofing">
            <label>Description (optional)</label>
            <input type="text" name="description">
            <button type="submit" class="btn btn-success">Add Category</button>
        </form>
    </div>
    <div class="card">
        <h3>All Categories ({len(cats)})</h3>
        <div class="table-wrap">
        <table>
            <tr><th>Category</th><th>Description</th><th>Materials</th><th></th></tr>
            {rows if rows else "<tr><td colspan='4'>No categories yet.</td></tr>"}
        </table>
        </div>
    </div>
    """
    return HTMLResponse(content=page("Categories", body, username, info.get("role")))


@app.post("/categories/add")
async def category_add(request: Request, name: str = Form(...), description: str = Form("")):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can add categories")
    existing = supabase.table("categories").select("*").eq("name", name).execute().data
    if not existing:
        supabase.table("categories").insert({"name": name, "description": description or None}).execute()
    return RedirectResponse("/categories", status_code=303)


@app.get("/categories/delete/{category_id}")
def category_delete(request: Request, category_id: int):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can delete categories")
    others = supabase.table("categories").select("*").eq("name", "Others").execute().data
    if others:
        others_id = others[0]["id"]
    else:
        new_others = supabase.table("categories").insert({"name": "Others", "description": "Default"}).execute()
        others_id = new_others.data[0]["id"]
    supabase.table("products").update({"category_id": others_id}).eq("category_id", category_id).execute()
    supabase.table("categories").delete().eq("id", category_id).execute()
    return RedirectResponse("/categories", status_code=303)


# ============ USERS ============

@app.get("/users", response_class=HTMLResponse)
def users_list(request: Request):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can manage users")
    users = supabase.table("shop_users").select("*").order("username").execute().data
    rows = ""
    for u in users:
        role_badge = "🔴 Admin" if u.get("role") == "admin" else "🟢 Cashier"
        status_badge = "✅ Active" if u.get("is_active") else "❌ Inactive"
        actions = f"<a href='/users/edit/{u['id']}' class='btn btn-warn btn-small'>✏️</a>"
        if u["username"] != username:
            actions += f" <a href='/users/delete/{u['id']}' class='btn btn-danger btn-small' onclick=\"return confirm('Delete {u['username']}?')\">🗑️</a>"
        rows += f"""<tr>
            <td><strong>{u['username']}</strong><br><small>{u.get('full_name','')}</small></td>
            <td>{role_badge}</td>
            <td>{status_badge}</td>
            <td>{actions}</td>
        </tr>"""
    body = f"""
    <h2>👥 Users</h2>
    <div class="card">
        <a href="/users/add" class="btn btn-success">➕ Add New User</a>
    </div>
    <div class="card">
        <div class="table-wrap">
        <table>
            <tr><th>User</th><th>Role</th><th>Status</th><th>Actions</th></tr>
            {rows}
        </table>
        </div>
    </div>
    """
    return HTMLResponse(content=page("Users", body, username, info.get("role")))


@app.get("/users/add", response_class=HTMLResponse)
def users_add_form(request: Request):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can manage users")
    body = """
    <h2>➕ Add New User</h2>
    <div class="card">
        <form method="post" action="/users/add">
            <label>Username (login name)</label>
            <input type="text" name="username" required>
            <label>Password</label>
            <input type="text" name="password" required minlength="4">
            <label>Full Name</label>
            <input type="text" name="full_name">
            <label>Role</label>
            <select name="role" required>
                <option value="cashier">Cashier (limited access)</option>
                <option value="admin">Admin (full access)</option>
            </select>
            <button type="submit" class="btn btn-success">Create User</button>
            <a href="/users" class="btn">Cancel</a>
        </form>
    </div>
    """
    return HTMLResponse(content=page("Add User", body, username, info.get("role")))


@app.post("/users/add")
async def users_add(request: Request, username: str = Form(...), password: str = Form(...), full_name: str = Form(""), role: str = Form("cashier")):
    current = get_current_user(request)
    if not current:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(current)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can add users")
    existing = supabase.table("shop_users").select("*").eq("username", username).execute().data
    if not existing:
        supabase.table("shop_users").insert({"username": username, "password": password, "full_name": full_name, "role": role, "is_active": True}).execute()
    return RedirectResponse("/users", status_code=303)


@app.get("/users/edit/{user_id}", response_class=HTMLResponse)
def users_edit_form(request: Request, user_id: int):
    current = get_current_user(request)
    if not current:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(current)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can manage users")
    u = supabase.table("shop_users").select("*").eq("id", user_id).single().execute().data
    body = f"""
    <h2>✏️ Edit User: {u['username']}</h2>
    <div class="card">
        <form method="post" action="/users/edit/{user_id}">
            <label>Full Name</label>
            <input type="text" name="full_name" value="{u.get('full_name','')}">
            <label>Password (leave empty to keep current)</label>
            <input type="text" name="password" placeholder="New password (or leave blank)">
            <label>Role</label>
            <select name="role">
                <option value="cashier" {'selected' if u.get('role')=='cashier' else ''}>Cashier</option>
                <option value="admin" {'selected' if u.get('role')=='admin' else ''}>Admin</option>
            </select>
            <label>Status</label>
            <select name="is_active">
                <option value="true" {'selected' if u.get('is_active') else ''}>Active</option>
                <option value="false" {'selected' if not u.get('is_active') else ''}>Inactive (blocked)</option>
            </select>
            <button type="submit" class="btn btn-success">Save Changes</button>
            <a href="/users" class="btn">Cancel</a>
        </form>
    </div>
    """
    return HTMLResponse(content=page("Edit User", body, current, info.get("role")))


@app.post("/users/edit/{user_id}")
async def users_edit(request: Request, user_id: int, full_name: str = Form(""), password: str = Form(""), role: str = Form("cashier"), is_active: str = Form("true")):
    current = get_current_user(request)
    if not current:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(current)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can edit users")
    data = {"full_name": full_name, "role": role, "is_active": (is_active == "true")}
    if password:
        data["password"] = password
    supabase.table("shop_users").update(data).eq("id", user_id).execute()
    return RedirectResponse("/users", status_code=303)


@app.get("/users/delete/{user_id}")
def users_delete(request: Request, user_id: int):
    current = get_current_user(request)
    if not current:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(current)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can delete users")
    u = supabase.table("shop_users").select("*").eq("id", user_id).single().execute().data
    if u["username"] == current:
        raise HTTPException(400, "You cannot delete your own account")
    supabase.table("shop_users").delete().eq("id", user_id).execute()
    return RedirectResponse("/users", status_code=303)


# ============ REPORTS ============

@app.get("/reports", response_class=HTMLResponse)
def reports(request: Request):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can view reports")
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
    total_credit = 0.0
    for s in sales:
        amount = float(s.get("total", 0))
        total_all += amount
        total_credit += float(s.get("amount_on_credit", 0))
        d = parse_date(s.get("created_at", ""))
        if d:
            if d >= today_start:
                today_total += amount
            if d >= week_start:
                week_total += amount
            if d >= month_start:
                month_total += amount

    expenses = supabase.table("expenses").select("*").execute().data
    month_expenses = 0.0
    for e in expenses:
        try:
            d = datetime.fromisoformat(str(e.get("expense_date", "")).replace("Z", "+00:00")).replace(tzinfo=None)
            if d >= month_start:
                month_expenses += float(e.get("amount", 0))
        except Exception:
            pass

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
    top_rows = "".join(f"<tr><td>{name}</td><td>{data['qty']:.0f}</td><td>GHS {data['revenue']:,.2f}</td><td>GHS {data['profit']:,.2f}</td></tr>" for name, data in top)

    recent_rows = ""
    for s in sales[:20]:
        cust = s.get("customer_name") or "Walk-in"
        recent_rows += f"<tr><td>{s.get('created_at','')[:16]}</td><td>{s.get('invoice_no','')}</td><td>{cust}</td><td>GHS {float(s.get('total',0)):,.2f}</td><td>{s.get('cashier_name') or s.get('user_id','')}</td><td><a href='/receipt/{s['id']}' class='btn btn-small'>View</a></td></tr>"

    net_profit = total_all - month_expenses

    body = f"""
    <h2>Reports</h2>

    <div class="card">
        <h3>📥 Export Data to Excel</h3>
        <a href="/export/sales" class="btn btn-success">📥 All Sales</a>
        <a href="/export/products" class="btn btn-success">📥 All Materials</a>
        <a href="/export/stock" class="btn btn-success">📥 Stock Movements</a>
        <a href="/export/customers" class="btn btn-success">📥 Customers</a>
        <a href="/export/purchases" class="btn btn-success">📥 Purchases</a>
    </div>

    <div class="grid">
        <div class="card stat"><div class="num">GHS {today_total:,.2f}</div><div class="label">Today</div></div>
        <div class="card stat"><div class="num">GHS {week_total:,.2f}</div><div class="label">Last 7 days</div></div>
        <div class="card stat"><div class="num">GHS {month_total:,.2f}</div><div class="label">Last 30 days</div></div>
        <div class="card stat"><div class="num">GHS {total_all:,.2f}</div><div class="label">All time</div></div>
    </div>

    <div class="grid">
        <div class="card stat"><div class="num" style="color:#dc2626;">GHS {total_credit:,.2f}</div><div class="label">Total on Credit</div></div>
        <div class="card stat"><div class="num" style="color:#dc2626;">GHS {month_expenses:,.2f}</div><div class="label">Expenses (30 days)</div></div>
    </div>

    <div class="card {'profit-box' if net_profit >= 0 else 'loss-box'}">
        <h3 style="margin:0;">{'💰 Net Profit' if net_profit >= 0 else '⚠️ Net Loss'} (all time)</h3>
        <div class="big-num" style="color:{'#16a34a' if net_profit >= 0 else '#dc2626'};">GHS {net_profit:,.2f}</div>
        <p style="text-align:center;color:#666;">Sales − Expenses (approximate)</p>
    </div>

    <div class="card">
        <h3>🏆 Top Selling Materials</h3>
        <div class="table-wrap">
        <table>
            <tr><th>Material</th><th>Qty Sold</th><th>Revenue</th><th>Profit</th></tr>
            {top_rows if top_rows else "<tr><td colspan='4'>No sales yet.</td></tr>"}
        </table>
        </div>
    </div>

    <div class="card">
        <h3>🧾 Recent Sales (last 20)</h3>
        <div class="table-wrap">
        <table>
            <tr><th>Date</th><th>Invoice</th><th>Customer</th><th>Total</th><th>Cashier</th><th></th></tr>
            {recent_rows if recent_rows else "<tr><td colspan='6'>No sales yet.</td></tr>"}
        </table>
        </div>
    </div>
    """
    return HTMLResponse(content=page("Reports", body, username, info.get("role")))


# ============ EXCEL EXPORTS ============

def style_header(ws, headers):
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")
        cell.alignment = Alignment(horizontal="center")


@app.get("/export/sales")
def export_sales(request: Request):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can export data")
    sales = supabase.table("sales").select("*").order("created_at", desc=True).execute().data
    wb = Workbook()
    ws = wb.active
    ws.title = "Sales"
    headers = ["Date", "Invoice", "Customer", "Subtotal", "Discount", "Total", "Paid", "On Credit", "Payment", "Cashier"]
    style_header(ws, headers)
    for s in sales:
        ws.append([
            s.get("created_at", "")[:19].replace("T", " "),
            s.get("invoice_no", ""),
            s.get("customer_name") or "Walk-in",
            float(s.get("subtotal", 0)),
            float(s.get("discount", 0)),
            float(s.get("total", 0)),
            float(s.get("amount_paid_now", s.get("total", 0))),
            float(s.get("amount_on_credit", 0)),
            s.get("payment_method", ""),
            s.get("cashier_name") or s.get("user_id", ""),
        ])
    widths = [20, 22, 20, 12, 12, 12, 12, 12, 15, 15]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i)].width = w
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=OBOLO_sales_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"}
    )


@app.get("/export/products")
def export_products(request: Request):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can export data")
    products = supabase.table("products").select("*").eq("is_active", True).order("name").execute().data
    wb = Workbook()
    ws = wb.active
    ws.title = "Materials"
    headers = ["Name", "SKU", "Unit", "Stock", "Cost Price", "Selling Price", "Reorder Level", "Location"]
    style_header(ws, headers)
    for p in products:
        ws.append([
            p.get("name", ""),
            p.get("sku", ""),
            p.get("unit", ""),
            float(p.get("quantity_in_stock", 0)),
            float(p.get("cost_price", 0)),
            float(p.get("selling_price", 0)),
            float(p.get("reorder_level", 0)),
            p.get("location") or "",
        ])
    widths = [30, 15, 10, 10, 12, 14, 14, 15]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i)].width = w
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=OBOLO_materials_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"}
    )


@app.get("/export/stock")
def export_stock(request: Request):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can export data")
    movements = supabase.table("stock_movements").select("*").order("created_at", desc=True).limit(5000).execute().data
    wb = Workbook()
    ws = wb.active
    ws.title = "Stock Movements"
    headers = ["Date", "Type", "Quantity", "Note"]
    style_header(ws, headers)
    for m in movements:
        ws.append([
            m.get("created_at", "")[:19].replace("T", " "),
            m.get("movement_type", ""),
            float(m.get("quantity", 0)),
            m.get("note", ""),
        ])
    widths = [20, 12, 12, 50]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i)].width = w
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=OBOLO_stock_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"}
    )


@app.get("/export/customers")
def export_customers(request: Request):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can export data")
    customers = supabase.table("customers").select("*").eq("is_active", True).order("name").execute().data
    wb = Workbook()
    ws = wb.active
    ws.title = "Customers"
    headers = ["Name", "Phone", "Address", "Balance Owed", "Notes"]
    style_header(ws, headers)
    for c in customers:
        ws.append([
            c.get("name", ""),
            c.get("phone", "") or "",
            c.get("address", "") or "",
            float(c.get("balance", 0)),
            c.get("notes", "") or "",
        ])
    widths = [25, 15, 25, 15, 30]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i)].width = w
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=OBOLO_customers_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"}
    )


@app.get("/export/purchases")
def export_purchases(request: Request):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can export data")
    purchases = supabase.table("purchase_orders").select("*").order("created_at", desc=True).execute().data
    wb = Workbook()
    ws = wb.active
    ws.title = "Purchases"
    headers = ["Date", "PO Number", "Supplier", "Total", "Paid", "Owed", "Payment Method"]
    style_header(ws, headers)
    for po in purchases:
        ws.append([
            po.get("created_at", "")[:19].replace("T", " "),
            po.get("po_number", ""),
            po.get("supplier_name", ""),
            float(po.get("total", 0)),
            float(po.get("amount_paid", 0)),
            float(po.get("amount_owed", 0)),
            po.get("payment_method", ""),
        ])
    widths = [20, 22, 25, 12, 12, 12, 18]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i)].width = w
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=OBOLO_purchases_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"}
    )


@app.get("/health")
def health():
    return {"status": "ok"}