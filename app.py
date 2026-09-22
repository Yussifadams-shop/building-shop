import os
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Missing SUPABASE_URL or SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="Building Materials Shop")


def page(title, body):
    return f"""<!DOCTYPE html>
<html>
<head>
<title>{title} - Building Shop</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
* {{ box-sizing: border-box; }}
body {{ font-family: Arial, sans-serif; margin: 0; background: #f4f4f7; color: #222; }}
.header {{ background: #1e40af; color: white; padding: 15px 20px; }}
.header h1 {{ margin: 0; font-size: 20px; display: inline-block; }}
.header a {{ color: white; text-decoration: none; margin-left: 15px; font-size: 14px; }}
.container {{ max-width: 1000px; margin: 20px auto; padding: 0 15px; }}
.card {{ background: white; border-radius: 8px; padding: 20px; margin-bottom: 15px; }}
h2 {{ color: #1e40af; margin-top: 0; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #eee; }}
th {{ background: #f9fafb; }}
input, select {{ width: 100%; padding: 10px; margin: 5px 0 15px; border: 1px solid #ddd; border-radius: 5px; }}
button, .btn {{ background: #1e40af; color: white; padding: 12px 20px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; }}
.btn-success {{ background: #16a34a; }}
.low {{ color: #dc2626; font-weight: bold; }}
.ok {{ color: #16a34a; font-weight: bold; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
.stat {{ text-align: center; padding: 15px; }}
.stat .num {{ font-size: 28px; font-weight: bold; color: #1e40af; }}
.stat .label {{ color: #666; font-size: 13px; }}
</style>
</head>
<body>
<div class="header">
<h1>Building Shop</h1>
<a href="/">Home</a>
<a href="/products">Materials</a>
<a href="/add">Add</a>
<a href="/categories">Categories</a>
</div>
<div class="container">{body}</div>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def home():
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
    </div>
    """
    return page("Dashboard", body)


@app.get("/products", response_class=HTMLResponse)
def products_list(search: str = ""):
    query = supabase.table("products").select("*").eq("is_active", True)
    if search:
        query = query.ilike("name", f"%{search}%")
    products = query.order("name").execute().data
    rows = ""
    for p in products:
        qty = float(p.get("quantity_in_stock", 0))
        reorder = float(p.get("reorder_level", 0))
        status = "low" if qty <= reorder else "ok"
        rows += f"<tr><td><strong>{p['name']}</strong><br><small>{p.get('sku','')}</small></td><td>{p.get('unit','')}</td><td class='{status}'>{qty}</td><td>GHS {float(p['selling_price']):,.2f}</td><td><a href='/sell/{p['id']}' class='btn btn-success'>Sell</a></td></tr>"
    body = f"""
    <h2>All Materials</h2>
    <div class="card">
        <form method="get"><input type="text" name="search" placeholder="Search..." value="{search}"><button>Search</button></form>
    </div>
    <div class="card"><table>
        <tr><th>Material</th><th>Unit</th><th>Stock</th><th>Price</th><th></th></tr>
        {rows if rows else "<tr><td colspan='5'>No materials. <a href='/add'>Add one</a>.</td></tr>"}
    </table></div>
    """
    return page("Materials", body)


@app.get("/add", response_class=HTMLResponse)
def add_form():
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
    return page("Add", body)


@app.post("/add")
async def add_product(name: str = Form(...), sku: str = Form(...), category_id: str = Form(...), unit: str = Form(...), location: str = Form(""), cost_price: float = Form(...), selling_price: float = Form(...), quantity_in_stock: float = Form(...), reorder_level: float = Form(10)):
    data = {"name": name, "sku": sku, "category_id": int(category_id), "unit": unit, "location": location or None, "cost_price": cost_price, "selling_price": selling_price, "quantity_in_stock": quantity_in_stock, "reorder_level": reorder_level, "is_active": True}
    result = supabase.table("products").insert(data).execute()
    if result.data and quantity_in_stock > 0:
        supabase.table("stock_movements").insert({"product_id": result.data[0]["id"], "movement_type": "IN", "quantity": quantity_in_stock, "unit_cost": cost_price, "note": "Opening stock"}).execute()
    return RedirectResponse("/products", status_code=303)


@app.get("/sell/{product_id}", response_class=HTMLResponse)
def sell_form(product_id: int):
    p = supabase.table("products").select("*").eq("id", product_id).single().execute().data
    body = f"""
    <h2>Sell: {p['name']}</h2>
    <div class="card">
        <p>Available: <strong>{p['quantity_in_stock']} {p['unit']}</strong></p>
        <p>Price: <strong>GHS {float(p['selling_price']):,.2f}</strong></p>
        <form method="post" action="/sell/{product_id}">
            <label>Quantity</label><input type="number" step="0.01" name="quantity" required min="0.01" max="{p['quantity_in_stock']}">
            <button type="submit" class="btn-success">Sell</button>
            <a href="/products" class="btn">Cancel</a>
        </form>
    </div>
    """
    return page("Sell", body)


@app.post("/sell/{product_id}")
async def do_sell(product_id: int, quantity: float = Form(...)):
    p = supabase.table("products").select("*").eq("id", product_id).single().execute().data
    if float(p["quantity_in_stock"]) < quantity:
        raise HTTPException(400, "Not enough stock")
    new_qty = float(p["quantity_in_stock"]) - quantity
    supabase.table("products").update({"quantity_in_stock": new_qty}).eq("id", product_id).execute()
    supabase.table("stock_movements").insert({"product_id": product_id, "movement_type": "OUT", "quantity": quantity, "note": f"Sale"}).execute()
    body = f"""
    <div class="card">
        <h2>Sale Complete</h2>
        <p>{quantity} {p['unit']} of {p['name']} sold for GHS {quantity * float(p['selling_price']):,.2f}</p>
        <p>Remaining: {new_qty} {p['unit']}</p>
        <a href="/products" class="btn">Back</a>
    </div>
    """
    return page("Done", body)


@app.get("/categories", response_class=HTMLResponse)
def categories_list():
    cats = supabase.table("categories").select("*").order("name").execute().data
    rows = "".join(f"<tr><td>{c['name']}</td><td>{c.get('description','')}</td></tr>" for c in cats)
    body = f"<h2>Categories</h2><div class='card'><table><tr><th>Category</th><th>Description</th></tr>{rows}</table></div>"
    return page("Categories", body)


@app.get("/health")
def health():
    return {"status": "ok"}