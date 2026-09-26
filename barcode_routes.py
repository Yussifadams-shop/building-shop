from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from auth import get_current_user, get_user_info
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter()


@router.get("/scan", response_class=HTMLResponse)
def scan_page(request: Request, code: str = ""):
    from app import page

    username = get_current_user(request)
    if not username:
        return RedirectResponse("/login", status_code=303)
    info = get_user_info(username)
    role = info.get("role", "cashier") if info else "cashier"

    # Lookup result
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
                <p style="margin:0;">❌ No material found with code: <strong>{code}</strong></p>
                <p style="margin:10px 0 0 0;font-size:14px;">Check that this code matches a product's <strong>SKU</strong> or <strong>Barcode</strong> field.</p>
            </div>
            """

    body = f"""
    <h2>📷 Barcode Scanner</h2>

    <div class="card">
        <p style="text-align:center;color:#666;">Hold the barcode steady inside the yellow box.</p>
        <div id="reader" style="width:100%;max-width:500px;margin:0 auto;"></div>
        <div id="status" style="text-align:center;margin-top:10px;padding:10px;background:#f9fafb;border-radius:5px;color:#666;">
            ⏳ Starting camera...
        </div>
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
            <input type="text" name="code" placeholder="Enter SKU or barcode" style="flex:1;min-width:200px;margin:0;">
            <button type="submit" class="btn">Search</button>
        </form>
    </div>

    <div class="card">
        <h3>💡 Tips for Better Scanning</h3>
        <ul>
            <li><strong>Lighting:</strong> Use in a well-lit area (natural light is best)</li>
            <li><strong>Distance:</strong> Hold phone 10–15 cm from the barcode</li>
            <li><strong>Angle:</strong> Keep phone parallel to the label (not tilted)</li>
            <li><strong>Steady:</strong> Hold still for 2 seconds — don't rush</li>
            <li><strong>Focus:</strong> Tap the screen where the barcode is to help autofocus</li>
            <li><strong>Clean lens:</strong> Wipe camera lens with soft cloth</li>
        </ul>
    </div>

    <div class="card">
        <h3>✅ What Barcodes Work</h3>
        <p style="font-size:14px;">This scanner supports:</p>
        <ul style="font-size:14px;">
            <li>CODE 128 (used by our printed labels)</li>
            <li>Code 39</li>
            <li>EAN-13, EAN-8 (product barcodes)</li>
            <li>UPC-A, UPC-E</li>
            <li>ITF (Interleaved 2 of 5)</li>
            <li>QR Codes</li>
        </ul>
    </div>

    <script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
    <script>
    var html5QrCode = null;
    var isScanning = false;

    function setStatus(msg, color) {{
        var el = document.getElementById('status');
        el.innerText = msg;
        el.style.color = color || '#666';
    }}

    function startScanner() {{
        if (isScanning) return;
        setStatus('⏳ Requesting camera...', '#666');

        if (!html5QrCode) {{
            try {{
                html5QrCode = new Html5Qrcode("reader", {{ verbose: false }});
            }} catch (e) {{
                setStatus('❌ Failed to initialize scanner: ' + e.message, '#dc2626');
                return;
            }}
        }}

        // Try environment camera (back camera), then fallback
        html5QrCode.start(
            {{ facingMode: "environment" }},
            {{
                fps: 15,
                qrbox: function(viewfinderWidth, viewfinderHeight) {{
                    var minEdge = Math.min(viewfinderWidth, viewfinderHeight);
                    var size = Math.floor(minEdge * 0.75);
                    return {{ width: size, height: Math.floor(size * 0.6) }};
                }},
                aspectRatio: 1.5,
                disableFlip: false
            }},
            function onScanSuccess(decodedText, decodedResult) {{
                setStatus('✅ Found: ' + decodedText, '#16a34a');
                if (navigator.vibrate) navigator.vibrate(100);
                stopScanner();
                setTimeout(function() {{
                    window.location.href = '/scan?code=' + encodeURIComponent(decodedText);
                }}, 400);
            }},
            function onScanFailure(error) {{
                // Quietly ignore frame misses (happens constantly when no barcode in view)
            }}
        ).then(function() {{
            isScanning = true;
            setStatus('🔍 Scanning... point at a barcode', '#1e40af');
        }}).catch(function(err) {{
            var msg = String(err);
            if (msg.indexOf('NotAllowed') >= 0) {{
                setStatus('❌ Camera permission denied. Please allow camera access.', '#dc2626');
            }} else if (msg.indexOf('NotFound') >= 0) {{
                setStatus('❌ No camera found on this device.', '#dc2626');
            }} else {{
                setStatus('❌ Camera error: ' + msg, '#dc2626');
            }}
        }});
    }}

    function stopScanner() {{
        if (html5QrCode && isScanning) {{
            html5QrCode.stop().then(function() {{
                isScanning = false;
                setStatus('⏸️ Camera stopped', '#666');
            }}).catch(function(err) {{
                console.log('Stop error:', err);
            }});
        }}
    }}

    window.addEventListener('load', function() {{
        setTimeout(startScanner, 800);
    }});

    window.addEventListener('beforeunload', function() {{
        stopScanner();
    }});
    </script>
    """
    return page("Scan", body, username, role)  

@router.get("/barcodes", response_class=HTMLResponse)
def barcodes_page(request: Request):
    from app import page

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
                svg.outerHTML = '<div style="font-size:11px;color:#dc2626;">Barcode error: ' + code + '</div>';
            }}
        }});
    }});
    </script>
    """
    return page("Barcodes", body, username, info.get("role"))