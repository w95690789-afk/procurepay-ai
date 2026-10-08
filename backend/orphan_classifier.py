import os
import re
import json
import requests
from typing import Dict, Any, List, Optional
import pandas as pd
from .config import settings

# Master Catalog of Normalized Industrial Products
MASTER_CATALOG = [
    {
        "master_sku": "ELEC-SEN-001",
        "description": "Sensor Fotoelectrico Omron E3Z-D61 NPN Difuso",
        "category": "Material Eléctrico y Automatización",
        "sat_clave_prod": "39121500",
        "unit": "PZA",
        "benchmark_price_usd": 145.0,
        "aliases": ["sensor fotoelectrico", "sensor omron", "sensor difuso e3z", "fotocelda omron"]
    },
    {
        "master_sku": "ELEC-SEN-002",
        "description": "Sensor Inductivo M12 PNP NO Alcance 4mm",
        "category": "Material Eléctrico y Automatización",
        "sat_clave_prod": "39121500",
        "unit": "PZA",
        "benchmark_price_usd": 65.0,
        "aliases": ["sensor inductivo", "sensor m12", "proximidad pnp", "sensor de proximidad"]
    },
    {
        "master_sku": "SEG-GNT-101",
        "description": "Guantes de Nitrilo Grado Industrial Calibre 6mil (Caja 100 pzas)",
        "category": "Seguridad Industrial y EPP",
        "sat_clave_prod": "46181504",
        "unit": "CAJA",
        "benchmark_price_usd": 38.5,
        "aliases": ["guantes de nitrilo", "guantes desechables", "guantes nitrilo caja", "guante proteccion"]
    },
    {
        "master_sku": "SEG-CAS-202",
        "description": "Casco de Seguridad Industrial Clase E Dielectrico con Barboquejo",
        "category": "Seguridad Industrial y EPP",
        "sat_clave_prod": "46181701",
        "unit": "PZA",
        "benchmark_price_usd": 22.0,
        "aliases": ["casco de seguridad", "casco blanco", "casco dielectrico", "casco con barboquejo"]
    },
    {
        "master_sku": "QUIM-DES-501",
        "description": "Desengrasante Biodegradable Industrial Heavy Duty Tambor 20 Litros",
        "category": "Químicos y Limpieza Industrial",
        "sat_clave_prod": "47131800",
        "unit": "TAMBOR",
        "benchmark_price_usd": 85.0,
        "aliases": ["desengrasante", "desengrasante industrial", "limpiador biodegradable", "desengrasante tambor"]
    },
    {
        "master_sku": "FERR-TRN-301",
        "description": "Tornilleria Hexagonal Grado 8 Alta Resistencia 1/2 x 2 pulg (Ciento)",
        "category": "Ferretería y Sujeción",
        "sat_clave_prod": "31161500",
        "unit": "CIENTO",
        "benchmark_price_usd": 48.0,
        "aliases": ["tornillos grado 8", "tornillo hexagonal", "tornillos alta resistencia", "tornilleria"]
    },
    {
        "master_sku": "REF-ROD-401",
        "description": "Rodamiento de Bolas SKF 6205-2RS1 Sellado Doble",
        "category": "Refacciones Mecánicas",
        "sat_clave_prod": "31171505",
        "unit": "PZA",
        "benchmark_price_usd": 18.5,
        "aliases": ["balero skf", "rodamiento 6205", "balero 6205 2rs", "rodamiento sellado"]
    }
]

CATEGORIES_MASTER = [
    "Material Eléctrico y Automatización",
    "Seguridad Industrial y EPP",
    "Químicos y Limpieza Industrial",
    "Ferretería y Sujeción",
    "Refacciones Mecánicas",
    "Herramientas y Maquinaria",
    "Papelería y Oficina",
    "Servicios y Logística"
]

class OrphanProductClassifier:
    """
    3-Tier Cognitive Product Classifier & Catalog Homologator:
    - Tier 0: Direct alias / exact match against Master Catalog
    - Tier 1: Groq LLM Semantic Extraction, SAT ClaveProdServ deduction & confidence scoring
    - Tier 2: Heuristic Token/Levenshtein fallback with 'Sugerencia de Alta en Catálogo'
    """
    def __init__(self):
        self.groq_api_key = settings.GROQ_API_KEY
        self.groq_model = "openai/gpt-oss-120b"
        self.groq_fallback = "qwen/qwen3.8-27b"

    def classify_item(self, raw_description: str, raw_sku: Optional[str] = None) -> Dict[str, Any]:
        clean_desc = str(raw_description).strip()
        lower_desc = clean_desc.lower()

        # Tier 0: Direct Match in Master Catalog
        for item in MASTER_CATALOG:
            if raw_sku and raw_sku.upper() == item["master_sku"]:
                return {
                    "is_orphan": False,
                    "confidence_score": 100,
                    "tier_used": "TIER_0_MASTER_CATALOG",
                    "master_sku": item["master_sku"],
                    "normalized_name": item["description"],
                    "category": item["category"],
                    "sat_clave_prod": item["sat_clave_prod"],
                    "unit": item["unit"],
                    "benchmark_price_usd": item["benchmark_price_usd"],
                    "needs_catalog_registration": False,
                    "reasoning": "Coincidencia exacta con SKU del Catálogo Maestro Corporativo."
                }
            for alias in item["aliases"]:
                if alias in lower_desc:
                    return {
                        "is_orphan": False,
                        "confidence_score": 95,
                        "tier_used": "TIER_0_ALIAS_MATCH",
                        "master_sku": item["master_sku"],
                        "normalized_name": item["description"],
                        "category": item["category"],
                        "sat_clave_prod": item["sat_clave_prod"],
                        "unit": item["unit"],
                        "benchmark_price_usd": item["benchmark_price_usd"],
                        "needs_catalog_registration": False,
                        "reasoning": f"Coincidencia directa por alias de ingeniería '{alias}'."
                    }

        # Item is ORPHAN (Uncatalogued / Free text from WhatsApp, email or requisition)
        # Tier 1: Groq LLM Semantic Normalization & SAT Classifier
        if self.groq_api_key:
            prompt = f"""Eres un Agente Especialista en Catálogos Maestros de Compras Industriales y Clasificación SAT / UNSPSC.
El solicitante de planta ingresó este artículo no catalogado (producto huérfano):
"{clean_desc}"

Tu tarea:
1. Normalizarlo a un nombre técnico comercial estándar.
2. Asignar la categoría industrial adecuada de esta lista: {CATEGORIES_MASTER}.
3. Proponer el código fiscal SAT / UNSPSC (8 dígitos) correspondiente.
4. Determinar la unidad estándar de compra (PZA, CAJA, TAMBOR, METRO, LITRO, CIENTO, PAQUETE).
5. Estimar un precio benchmark unitario en USD.
6. Proponer un nuevo código de SKU maestro con formato CAT-SUBCAT-NUM.

Responde ÚNICAMENTE un objeto JSON válido con esta estructura:
{{
    "normalized_name": "Nombre Técnico Normalizado",
    "suggested_master_sku": "GEN-IND-901",
    "category": "Categoría elegida de la lista",
    "sat_clave_prod": "Código SAT 8 dígitos",
    "unit": "PZA",
    "estimated_unit_price_usd": 50.0,
    "confidence_score": 92,
    "technical_reasoning": "Explicación breve de por qué se normalizó así."
}}"""
            for model_name in [self.groq_model, self.groq_fallback]:
                try:
                    url = "https://api.groq.com/openai/v1/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {self.groq_api_key}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "model": model_name,
                        "messages": [
                            {"role": "system", "content": "Eres un clasificador de catálogos ERP que responde solo en JSON estricto."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1,
                        "max_tokens": 500
                    }
                    res = requests.post(url, json=payload, headers=headers, timeout=8)
                    if res.status_code == 200:
                        content = res.json()['choices'][0]['message']['content'].strip()
                        if "```json" in content:
                            content = content.split("```json")[1].split("```")[0].strip()
                        elif "```" in content:
                            content = content.split("```")[1].split("```")[0].strip()
                        ai_data = json.loads(content)
                        return {
                            "is_orphan": True,
                            "confidence_score": ai_data.get("confidence_score", 90),
                            "tier_used": f"TIER_1_GROQ_LLM ({model_name})",
                            "master_sku": ai_data.get("suggested_master_sku", "SKU-AUTO-GEN"),
                            "normalized_name": ai_data.get("normalized_name", clean_desc),
                            "category": ai_data.get("category", "Refacciones Mecánicas"),
                            "sat_clave_prod": ai_data.get("sat_clave_prod", "46181500"),
                            "unit": ai_data.get("unit", "PZA"),
                            "benchmark_price_usd": float(ai_data.get("estimated_unit_price_usd", 50.0)),
                            "needs_catalog_registration": True,
                            "reasoning": ai_data.get("technical_reasoning", "Homologado cognitivamente por IA a partir de texto informal.")
                        }
                except Exception as e:
                    print(f"Tier 1 LLM classification failed ({model_name}): {e}")
                    continue

        # Tier 2: Heuristic Fallback
        cat = "Refacciones Mecánicas"
        if any(w in lower_desc for w in ["cable", "foco", "enchufe", "sensor", "relevador", "fusible"]):
            cat = "Material Eléctrico y Automatización"
        elif any(w in lower_desc for w in ["guante", "casco", "lente", "bota", "careta", "chaleco"]):
            cat = "Seguridad Industrial y EPP"
        elif any(w in lower_desc for w in ["limpiador", "detergente", "quimico", "desengrasante", "aceite", "solvente"]):
            cat = "Químicos y Limpieza Industrial"

        return {
            "is_orphan": True,
            "confidence_score": 75,
            "tier_used": "TIER_2_HEURISTIC_RULE",
            "master_sku": f"SKU-ORPH-{abs(hash(clean_desc)) % 10000:04d}",
            "normalized_name": clean_desc.title(),
            "category": cat,
            "sat_clave_prod": "84111500",
            "unit": "PZA",
            "benchmark_price_usd": 60.0,
            "needs_catalog_registration": True,
            "reasoning": f"Clasificado por reglas de contingencia en categoría '{cat}'."
        }

    def process_requisition_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Processes all items in a requisition, identifying and classifying orphan items."""
        enriched_items = []
        for it in items:
            raw_desc = it.get("description", it.get("descripcion", it.get("Item", "Insumo General")))
            raw_sku = it.get("sku", it.get("SKU", it.get("codigo", None)))
            classification = self.classify_item(raw_desc, raw_sku)
            
            merged = {
                **it,
                "original_description": raw_desc,
                "normalized_description": classification["normalized_name"],
                "homologated_sku": classification["master_sku"],
                "category": classification["category"],
                "sat_clave_prod": classification["sat_clave_prod"],
                "is_orphan": classification["is_orphan"],
                "classification_confidence": classification["confidence_score"],
                "classification_tier": classification["tier_used"],
                "classification_reasoning": classification["reasoning"],
                "needs_catalog_registration": classification["needs_catalog_registration"]
            }
            if "estimated_unit_price" not in merged or not merged["estimated_unit_price"]:
                merged["estimated_unit_price"] = classification["benchmark_price_usd"]
            enriched_items.append(merged)
        return enriched_items

orphan_classifier = OrphanProductClassifier()
