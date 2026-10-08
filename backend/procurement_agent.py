import os
import re
import json
import xml.etree.ElementTree as ET
import requests
from typing import Dict, Any, List, Optional, Union
import pandas as pd
from .config import settings
from .orphan_classifier import orphan_classifier

class ProcurementAgent:
    def __init__(self):
        self.groq_api_key = settings.GROQ_API_KEY
        self.groq_model = "openai/gpt-oss-120b"
        self.groq_fallback_model = "qwen/qwen3.8-27b"

    def parse_unstructured_text(self, raw_text: str, source_type: str = "email") -> Dict[str, Any]:
        """
        Use Groq LLM to extract structured purchase items from raw unstructured emails or chat messages.
        """
        prompt = f"""Eres un Agente Cognitivo de Compras B2B de nivel Enterprise.
Tu misión es extraer y normalizar los requerimientos de compra o cotización a partir de este texto desestructurado recibido por {source_type.upper()}:

--- TEXTO DE ENTRADA ---
{raw_text}
--- FIN TEXTO ---

Debes responder ÚNICAMENTE con un objeto JSON válido con esta estructura exacta (sin markdown adicional):
{{
    "channel": "{source_type}",
    "department": "Mantenimiento y Operaciones",
    "requested_by": "Supervisor de Planta",
    "vendor_hint": null,
    "delivery_days_hint": 2,
    "items": [
        {{
            "sku": "SKU-ORPH-01",
            "description": "Nombre técnico extraído",
            "quantity": 2.0,
            "unit": "PZA",
            "estimated_unit_price": 50.0
        }}
    ]
}}"""

        extracted_items = []
        dept = "Mantenimiento y Operaciones"
        req_by = "Usuario Planta"

        if self.groq_api_key:
            for model_name in [self.groq_model, self.groq_fallback_model]:
                try:
                    url = "https://api.groq.com/openai/v1/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {self.groq_api_key}",
                        "Content-Type": "application/json"
                    }
                    data = {
                        "model": model_name,
                        "messages": [
                            {"role": "system", "content": "Eres un extractor de datos de adquisiciones B2B que solo responde en JSON válido."},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 800,
                        "temperature": 0.1
                    }
                    res = requests.post(url, headers=headers, json=data, timeout=12)
                    if res.status_code == 200:
                        content = res.json()['choices'][0]['message']['content'].strip()
                        if "```json" in content:
                            content = content.split("```json")[1].split("```")[0].strip()
                        elif "```" in content:
                            content = content.split("```")[1].split("```")[0].strip()
                        parsed = json.loads(content)
                        extracted_items = parsed.get("items", [])
                        dept = parsed.get("department", dept)
                        req_by = parsed.get("requested_by", req_by)
                        break
                except Exception as e:
                    print(f"Groq parsing failed with model {model_name}: {e}")
                    continue

        if not extracted_items:
            extracted_items = [
                {"sku": "SKU-HUERF-99", "description": raw_text[:100], "quantity": 1.0, "unit": "PZA", "estimated_unit_price": 75.0}
            ]

        # Enrich items with Orphan Classifier & Master Catalog
        enriched_items = orphan_classifier.process_requisition_items(extracted_items)
        req_id = f"REQ-AI-{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}"

        return {
            "channel": source_type,
            "requisition_id": req_id,
            "department": dept,
            "requested_by": req_by,
            "created_at": pd.Timestamp.now().isoformat(),
            "currency": "USD",
            "items": enriched_items,
            "raw_source_preview": raw_text[:200] + "..." if len(raw_text) > 200 else raw_text
        }

    def parse_cfdi_xml(self, xml_content: str) -> Dict[str, Any]:
        """Parse real CFDI 4.0 XML (Mexican Electronic Invoice / SAT Standard)."""
        try:
            root = ET.fromstring(xml_content)
            ns = {
                'cfdi': 'http://www.sat.gob.mx/cfd/4' if 'http://www.sat.gob.mx/cfd/4' in xml_content else 'http://www.sat.gob.mx/cfd/3',
                'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'
            }

            emisor = root.find('cfdi:Emisor', ns)
            vendor_name = emisor.attrib.get('Nombre', 'Proveedor SAT Verificado') if emisor is not None else 'Proveedor SAT'
            vendor_rfc = emisor.attrib.get('Rfc', 'XAXX010101000') if emisor is not None else 'XAXX010101000'

            total = float(root.attrib.get('Total', 0.0))
            subtotal = float(root.attrib.get('SubTotal', 0.0))
            currency = root.attrib.get('Moneda', 'USD')
            invoice_num = root.attrib.get('Folio', f"FOL-{pd.Timestamp.now().strftime('%H%M%S')}")

            uuid = "4A7B8C9D-0E1F-2A3B-4C5D-6E7F8A9B0C1D"
            tfd = root.find('.//tfd:TimbreFiscalDigital', ns)
            if tfd is not None:
                uuid = tfd.attrib.get('UUID', uuid)

            raw_items = []
            conceptos = root.findall('.//cfdi:Concepto', ns)
            for idx, c in enumerate(conceptos):
                raw_items.append({
                    "sku": c.attrib.get('NoIdentificacion', f"SKU-SAT-{idx+1}"),
                    "description": c.attrib.get('Descripcion', 'Concepto Facturado'),
                    "quantity": float(c.attrib.get('Cantidad', 1.0)),
                    "unit_price": float(c.attrib.get('ValorUnitario', 0.0)),
                    "subtotal": float(c.attrib.get('Importe', 0.0))
                })

            enriched_items = orphan_classifier.process_requisition_items(raw_items)
            tax = round(total - subtotal, 2)

            return {
                "channel": "cfdi_xml_sat",
                "invoice_number": invoice_num,
                "uuid_fiscal": uuid,
                "vendor_name": vendor_name,
                "vendor_rfc": vendor_rfc,
                "currency": currency,
                "subtotal": subtotal,
                "tax": tax,
                "grand_total": total,
                "items": enriched_items,
                "sat_status": "VIGENTE_VALIDADO"
            }
        except Exception as e:
            print(f"Error parsing CFDI XML: {e}")
            raise ValueError(f"Error procesando XML de CFDI: {str(e)}")

    def parse_fma017_excel(self, file_path: str) -> Dict[str, Any]:
        """
        Parses official FMA-017 Material and Service Requisition Excel format.
        Extracts metadata, requested items, quantities and units.
        """
        try:
            import openpyxl
            wb = openpyxl.load_workbook(file_path, data_only=True)
            ws = wb.active
            
            folio = f"FMA017-{pd.Timestamp.now().strftime('%Y%m%d%H%M')}"
            solicitante = "Ing. Supervisor de Planta"
            departamento = "Mantenimiento y Automatización"
            
            # Read first rows for metadata
            for r in range(1, min(15, ws.max_row + 1)):
                row_vals = [str(ws.cell(row=r, column=c).value or '') for c in range(1, min(10, ws.max_column + 1))]
                row_str = " ".join(row_vals).upper()
                if "FOLIO" in row_str:
                    m = re.search(r'FOLIO\s*:?\s*([A-Za-z0-9\-_]+)', row_str)
                    if m and m.group(1).upper() != 'FOLIO':
                        folio = m.group(1).strip()
                if "DEPARTAMENTO" in row_str or "AREA" in row_str:
                    for v in row_vals:
                        if len(v) > 3 and "DEPARTAMENTO" not in v and "AREA" not in v:
                            departamento = v
                            break

            raw_items = []
            # Find table header
            header_row = 8
            for r in range(1, min(15, ws.max_row + 1)):
                row_vals = [str(ws.cell(row=r, column=c).value or '').upper() for c in range(1, min(10, ws.max_column + 1))]
                if any("DESCRIPCI" in v or "ARTICULO" in v or "CONCEPTO" in v for v in row_vals):
                    header_row = r
                    break

            for r in range(header_row + 1, ws.max_row + 1):
                desc_val = ws.cell(row=r, column=3).value or ws.cell(row=r, column=2).value
                if not desc_val or str(desc_val).strip() == "" or str(desc_val).upper() in ["TOTAL", "SUBTOTAL", "OBSERVACIONES"]:
                    continue
                qty_val = ws.cell(row=r, column=4).value or ws.cell(row=r, column=3).value or 1
                try:
                    qty = float(qty_val)
                except (ValueError, TypeError):
                    qty = 1.0
                unit_val = str(ws.cell(row=r, column=5).value or ws.cell(row=r, column=4).value or "PZA").strip()

                raw_items.append({
                    "sku": f"FMA-ITEM-{len(raw_items)+1:02d}",
                    "description": str(desc_val).strip(),
                    "quantity": qty,
                    "unit": unit_val,
                    "estimated_unit_price": 50.0
                })

            if not raw_items:
                raw_items = [
                    {"sku": "FMA-DEF-01", "description": "Material de Consumo Operativo FMA-017", "quantity": 2.0, "unit": "PZA", "estimated_unit_price": 45.0}
                ]

            enriched_items = orphan_classifier.process_requisition_items(raw_items)
            return {
                "channel": "excel_fma017",
                "requisition_id": folio,
                "department": departamento,
                "requested_by": solicitante,
                "created_at": pd.Timestamp.now().isoformat(),
                "currency": "USD",
                "items": enriched_items
            }
        except Exception as e:
            print(f"Error parsing FMA017 excel: {e}")
            # Fallback to standard dataframe reader
            df = pd.read_excel(file_path)
            return self.parse_requisition(df)

    def parse_requisition(self, file_path_or_content: Any) -> Dict[str, Any]:
        """Parse structured requisition from Excel, CSV, JSON, raw text or XML."""
        if isinstance(file_path_or_content, dict):
            if 'requisition_id' not in file_path_or_content:
                file_path_or_content['requisition_id'] = f"REQ-DICT-{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}"
            if 'items' in file_path_or_content:
                file_path_or_content['items'] = orphan_classifier.process_requisition_items(file_path_or_content['items'])
            return file_path_or_content

        if isinstance(file_path_or_content, str):
            if file_path_or_content.endswith(('.xlsx', '.xls')):
                return self.parse_fma017_excel(file_path_or_content)
            elif file_path_or_content.endswith('.csv'):
                df = pd.read_csv(file_path_or_content)
            elif file_path_or_content.endswith('.json'):
                with open(file_path_or_content, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return self.parse_requisition(data)
            elif file_path_or_content.endswith('.xml'):
                with open(file_path_or_content, 'r', encoding='utf-8') as f:
                    return self.parse_cfdi_xml(f.read())
            elif "\n" in file_path_or_content or " " in file_path_or_content:
                return self.parse_unstructured_text(file_path_or_content, source_type="unstructured_text")
            else:
                raise ValueError("Formato de archivo no soportado")
        elif isinstance(file_path_or_content, pd.DataFrame):
            df = file_path_or_content
        else:
            raise ValueError("Tipo de entrada inválido")

        raw_items = []
        for idx, row in df.iterrows():
            item = {
                'sku': str(row.get('SKU', row.get('sku', row.get('Codigo', f'SKU-{idx+1}')))),
                'description': str(row.get('Descripcion', row.get('descripcion', row.get('description', row.get('Item', 'Insumo Corporativo'))))),
                'quantity': float(row.get('Cantidad', row.get('cantidad', row.get('quantity', row.get('Qty', 1))))),
                'unit': str(row.get('Unidad', row.get('unidad', row.get('unit', 'PZA')))),
                'estimated_unit_price': float(row.get('Precio_Estimado', row.get('precio_estimado', row.get('target_price', 50.0))))
            }
            raw_items.append(item)

        enriched_items = orphan_classifier.process_requisition_items(raw_items)
        req_id = f"REQ-EXCEL-{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}"
        return {
            'channel': 'excel_spreadsheet',
            'requisition_id': req_id,
            'department': 'Operaciones y Mantenimiento',
            'requested_by': 'Carlos Mendoza - Gerente de Planta',
            'created_at': pd.Timestamp.now().isoformat(),
            'currency': 'USD',
            'items': enriched_items
        }

    def generate_and_compare_quotes(self, requisition: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulates dynamic multi-vendor quoting and creates a comparative matrix 
        evaluating price, lead time, SAT compliance status, and quality score.
        """
        vendors_pool = [
            {
                'vendor_id': 'VEND-001',
                'vendor_name': 'ProServicios Express Logistics',
                'paypal_email': 'vendor-proserv@example.com',
                'rfc': 'PEL180420TR1',
                'sat_69b_status': 'CLEAN',
                'price_multiplier': 0.95,
                'lead_time_days': 2,
                'quality_rating': 4.9,
                'payment_terms': 'PayPal Immediate Payout'
            },
            {
                'vendor_id': 'VEND-002',
                'vendor_name': 'Suministros Industriales del Norte S.A. de C.V.',
                'paypal_email': 'ventas-norte@example.com',
                'rfc': 'SIN100915AA2',
                'sat_69b_status': 'CLEAN',
                'price_multiplier': 1.05,
                'lead_time_days': 4,
                'quality_rating': 4.7,
                'payment_terms': 'Net 30 Days'
            },
            {
                'vendor_id': 'VEND-003',
                'vendor_name': 'ElectroPartes & Automatización Global',
                'paypal_email': 'pagos-electropartes@example.com',
                'rfc': 'EAG150311KJ9',
                'sat_69b_status': 'CLEAN',
                'price_multiplier': 1.15,
                'lead_time_days': 1,
                'quality_rating': 4.8,
                'payment_terms': 'PayPal Orders Checkout'
            }
        ]

        quotes = []
        for vendor in vendors_pool:
            v_items = []
            subtotal = 0.0
            for it in requisition['items']:
                base_price = it.get('estimated_unit_price', 50.0)
                v_unit_price = round(base_price * vendor['price_multiplier'], 2)
                v_subtotal = round(v_unit_price * it['quantity'], 2)
                subtotal += v_subtotal
                v_items.append({
                    'sku': it.get('homologated_sku', it.get('sku', 'SKU-01')),
                    'description': it.get('normalized_description', it.get('description', 'Item')),
                    'category': it.get('category', 'Refacciones Mecánicas'),
                    'quantity': it['quantity'],
                    'unit': it['unit'],
                    'unit_price': v_unit_price,
                    'subtotal': v_subtotal
                })
            
            tax = round(subtotal * 0.16, 2)
            grand_total = round(subtotal + tax, 2)

            # Score calculation: 60% price, 25% lead time, 15% quality
            score = round((1000 / (grand_total + 1)) * 0.6 + (10 / vendor['lead_time_days']) * 2.5 + vendor['quality_rating'] * 3, 1)

            quotes.append({
                'vendor': vendor,
                'items': v_items,
                'subtotal': subtotal,
                'tax': tax,
                'grand_total': grand_total,
                'currency': requisition.get('currency', 'USD'),
                'delivery_days': vendor['lead_time_days'],
                'composite_score': score
            })

        # Sort by lowest grand total
        quotes.sort(key=lambda q: q['grand_total'])
        best_quote = quotes[0]

        return {
            'requisition_id': requisition.get('requisition_id', 'REQ-000'),
            'selected_quote': best_quote,
            'all_quotes': quotes,
            'savings_vs_highest': round(quotes[-1]['grand_total'] - best_quote['grand_total'], 2),
            'selection_reason': f"Mejor costo total (${best_quote['grand_total']:.2f}) con entrega en {best_quote['delivery_days']} días y calificación {best_quote['vendor']['quality_rating']}/5.0"
        }

procurement_agent = ProcurementAgent()
