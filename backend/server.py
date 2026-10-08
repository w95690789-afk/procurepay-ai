import os
import io
import json
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any, List

from .config import settings
from .orchestrator import orchestrator
from .procurement_agent import procurement_agent
from .orphan_classifier import orphan_classifier, MASTER_CATALOG, CATEGORIES_MASTER
from .accounting_engine import accounting_engine, CHART_OF_ACCOUNTS, COST_CENTERS, BUSINESS_UNITS
from .sharepoint_emulator import sharepoint_emulator
from .paypal_service import paypal_service

app = FastAPI(
    title="ProcurePay AI - Enterprise Autonomous Procurement, Accounting & PayPal Settlement",
    description="Cognitive Multi-Channel Ingestion, SharePoint Sync, Orphan Item Classification, Accounting Journal Entries, SAT 3-Way Audit & Instant PayPal Settlement",
    version="2.5.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

root_project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_dir = os.path.join(root_project_dir, "frontend")
static_dir = os.path.join(frontend_dir, "static")

if not os.path.exists(static_dir):
    try:
        os.makedirs(static_dir, exist_ok=True)
    except Exception:
        static_dir = "/tmp/static"
        os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    candidates = [
        os.path.join(frontend_dir, "index.html"),
        os.path.join(root_project_dir, "frontend", "index.html"),
        os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html"),
        os.path.join("/var/task", "frontend", "index.html"),
        os.path.join(os.getcwd(), "frontend", "index.html")
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as f:
                return f.read()
    return "<h1>ProcurePay AI Online</h1>"

@app.get("/favicon.ico")
async def favicon():
    return HTMLResponse(content="", status_code=204)

@app.get("/api/health")
async def health_check():
    try:
        token = paypal_service.get_access_token()
        paypal_status = "CONNECTED"
    except Exception as e:
        paypal_status = f"ERROR: {str(e)}"

    return {
        "status": "healthy",
        "paypal_environment": settings.PAYPAL_ENV,
        "paypal_connectivity": paypal_status,
        "groq_model": procurement_agent.groq_model,
        "auto_approval_threshold_usd": settings.AUTO_APPROVAL_THRESHOLD_USD,
        "sharepoint_status": "ONLINE_CONNECTED",
        "accounting_engine": "ACTIVE_NIF_SAT"
    }

# --- SharePoint Endpoints ---

@app.get("/api/sharepoint/library")
async def get_sharepoint_library():
    """Returns the current document library status of the simulated SharePoint."""
    return JSONResponse(content=sharepoint_emulator.list_library_contents())

@app.post("/api/sharepoint/process-inbox")
async def process_sharepoint_inbox():
    """Reads all files in SharePoint /Buzon_Entrada_Requisiciones and runs the full pipeline."""
    inbox_dir = os.path.join(sharepoint_emulator.base_dir, sharepoint_emulator.folders["buzon_entrada"])
    files = [f for f in os.listdir(inbox_dir) if os.path.isfile(os.path.join(inbox_dir, f))]
    
    if not files:
        # Re-seed if empty
        sharepoint_emulator._seed_sample_documents()
        files = [f for f in os.listdir(inbox_dir) if os.path.isfile(os.path.join(inbox_dir, f))]

    target_file = os.path.join(inbox_dir, files[0])
    
    # Process the file
    if target_file.endswith('.json'):
        with open(target_file, 'r', encoding='utf-8') as f:
            req_data = json.load(f)
        result = orchestrator.process_end_to_end_procurement(req_data)
    else:
        result = orchestrator.process_end_to_end_procurement(target_file)

    # Move processed file to en_cotizacion or keep history
    sharepoint_emulator.move_document_stage(files[0], "buzon_entrada", "en_cotizacion")
    return JSONResponse(content=result)

# --- Orphan Product Classifier Endpoints ---

@app.post("/api/classify-orphan")
async def classify_orphan_item(payload: Dict[str, Any] = Body(...)):
    """Direct classification of an uncatalogued/orphan item."""
    desc = payload.get("description", "")
    sku = payload.get("sku", None)
    if not desc:
        raise HTTPException(status_code=400, detail="Descripción requerida.")
    
    result = orphan_classifier.classify_item(desc, sku)
    return JSONResponse(content=result)

@app.get("/api/master-catalog")
async def get_master_catalog():
    """Returns master catalog benchmarks and categories."""
    return JSONResponse(content={
        "master_catalog": MASTER_CATALOG,
        "categories": CATEGORIES_MASTER
    })

# --- Accounting Engine Endpoints ---

@app.get("/api/accounting/catalogo")
async def get_accounting_catalogs():
    """Returns Chart of Accounts, Cost Centers, Business Units and DMS Matrix."""
    return JSONResponse(content={
        "chart_of_accounts": CHART_OF_ACCOUNTS,
        "cost_centers": COST_CENTERS,
        "business_units": BUSINESS_UNITS
    })

@app.post("/api/accounting/classify")
async def classify_accounting_item(payload: Dict[str, Any] = Body(...)):
    """Suggests account code, cost center, DMS cross-reference, and tax rule."""
    desc = payload.get("description", "")
    cat = payload.get("category", "Refacciones Mecánicas")
    bu = payload.get("business_unit_id", "UN-MX-MTY")
    dept = payload.get("department", "Operaciones")
    
    classification = accounting_engine.determine_accounting_classification(
        item_description=desc,
        category=cat,
        department=dept,
        business_unit_id=bu
    )
    return JSONResponse(content=classification)

# --- Procurement & Multi-Channel Pipeline Endpoints ---

@app.post("/api/ingest-unstructured")
async def ingest_unstructured(payload: Dict[str, Any] = Body(...)):
    """Ingest unstructured email body or WhatsApp message, extract with Groq and run pipeline."""
    try:
        raw_text = payload.get("raw_text", "")
        source_type = payload.get("source_type", "email")
        if not raw_text:
            raise HTTPException(status_code=400, detail="El campo raw_text es requerido.")

        requisition = procurement_agent.parse_unstructured_text(raw_text, source_type=source_type)
        result = orchestrator.process_end_to_end_procurement(requisition)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ingest-xml")
async def ingest_xml(payload: Dict[str, Any] = Body(...)):
    """Ingest and audit raw Mexican SAT CFDI 4.0 XML invoice."""
    try:
        xml_text = payload.get("xml_content", "")
        if not xml_text:
            raise HTTPException(status_code=400, detail="El campo xml_content es requerido.")

        cfdi_data = procurement_agent.parse_cfdi_xml(xml_text)
        
        sample_df = pd.DataFrame([
            {"SKU": it['sku'], "Descripcion": it['description'], "Cantidad": it['quantity'], "Precio_Estimado": it['unit_price']}
            for it in cfdi_data['items']
        ])
        result = orchestrator.process_end_to_end_procurement(sample_df, incoming_invoice=cfdi_data)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload-requisition")
async def upload_requisition(file: UploadFile = File(...)):
    """Upload and process Excel (.xlsx, .xls, FMA-017), CSV or JSON requisition file."""
    try:
        contents = await file.read()
        filename = file.filename or "requisition.xlsx"
        if os.environ.get("VERCEL") or not os.access(root_project_dir, os.W_OK):
            temp_dir = "/tmp/temp_uploads"
        else:
            temp_dir = os.path.join(root_project_dir, "temp_uploads")
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, filename)

        with open(file_path, "wb") as f:
            f.write(contents)

        # Stage to SharePoint inbox
        sharepoint_emulator.stage_file_to_folder(file_path, "buzon_entrada", filename)

        result = orchestrator.process_end_to_end_procurement(file_path)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/presets/{preset_id}")
async def run_preset(preset_id: str):
    """Executes pre-configured enterprise demonstration scenarios."""
    if preset_id == "sharepoint-fma017":
        req = {
            "folio": "FMA017-FOL-9042",
            "department": "Mantenimiento Industrial y Automatización",
            "requested_by": "Ing. Carlos Mendoza (Jefe de Planta)",
            "currency": "USD",
            "items": [
                {"sku": "SKU-HUERF-11", "description": "Guantes de nitrilo calibre 6mil caja 100", "quantity": 4, "unit": "CAJA", "estimated_unit_price": 40.0},
                {"sku": "ELEC-SEN-002", "description": "Sensor inductivo M12 PNP NO alcance 4mm", "quantity": 2, "unit": "PZA", "estimated_unit_price": 65.0},
                {"sku": "SKU-HUERF-12", "description": "Desengrasante biodegradable tambor 20L", "quantity": 1, "unit": "TAMBOR", "estimated_unit_price": 85.0}
            ]
        }
        return JSONResponse(content=orchestrator.process_end_to_end_procurement(req))

    elif preset_id == "fletes-retencion":
        req = {
            "folio": "REQ-LOG-7721",
            "department": "Logística y Distribución",
            "requested_by": "Lic. Javier Ochoa",
            "currency": "USD",
            "items": [
                {"sku": "LOG-FLE-01", "description": "Servicio de flete y traslado de 5 unidades en madrina planta Hermosillo", "quantity": 1, "unit": "SRV", "estimated_unit_price": 320.0}
            ]
        }
        return JSONResponse(content=orchestrator.process_end_to_end_procurement(req))

    elif preset_id == "high-value-approval":
        req = {
            "folio": "REQ-ROBOT-001",
            "department": "Línea Robótica Ensamblado",
            "requested_by": "Ing. Laura Treviño - Dir. Operaciones",
            "currency": "USD",
            "items": [
                {"sku": "ELEC-SEN-001", "description": "Sensor Fotoeléctrico Omron E3Z-D61 NPN", "quantity": 8, "unit": "PZA", "estimated_unit_price": 145.0},
                {"sku": "ROB-SERVO-01", "description": "Servomotor Fanuc 2.5kW AC Servo con Encoder", "quantity": 1, "unit": "PZA", "estimated_unit_price": 1200.0}
            ]
        }
        return JSONResponse(content=orchestrator.process_end_to_end_procurement(req))

    elif preset_id == "sat-discrepancy-block":
        req = {
            "folio": "REQ-SAFE-999",
            "department": "Seguridad e Higiene",
            "requested_by": "Ing. Daniel Cruz",
            "currency": "USD",
            "items": [
                {"sku": "SEG-CAS-202", "description": "Casco de Seguridad Industrial Clase E Dielectrico", "quantity": 5, "unit": "PZA", "estimated_unit_price": 22.0}
            ]
        }
        # Tampered invoice with EFOS / overcharge
        tampered_invoice = {
            "invoice_number": "FAC-FRAUD-999",
            "vendor_name": "Suministros Fantasma S.A. de C.V. (EFOS SAT 69-B)",
            "vendor_rfc": "FAS190101999",
            "currency": "USD",
            "items": [
                {"sku": "SEG-CAS-202", "description": "Casco de Seguridad", "quantity": 5, "unit_price": 95.0, "subtotal": 475.0}
            ],
            "subtotal": 475.0,
            "tax": 76.0,
            "grand_total": 551.0
        }
        return JSONResponse(content=orchestrator.process_end_to_end_procurement(req, incoming_invoice=tampered_invoice))

    raise HTTPException(status_code=404, detail="Preset no encontrado")
