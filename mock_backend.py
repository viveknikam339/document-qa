# mock_backend.py
from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
import uvicorn
import time
app = FastAPI()
class PlanRequest(BaseModel):
   user_input: str
@app.post("/plan-workflow")
async def plan_workflow(req: PlanRequest):
   txt = req.user_input.lower()
   wf = {"workflow": [], "metadata": {"created_at": int(time.time())}}
   if "invoice" in txt:
       wf["workflow"].append({"id": "extract_invoice", "tool": "InvoiceProcessor"})
       if "reconcile" in txt:
           wf["workflow"].append({"id": "reconcile", "tool": "ReconciliationService"})
       wf["workflow"].append({"id": "save", "tool": "FirestoreSaver"})
   else:
       wf["workflow"].append({"id": "classify_ticket", "tool": "TicketClassifier"})
       wf["workflow"].append({"id": "generate_reply", "tool": "SupportReply"})
   return wf
@app.post("/execute-workflow")
async def execute_workflow(payload: dict):
   results = {"steps": []}
   for step in payload.get("workflow", []):
       tool = step.get("tool")
       time.sleep(1)  # simulate delay
       if tool == "InvoiceProcessor":
           out = {"invoice_no": "INV-0001", "amount": 500.0}
       elif tool == "ReconciliationService":
           out = {"status": "reconciled"}
       elif tool == "SupportReply":
           out = {"draft_reply": "Mock reply: We will check and revert."}
       else:
           out = {"info": f"Executed {tool}"}
       results["steps"].append({"step": step.get("id"), "tool": tool, "output": out})
   results["status"] = "completed"
   return results
@app.get("/stats")
async def stats():
   return {"total_tasks": 12, "hours_saved": 3.7, "category_counts": {"finance": 8, "support": 4}}
if __name__ == "__main__":
   uvicorn.run(app, host="0.0.0.0", port=8000)