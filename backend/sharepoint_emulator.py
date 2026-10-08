import os
import json
import time
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd

class SharePointEmulator:
    """
    Virtual SharePoint Document Library & Sync Manager.
    Emulates Microsoft Graph API / SharePoint online folder structures and workflows:
    - /Buzon_Entrada_Requisiciones: Incoming requisitions
    - /En_Cotizacion: RFQs actively being processed
    - /Consolidados: Comparative matrices and vendor rankings
    - /Aprobados_Pagados: Final approved orders with PayPal settlements & accounting polizas
    """
    def __init__(self, base_storage_dir: Optional[str] = None):
        if not base_storage_dir:
            if os.environ.get("VERCEL") or not os.access(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), os.W_OK):
                base_storage_dir = "/tmp/sharepoint_storage"
            else:
                base_storage_dir = os.path.join(os.path.dirname(__file__), "..", "sharepoint_storage")
        self.base_dir = os.path.abspath(base_storage_dir)
        
        self.folders = {
            "buzon_entrada": "01_Buzon_Entrada_Requisiciones",
            "en_cotizacion": "02_En_Cotizacion",
            "consolidados": "03_Consolidados_Comparativos",
            "aprobados_pagados": "04_Aprobados_Pagados"
        }
        self._init_folders()
        self._seed_sample_documents()

    def _init_folders(self):
        for folder_name in self.folders.values():
            folder_path = os.path.join(self.base_dir, folder_name)
            os.makedirs(folder_path, exist_ok=True)

    def _seed_sample_documents(self):
        """Seed initial documents in the SharePoint emulator if empty."""
        buzon_dir = os.path.join(self.base_dir, self.folders["buzon_entrada"])
        if len(os.listdir(buzon_dir)) == 0:
            sample_req = {
                "folio": "FMA-017-REQ-8821",
                "department": "Planta Ensamble Automotriz - Bahía 4",
                "solicitante": "Ing. Roberto Garza - Jefe de Turno",
                "fecha_solicitud": datetime.now().strftime("%Y-%m-%d"),
                "prioridad": "ALTA",
                "items": [
                    {"sku": "SKU-HUERF-01", "descripcion": "Guantes de nitrilo grado industrial 6 milipulgadas caja 100", "cantidad": 5, "unidad": "CAJA", "precio_estimado": 42.0},
                    {"sku": "SKU-ELEC-44", "descripcion": "Sensor inductivo M12 PNP NO alcance 4mm", "cantidad": 2, "unidad": "PZA", "precio_estimado": 65.0},
                    {"sku": "SKU-HUERF-02", "descripcion": "Desengrasante biodegradable de alta resistencia tambor 20L", "cantidad": 1, "unidad": "TAMBOR", "precio_estimado": 85.0}
                ]
            }
            sample_file = os.path.join(buzon_dir, "Requisicion_FMA017_Folio_8821.json")
            with open(sample_file, "w", encoding="utf-8") as f:
                json.dump(sample_req, f, indent=2, ensure_ascii=False)

    def list_library_contents(self) -> Dict[str, Any]:
        """Returns the document hierarchy and metadata of the virtual SharePoint library."""
        library_data = {}
        total_files = 0

        for key, folder_name in self.folders.items():
            folder_path = os.path.join(self.base_dir, folder_name)
            files_list = []
            if os.path.exists(folder_path):
                for fname in sorted(os.listdir(folder_path)):
                    fpath = os.path.join(folder_path, fname)
                    if os.path.isfile(fpath):
                        stat = os.stat(fpath)
                        files_list.append({
                            "name": fname,
                            "size_kb": round(stat.st_size / 1024, 2),
                            "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                            "extension": fname.split(".")[-1].upper() if "." in fname else "FILE",
                            "status": key.upper(),
                            "path": f"/sites/Compras-Corporativas/Shared Documents/{folder_name}/{fname}"
                        })
            library_data[key] = {
                "folder_name": folder_name,
                "display_name": folder_name.replace("_", " "),
                "file_count": len(files_list),
                "files": files_list
            }
            total_files += len(files_list)

        return {
            "site_url": "https://corporativo.sharepoint.com/sites/CISA-Compras",
            "library_name": "Requisiciones_y_Auditorias_2026",
            "last_sync_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sync_status": "ONLINE_CONNECTED",
            "total_documents": total_files,
            "folders": library_data
        }

    def stage_file_to_folder(self, source_file_path: str, target_folder_key: str, new_filename: Optional[str] = None) -> str:
        """Copies or moves a file to a specific SharePoint folder stage."""
        if target_folder_key not in self.folders:
            raise ValueError(f"Carpeta no válida: {target_folder_key}")
        
        target_dir = os.path.join(self.base_dir, self.folders[target_folder_key])
        os.makedirs(target_dir, exist_ok=True)
        
        target_filename = new_filename if new_filename else os.path.basename(source_file_path)
        dest_path = os.path.join(target_dir, target_filename)
        
        shutil.copy2(source_file_path, dest_path)
        return dest_path

    def move_document_stage(self, filename: str, from_folder_key: str, to_folder_key: str) -> bool:
        """Moves a document through the procurement pipeline lifecycle."""
        src_path = os.path.join(self.base_dir, self.folders.get(from_folder_key, ""), filename)
        dest_path = os.path.join(self.base_dir, self.folders.get(to_folder_key, ""), filename)
        
        if os.path.exists(src_path):
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.move(src_path, dest_path)
            return True
        return False

    def archive_approved_procurement(
        self,
        folio: str,
        requisition_data: Dict[str, Any],
        comparative_quote: Dict[str, Any],
        audit_report: Dict[str, Any],
        accounting_poliza: Dict[str, Any],
        paypal_settlement: Dict[str, Any]
    ) -> str:
        """Generates an executive enterprise compliance packet and archives it to /Aprobados_Pagados."""
        archive_dir = os.path.join(self.base_dir, self.folders["aprobados_pagados"])
        packet_filename = f"Expediente_Auditoria_Pagada_{folio}_{datetime.now().strftime('%Y%m%d%H%M')}.json"
        packet_path = os.path.join(archive_dir, packet_filename)
        
        expediente = {
            "metadata": {
                "folio_corporativo": folio,
                "sharepoint_site": "https://corporativo.sharepoint.com/sites/CISA-Compras",
                "fecha_archivado": datetime.now().isoformat(),
                "estatus_final": "PAGADO_Y_CONTABILIZADO_EN_ERP",
                "auditor_responsable": "ProcurePay Autonomous AI Engine v2.5"
            },
            "requisicion_origen": requisition_data,
            "cuadro_comparativo_rfq": comparative_quote,
            "auditoria_3way_matching": audit_report,
            "asiento_contable_poliza": accounting_poliza,
            "liquidacion_paypal": paypal_settlement
        }

        with open(packet_path, "w", encoding="utf-8") as f:
            json.dump(expediente, f, indent=2, ensure_ascii=False)
            
        return packet_path

sharepoint_emulator = SharePointEmulator()
