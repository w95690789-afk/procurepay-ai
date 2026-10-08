import os
import json
import time
from typing import Dict, Any, Optional
from .config import settings
from .procurement_agent import procurement_agent
from .accounting_auditor import accounting_auditor
from .accounting_engine import accounting_engine
from .sharepoint_emulator import sharepoint_emulator
from .paypal_service import paypal_service

class ProcurePayOrchestrator:
    def __init__(self):
        self.auto_approval_threshold = settings.AUTO_APPROVAL_THRESHOLD_USD

    def process_end_to_end_procurement(
        self,
        requisition_input: Any,
        incoming_invoice: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        logs = []
        start_time = time.time()

        # Step 1: SharePoint Document Ingestion & Orphan Item Homologation
        logs.append({
            'step': 1,
            'name': 'SharePoint Ingestion & Orphan Classification',
            'status': 'IN_PROGRESS',
            'msg': 'Sincronizando documento de SharePoint y normalizando artículos huérfanos con IA...'
        })
        requisition = procurement_agent.parse_requisition(requisition_input)
        req_id = requisition['requisition_id']
        num_items = len(requisition['items'])
        orphans_count = sum(1 for it in requisition['items'] if it.get('is_orphan', False))

        logs[-1]['status'] = 'COMPLETED'
        logs[-1]['msg'] = (
            f"Requisición {req_id} procesada con éxito ({num_items} líneas). "
            f"Detectados y clasificados por IA: {orphans_count} artículos huérfanos."
        )

        # Step 2: Multi-Vendor RFQ & Consolidator Matrix
        logs.append({
            'step': 2,
            'name': 'Multi-Vendor RFQ & Pricing Consolidator',
            'status': 'IN_PROGRESS',
            'msg': 'Solicitando cotizaciones automatizadas y generando cuadro comparativo semaforizado...'
        })
        quotes_analysis = procurement_agent.generate_and_compare_quotes(requisition)
        selected_quote = quotes_analysis['selected_quote']
        vendor_name = selected_quote['vendor']['vendor_name']
        grand_total = selected_quote['grand_total']
        curr = selected_quote['currency']
        savings = quotes_analysis['savings_vs_highest']

        logs[-1]['status'] = 'COMPLETED'
        logs[-1]['msg'] = (
            f"Proveedor seleccionado: '{vendor_name}' por ${grand_total:.2f} {curr} "
            f"(Ahorro proyectado vs peor cotización: ${savings:.2f} {curr})."
        )

        # Step 3: Incoming Invoice & 3-Way Matching Audit
        logs.append({
            'step': 3,
            'name': 'SAT 3-Way Matching & Art. 69-B Fiscal Audit',
            'status': 'IN_PROGRESS',
            'msg': 'Auditando factura contra orden de compra y verificando listas negras del SAT...'
        })

        if not incoming_invoice:
            incoming_invoice = {
                'invoice_number': f"FAC-{int(time.time())}",
                'vendor_name': selected_quote['vendor']['vendor_name'],
                'currency': selected_quote['currency'],
                'items': [
                    {
                        'sku': it['sku'],
                        'description': it['description'],
                        'quantity': it['quantity'],
                        'unit_price': it['unit_price'],
                        'subtotal': it['subtotal']
                    }
                    for it in selected_quote['items']
                ],
                'subtotal': selected_quote['subtotal'],
                'tax': selected_quote['tax'],
                'grand_total': selected_quote['grand_total']
            }

        audit_result = accounting_auditor.audit_invoice_3way_matching(requisition, selected_quote, incoming_invoice)

        if not audit_result['audit_passed']:
            num_disc = len(audit_result['discrepancies'])
            logs[-1]['status'] = 'FAILED'
            logs[-1]['msg'] = f"Auditoría fallida: {num_disc} discrepancias o alerta fiscal detectada. Pago bloqueado."
            return {
                'pipeline_status': 'REJECTED_AUDIT_DISCREPANCY',
                'execution_time_seconds': round(time.time() - start_time, 2),
                'requisition': requisition,
                'quotes_analysis': quotes_analysis,
                'invoice': incoming_invoice,
                'audit_result': audit_result,
                'accounting_poliza': None,
                'settlement': None,
                'sharepoint_archive': None,
                'logs': logs
            }

        score = audit_result['compliance_score']
        logs[-1]['status'] = 'COMPLETED'
        logs[-1]['msg'] = f"Auditoría 3-Way Matching 100% aprobada (Score Fiscal: {score}%)."

        # Step 4: Intelligent Accounting Engine & Journal Entry Generation
        logs.append({
            'step': 4,
            'name': 'Cognitive Accounting Engine & Balanced Póliza',
            'status': 'IN_PROGRESS',
            'msg': 'Determinando cuentas contables, centro de costos y generando asiento contable (Debe/Haber)...'
        })

        amount_to_pay = audit_result['approved_amount']
        currency = audit_result['currency']
        vendor_email = audit_result['vendor_paypal_email']

        settlement_result = {}

        # Step 5: Policy & PayPal Settlement Gateway
        logs.append({
            'step': 5,
            'name': 'PayPal Settlement Gateway Execution',
            'status': 'IN_PROGRESS',
            'msg': f'Evaluando política de autorización (Umbral Autónomo: ${self.auto_approval_threshold} USD)...'
        })

        if amount_to_pay <= self.auto_approval_threshold:
            # Autonomous Zero-Touch Settlement
            paypal_order = paypal_service.create_order(
                amount=amount_to_pay,
                currency=currency,
                description=f"ProcurePay Settlement for {req_id} - {vendor_name}",
                custom_id=req_id
            )
            paypal_payout = paypal_service.execute_payout(
                recipient_email=vendor_email,
                amount=amount_to_pay,
                currency=currency,
                note=f"Pago instantáneo de compra {req_id} para {vendor_name}"
            )

            order_id = paypal_order.get('id') or paypal_order.get('order_id')
            payout_id = paypal_payout.get('batch_header', {}).get('payout_batch_id') or paypal_payout.get('payout_batch_id') or paypal_payout.get('batch_id')

            settlement_result = {
                'mode': 'AUTONOMOUS_ZERO_TOUCH',
                'status': 'SETTLED',
                'paypal_order_id': order_id,
                'paypal_order_status': paypal_order.get('status', 'CREATED'),
                'paypal_payout_batch_id': payout_id,
                'amount_paid': amount_to_pay,
                'currency': currency,
                'recipient': vendor_email,
                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
            }
            logs[-1]['status'] = 'COMPLETED'
            logs[-1]['msg'] = f"Liquidación autónoma exitosa en PayPal Sandbox (Payout Batch ID: {settlement_result['paypal_payout_batch_id']})."
            pipeline_final_status = 'AUTONOMOUSLY_APPROVED_AND_SETTLED'
        else:
            # Human-in-the-Loop Approval Required
            paypal_order = paypal_service.create_order(
                amount=amount_to_pay,
                currency=currency,
                description=f"High Value Purchase Authorization for {req_id} - {vendor_name}",
                custom_id=req_id
            )
            order_id = paypal_order.get('id') or paypal_order.get('order_id')
            approval_link = next((l['href'] for l in paypal_order.get('links', []) if l.get('rel') == 'approve'), None)

            settlement_result = {
                'mode': 'HUMAN_APPROVAL_REQUIRED',
                'status': 'PENDING_EXECUTIVE_APPROVAL',
                'paypal_order_id': order_id,
                'paypal_order_status': paypal_order.get('status', 'CREATED'),
                'approval_link': approval_link,
                'amount_pending': amount_to_pay,
                'currency': currency,
                'recipient': vendor_email,
                'reason': f"El monto (${amount_to_pay:.2f} {currency}) supera el umbral autónomo de ${self.auto_approval_threshold} {currency}."
            }
            logs[-1]['status'] = 'PENDING'
            logs[-1]['msg'] = f"Monto alto. Orden PayPal {settlement_result['paypal_order_id']} creada esperando firma directiva."
            pipeline_final_status = 'PENDING_HUMAN_APPROVAL'

        # Generate Balanced Accounting Póliza
        accounting_poliza = accounting_engine.generate_balanced_journal_entry(
            folio=req_id,
            requisition=requisition,
            approved_quote=selected_quote,
            paypal_settlement=settlement_result
        )
        logs[3]['status'] = 'COMPLETED'
        logs[3]['msg'] = (
            f"Póliza '{accounting_poliza['poliza_number']}' generada y balanceada "
            f"(Debe: ${accounting_poliza['total_debe']:.2f} = Haber: ${accounting_poliza['total_haber']:.2f}). "
            f"ERP Destino: {accounting_poliza['classification_metadata']['erp_target']}."
        )

        # Step 6: Archive to SharePoint
        archive_path = sharepoint_emulator.archive_approved_procurement(
            folio=req_id,
            requisition_data=requisition,
            comparative_quote=quotes_analysis,
            audit_report=audit_result,
            accounting_poliza=accounting_poliza,
            paypal_settlement=settlement_result
        )

        return {
            'pipeline_status': pipeline_final_status,
            'execution_time_seconds': round(time.time() - start_time, 2),
            'requisition': requisition,
            'quotes_analysis': quotes_analysis,
            'invoice': incoming_invoice,
            'audit_result': audit_result,
            'accounting_poliza': accounting_poliza,
            'settlement': settlement_result,
            'sharepoint_archive': {
                'folder': '04_Aprobados_Pagados',
                'file_path': archive_path,
                'archive_name': os.path.basename(archive_path)
            },
            'logs': logs
        }

orchestrator = ProcurePayOrchestrator()
