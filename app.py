# app.py
import streamlit as st
from streamlit_mermaid import st_mermaid
import pandas as pd
import requests
import json
import time
import os
from typing import Dict
# ========== CONFIG ==========
# By default we run in MOCK mode (no GCP required).
MOCK_MODE = os.environ.get("MOCK_MODE", "true").lower() in ("1", "true", "yes")
API_BASE = os.environ.get("API_BASE", "http://0.0.0.0:8000")  # used only when MOCK_MODE=False
st.set_page_config(page_title="Agentic Automation POC", layout="wide")
st.title("🤖 Agentic Task Automation — POC (IntelliFlow)")
# --------- helpers ----------
def call_planner_local(user_input: str):
   """
   Simple local planner mock: looks for keywords and builds a workflow JSON.
   Replace with a call to your Planner (Cloud Run) when ready.
   """
   wf = {"workflow": []}
   txt = user_input.lower()
   if "invoice" in txt or "receipt" in txt or "reconcile" in txt:
       wf["workflow"].append({"id": "extract_invoice", "tool": "InvoiceProcessor", "inputs": {}})
       if "reconcile" in txt:
           wf["workflow"].append({"id": "reconcile", "tool": "ReconciliationService", "inputs": {}})
       wf["workflow"].append({"id": "save", "tool": "FirestoreSaver", "inputs": {}})
   elif "support" in txt or "ticket" in txt or "reply" in txt:
       wf["workflow"].append({"id": "classify_ticket", "tool": "TicketClassifier", "inputs": {}})
       wf["workflow"].append({"id": "generate_reply", "tool": "SupportReply", "inputs": {}})
       wf["workflow"].append({"id": "update_crm", "tool": "CRMUpdater", "inputs": {}})
   else:
       # generic: try support flow
       wf["workflow"].append({"id": "analyze", "tool": "GenericAnalyzer", "inputs": {}})
   # Add metadata
   wf["metadata"] = {"created_by": "streamlit_poc", "created_at": int(time.time())}
   return wf
def execute_workflow_local(workflow: dict, uploaded_file_bytes=None):
   """
   Local executor mock: loops through workflow steps and returns outputs.
   Replace with /execute-workflow to Cloud Run / Cloud Workflows when ready.
   """
   results = {"steps": [], "status": "running"}
   for idx, step in enumerate(workflow.get("workflow", []), start=1):
       step_id = step.get("id")
       tool = step.get("tool")
       # simulate processing delay
       time.sleep(1)
       # fake outputs
       if tool == "InvoiceProcessor":
           out = {"invoice_no": "INV-1001", "amount": 1234.56, "vendor": "Acme Pvt Ltd"}
       elif tool == "ReconciliationService":
           out = {"status": "reconciled", "discrepancy": 0.0}
       elif tool == "SupportReply":
           out = {"draft_reply": "Hi, thanks for contacting us. We will look into your billing query."}
       elif tool == "CRMUpdater":
           out = {"crm_status": "updated", "crm_id": "CRM-998"}
       else:
           out = {"result": f"Executed {tool} (mock)"}
       results["steps"].append({"step_id": step_id, "tool": tool, "output": out, "status": "success"})
   results["status"] = "completed"
   return results
def call_remote(method: str, path: str, json_payload=None, files=None):
   url = API_BASE.rstrip("/") + path
   try:
       if method.upper() == "POST":
           resp = requests.post(url, json=json_payload, files=files, timeout=120)
       else:
           resp = requests.get(url, params=json_payload, timeout=30)
       resp.raise_for_status()
       return resp.json()
   except Exception as e:
       return {"error": str(e)}
# ====== UI ===========
st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Prompt & Workflow", "Execute Workflow", "Dashboard", "Settings"])
# ---------- Prompt & Workflow page ----------
if page == "Prompt & Workflow":
   st.header("1) Describe what you want to automate")
   user_input = st.text_area("Write a natural language instruction (e.g. \"Automate invoice data entry and reconciliation\")", height=120)
   uploaded_file = st.file_uploader("Optionally upload an example file (invoice/image/pdf)", type=["pdf", "png", "jpg", "jpeg"])
   st.session_state["uploadedFile"] = uploaded_file
   col1, col2 = st.columns([1, 1])
   with col1:
       if st.button("Generate Workflow"):
           if not user_input:
               st.warning("Please enter a prompt.")
           else:
               with st.spinner("Generating workflow..."):
                   if MOCK_MODE:
                       workflow = call_planner_local(user_input)
                   else:
                       payload = {"user_input": user_input}
                       # if file uploaded, send as multipart
                       if uploaded_file is not None:
                           files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                           planner_resp = call_remote("POST", "/plan-workflow", json_payload=None, files=files)
                       else:
                           planner_resp = call_remote("POST", "/plan-workflow", json_payload=payload)
                       # planner_resp expected to be valid workflow JSON
                       workflow = planner_resp
               st.success("Workflow generated.")
               st.session_state["workflow"] = workflow
   with col2:
       if "workflow" in st.session_state:
           st.subheader("Generated Workflow (editable)")
           wf_json = json.dumps(st.session_state["workflow"], indent=2)
           edited = st.text_area("Edit workflow JSON if needed", value=wf_json, height=300)
           if st.button("Save Edited Workflow"):
               try:
                   parsed = json.loads(edited)
                   st.session_state["workflow"] = parsed
                   st.success("Workflow updated.")
               except Exception as e:
                   st.error(f"Invalid JSON: {e}")
       else:
           st.info("No workflow generated yet. Enter a prompt and click 'Generate Workflow'.")
# ---------- Execute Workflow ----------
if page == "Execute Workflow":
   st.header("2) Execute workflow")
   if "workflow" not in st.session_state:
       st.info("No workflow saved. Generate one on the 'Prompt & Workflow' tab.")
   else:
       st.subheader("Workflow to execute")
       st.json(st.session_state["workflow"])
       if st.button("Execute Workflow"):
           with st.spinner("Executing..."):
               if MOCK_MODE:
                   uploaded_file = st.session_state["uploadedFile"]
                   results = execute_workflow_local(st.session_state["workflow"], uploaded_file_bytes=(uploaded_file.getvalue() if uploaded_file else None))
               else:
                   results = call_remote("POST", "/execute-workflow", json_payload={"workflow": st.session_state["workflow"]})
               st.session_state["last_results"] = results
               st.success("Execution finished.")
       if "last_results" in st.session_state:
           st.subheader("Execution Results")
           st.json(st.session_state["last_results"])
# ---------- Dashboard ----------
if page == "Dashboard":
   st.header("3) Dashboard (POC)")
   st.markdown("- Total tasks automated: **(demo)**")
   if MOCK_MODE:
       demo_stats = {"total_tasks": 12, "hours_saved": 4.5, "category_counts": {"finance": 8, "support": 4}}
   else:
       demo_stats = call_remote("GET", "/stats")
   st.metric("Total Tasks Automated", demo_stats.get("total_tasks", 0))
   st.metric("Estimated Hours Saved", demo_stats.get("hours_saved", 0))
   st.subheader("Categories")
   st.bar_chart(pd.DataFrame([demo_stats.get("category_counts", {})]))
# ---------- Settings ----------
if page == "Settings":
   st.header("Settings")
   st.write("MOCK_MODE:", MOCK_MODE)
   st.write("API_BASE:", API_BASE)
   st.info("To connect to a real backend, run Streamlit with MOCK_MODE=false and set API_BASE to your Cloud Run backend.")