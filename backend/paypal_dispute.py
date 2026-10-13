import time
import hashlib
from typing import Dict, Any, List, Optional
from .paypal_service import paypal_service

class PayPalDisputeEngine:
    """
    Automated AI-Powered Dispute Resolution Engine for PayPal.
    Triggered when SAT 3-Way matching audits fail due to:
    - Vendor listed in SAT Art. 69-B (EFOS / Blacklisted invoicing company)
    - Tampered pricing exceeding tolerance (>15% overcharge)
    - Unauthorized quantity inflation or phantom delivery
    Generates formal claims compliant with PayPal Disputes API v1.
    """

    def generate_dispute_docket(
        self,
        requisition_id: str,
        vendor_name: str,
        vendor_rfc: str,
        invoice_number: str,
        discrepancies: List[Dict[str, Any]],
        claimed_amount: float,
        currency: str = "USD",
        paypal_order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Builds a comprehensive legal and evidence dossier for PayPal Disputes.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S UTC")
        dispute_id = f"PP-DISP-{int(time.time())}"
        
        # Categorize primary dispute reason
        def d_str(item: Any) -> str:
            if isinstance(item, dict):
                return f"{item.get('type', '')} {item.get('detail', '')}"
            return str(item)

        is_efos = any("69-B" in d_str(d) or "EFOS" in d_str(d) for d in discrepancies)
        is_price_fraud = any("excede" in d_str(d).lower() or "discrepancia" in d_str(d).lower() for d in discrepancies)

        if is_efos:
            reason_code = "UNAUTHORISED_TRANSACTION"
            reason_title = "Proveedor Fiscalmente Inexistente (SAT Art. 69-B EFOS)"
            severity = "CRITICAL_FRAUD"
        elif is_price_fraud:
            reason_code = "INCORRECT_TRANSACTION_AMOUNT"
            reason_title = "Cobro Excesivo No Autorizado vs Orden de Compra"
            severity = "HIGH_FINANCIAL_DISCREPANCY"
        else:
            reason_code = "MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED"
            reason_title = "Inconsistencia de Especificaciones Técnicas"
            severity = "MEDIUM"

        # Evidence Hash
        raw_evidence = f"{dispute_id}|{vendor_rfc}|{invoice_number}|{claimed_amount}|{timestamp}"
        evidence_hash = hashlib.sha256(raw_evidence.encode()).hexdigest()

        # Generate formal AI resolution statement
        statement = (
            f"RECLAMACIÓN FORMAL DE ADQUISICIÓN B2B ANTE PAYPAL RESOLUTION CENTER\n"
            f"Folio de Reclamación: {dispute_id}\n"
            f"Orden de Compra / Requisición: {requisition_id}\n"
            f"Proveedor Reportado: {vendor_name} (RFC: {vendor_rfc})\n"
            f"Factura Cuestionada: {invoice_number} por ${claimed_amount:.2f} {currency}\n\n"
            f"DIAGNÓSTICO DEL AGENTE DE AUDITORÍA 3-WAY MATCHING:\n"
        )
        for idx, d in enumerate(discrepancies, 1):
            statement += f"  [{idx}] {d_str(d)}\n"

        statement += (
            f"\nFUNDAMENTO Y PETICIÓN:\n"
            f"Se solicita la retención inmediata de fondos y cancelación de la orden {paypal_order_id or 'ORD-PENDING'} "
            f"al amparo de la Política de Protección al Comprador de PayPal para Empresas.\n"
            f"Sello Criptográfico de Auditoría: SHA256:{evidence_hash[:32]}"
        )

        return {
            "dispute_id": dispute_id,
            "status": "DRAFTED_AND_LOGGED_PAYPAL",
            "paypal_order_id": paypal_order_id or f"ORD-DISPUTED-{int(time.time())}",
            "reason_code": reason_code,
            "reason_title": reason_title,
            "severity": severity,
            "dispute_amount": {
                "value": f"{claimed_amount:.2f}",
                "currency_code": currency
            },
            "vendor_reported": {
                "name": vendor_name,
                "rfc": vendor_rfc
            },
            "evidence_hash": evidence_hash,
            "resolution_requested": "IMMEDIATE_REFUND_OR_CANCELLATION",
            "ai_statement": statement,
            "discrepancies_count": len(discrepancies),
            "discrepancies": discrepancies,
            "created_at": timestamp
        }

paypal_dispute_engine = PayPalDisputeEngine()
