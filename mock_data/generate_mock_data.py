import pandas as pd
import json
import os

mock_dir = os.path.dirname(__file__)

# Sample 1: Industrial Automation Requisition (Under $500 - Autonomous)
df_industrial = pd.DataFrame([
    {"SKU": "IND-VALV-01", "Descripcion": "Valvula de Control Neumatica 1/2 pulg", "Cantidad": 4, "Unidad": "PZA", "Precio_Estimado": 65.00},
    {"SKU": "IND-MANO-02", "Descripcion": "Manometro Digital de Presion 0-100 PSI", "Cantidad": 2, "Unidad": "PZA", "Precio_Estimado": 45.00},
    {"SKU": "IND-SEAL-03", "Descripcion": "Juego de Sellos Hidraulicos NBR", "Cantidad": 5, "Unidad": "KIT", "Precio_Estimado": 18.00}
])
df_industrial.to_excel(os.path.join(mock_dir, "requisicion_industrial_menor.xlsx"), index=False)

# Sample 2: Capital Equipment Requisition (Over $500 - Human Approval)
df_capex = pd.DataFrame([
    {"SKU": "PLC-SIEM-S7", "Descripcion": "Controlador PLC Modular Siemens S7-1200", "Cantidad": 2, "Unidad": "PZA", "Precio_Estimado": 450.00},
    {"SKU": "HMI-PANE-07", "Descripcion": "Pantalla HMI Tactil 7 pulgadas Color", "Cantidad": 1, "Unidad": "PZA", "Precio_Estimado": 380.00}
])
df_capex.to_excel(os.path.join(mock_dir, "requisicion_equipamiento_mayor.xlsx"), index=False)

print("Mock Excel files generated successfully in:", mock_dir)
