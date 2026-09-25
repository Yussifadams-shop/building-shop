from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from auth import get_current_user, get_user_info, log_activity
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter()


def page(title, body, user=None, role=None, extra_head=""):
    """Shared page wrapper — imports the parent page function dynamically."""
    from app import page as parent_page
    return parent_page(title, body, user, role, extra_head)


@router.get("/scan", response_class=HTMLResponse)
def scan_page(request: Request, code: str = ""):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    role = info.get("role", "cashier") if info else "cashier"

    result_html = ""
    if code:
        products = supabase.table("products").select("*").eq("is_active", True).eq("barcode", code).execute().data
        if not products:
            products = supabase.table("products").select("*").eq("is_active", True).eq("sku", code).execute().data
        if products:
            p = products[0]
            qty_available = float(p.get("quantity_in_stock", 0))
            result_html = f"""
            <div class="scan-result scan-success">
                <p style="margin:0 0 10px 0;"><strong>✅ Found: {p['name']}</strong></p>
                <p style="margin:0 0 10px 0;">Price: GHS {float(p['selling_price']):,.2f} | Stock: {qty_available} {p.get('unit','')}</p>
                <form method="post" action="/cart/add" style="display:flex;gap:10px;align-items:center;justify-content:center;flex-wrap:wrap;">
                    <input type="hidden" name="product_id" value="{p['id']}">
                    <input type="number" step="0.01" name="quantity" value="1" min="0.01" max="{qty_available}" style="width:100px;margin:0;padding:8px;">
                    <button type="submit" class="btn btn-success">Add to Cart</button>
                </form>
            </div>
            """
        else:
            result_html = f"""
            <div class="scan-result scan-error">
                <p style="margin:0;">❌ No material found with barcode: <strong>{code}</strong></p>
            </div>
            """

    body = f"""
    <h2>📷 Barcode Scanner</h2>

    <div class="card">
        <p style="text-align:center;color:#666;">Point your camera at a barcode to scan. Works best in bright light.</p>
        <div id="reader"></div>
        <div id="status" style="text-align:center;margin-top:10px;color:#666;">Starting camera...</div>
        <div style="text-align:center;margin-top:15px;">
            <button onclick="startScanner()" class="btn btn-success">▶️ Start Camera</button>
            <button onclick="stopScanner()" class="btn btn-danger">⏹️ Stop Camera</button>
            <a href="/cart" class="btn">🛒 View Cart</a>
        </div>
    </div>

    {result_html}

    <div class="card">
        <h3>🖊️ Manual Entry</h3>
        <p style="color:#666;font-size:14px;">If the camera can't read the barcode, type it here:</p>
        <form method="get" action="/scan" style="display:flex;gap:10px;flex-wrap:wrap;">
            <input type="text" name="code" placeholder="Enter barcode or SKU" style="flex:1;min-width:200px;margin:0;">
            <button type="submit" class="btn">Search</button>
        </form>
    </div>

    <div class="card">
        <h3>ℹ️ How It Works</h3>
        <ul>
            <li>Point your phone camera at a barcode</li>
            <li>The app finds the material and shows it below</li>
            <li>Click <strong>Add to Cart</strong> to add it to the current sale</li>
            <li>Keep scanning more items, then go to Cart to checkout</li>
            <li>Or type the barcode/SKU manually if needed</li>
        </ul>
    </div>

    <script src="https://unpkg.com/html5-qrcode" type="text/javascript"></script>
    <script>
    var html5QrCode = null;
    var scanning = false;

    function startScanner() {{
        if (scanning) return;
        document.getElementById('status').innerText = 'Starting camera...';

        if (!html5QrCode) {{
            html5QrCode = new Html5Qrcode("reader");
        }}

        html5QrCode.start(
            {{ facingMode: "environment" }},
            {{
                fps: 10,
                qrbox: {{ width: 250, height: 150 }},
                formatsToSupport: [
                    Html5QrcodeSupportedFormats.EAN_13,
                    Html5QrcodeSupportedFormats.EAN_8,
                    Html5QrcodeSupportedFormats.UPC_A,
                    Html5QrcodeSupportedFormats.UPC_E,
                    Html5QrcodeSupportedFormats.CODE_128,
                    Html5QrcodeSupportedFormats.CODE_39,
                    Html5QrcodeSupportedFormats.QR_CODE,
                    Html5QrcodeSupportedFormats.ITF
                ]
            }},
            function(decodedText) {{
                document.getElementById('status').innerText = 'Found: ' + decodedText;
                stopScanner();
                window.location.href = '/scan?code=' + encodeURIComponent(decodedText);
            }},
            function(errorMessage) {{ }}
        ).then(function() {{
            scanning = true;
            document.getElementById('status').innerText = 'Scanning... hold barcode steady';
        }}).catch(function(err) {{
            document.getElementById('status').innerText = '❌ Camera error: ' + err;
        }});
    }}

    function stopScanner() {{
        if (html5QrCode && scanning) {{
            html5QrCode.stop().then(function() {{
                scanning = false;
                document.getElementById('status').innerText = 'Camera stopped';
            }}).catch(function(err) {{ console.log('Stop error:', err); }});
        }}
    }}

    window.addEventListener('load', function() {{
        setTimeout(startScanner, 500);
    }});

    window.addEventListener('beforeunload', function() {{
        stopScanner();
    }});
    </script>
    """
    return page("Scan", body, username, role)


@router.get("/barcodes", response_class=HTMLResponse)
def barcodes_page(request: Request):
    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    if not info or info.get("role") != "admin":
        raise HTTPException(403, "Only admins can print barcodes")

    products = supabase.table("products").select("*").eq("is_active", True).order("name").execute().data

    labels = ""
    for p in products:
        code = p.get("barcode") or p.get("sku") or f"P{p['id']}"
        price = float(p.get("selling_price", 0))
        labels += f"""
        <div class="barcode-label">
            <div class="name">{p['name']}</div>
            <div class="price">GHS {price:,.2f} / {p.get('unit','')}</div>
            <svg class="barcode-svg" data-code="{code}"></svg>
            <div style="font-size:11px;margin-top:3px;">{code}</div>
        </div>
        """

    body = f"""
    <h2>🏷️ Barcode Labels</h2>

    <div class="card no-print">
        <p><strong>{len(products)}</strong> materials. Each will get a barcode label using its SKU (or barcode if set).</p>
        <button onclick="window.print()" class="btn btn-success">🖨️ Print All Labels</button>
        <a href="/products" class="btn">← Back to Materials</a>
    </div>

    <div class="card">
        {labels if labels else "<p>No materials to print labels for.</p>"}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.6/dist/JsBarcode.all.min.js"></script>
    <script>
    window.addEventListener('load', function() {{
        document.querySelectorAll('.barcode-svg').forEach(function(svg) {{
            var code = svg.getAttribute('data-code');
            try {{
                JsBarcode(svg, code, {{
                    format: 'CODE128',
                    width: 1.5,
                    height: 50,
                    displayValue: false,
                    margin: 0
                }});
            }} catch (e) {{
                svg.outerHTML = '<div style="font-size:11px;color:#dc2626;">Barcode error</div>';
            }}
        }});
    }});
    </script>
    """
    return page("Barcodes", body, username, info.get("role"))