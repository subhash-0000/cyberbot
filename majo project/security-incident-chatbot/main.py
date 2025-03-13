from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
from typing import List, Optional
from datetime import datetime

from app.database import get_db, Base, engine
from app.models import Alert, AlertCreate, AlertResponse
from app.services.openai_service import classify_alert_severity, generate_response_recommendation
from app.services.jira_service import create_jira_ticket
from app.services.slack_service import send_slack_alert
from app.repositories.alert_repository import create_alert, get_alert_by_id, get_alerts_by_filter
from sqlalchemy.orm import Session

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Security Incident Management Chatbot")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """
    Serve the main chat interface
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/process_alert/", response_model=AlertResponse)
async def process_alert(alert: AlertCreate, db: Session = Depends(get_db)):
    """
    Process an incoming security alert:
    1. Classify severity using OpenAI
    2. Store in database
    3. Trigger JIRA ticket for High/Critical alerts
    4. Send Slack notification for High/Critical alerts
    """
    # Classify severity using OpenAI
    severity = await classify_alert_severity(alert.message)
    
    # Create the alert in the database
    new_alert = create_alert(db, alert, severity)
    
    # For High or Critical alerts, create JIRA ticket and send Slack notification
    if severity in ["High", "Critical"]:
        jira_ticket_id = await create_jira_ticket(new_alert)
        new_alert.jira_ticket_id = jira_ticket_id
        db.commit()
        
        # Send Slack notification
        await send_slack_alert(new_alert)
    
    return AlertResponse(
        id=new_alert.id,
        source=new_alert.source,
        severity=new_alert.severity,
        message=new_alert.message,
        created_at=new_alert.created_at,
        jira_ticket_id=new_alert.jira_ticket_id
    )

@app.get("/alerts/", response_model=List[AlertResponse])
async def get_alerts(
    severity: Optional[str] = None,
    source: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Fetch alerts with optional filtering by severity, source, or date range
    """
    alerts = get_alerts_by_filter(db, severity, source, start_date, end_date)
    return alerts

@app.get("/alert/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: int, db: Session = Depends(get_db)):
    """
    Fetch a specific alert by ID
    """
    alert = get_alert_by_id(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert

@app.post("/create_ticket/{alert_id}")
async def trigger_jira_ticket(alert_id: int, db: Session = Depends(get_db)):
    """
    Manually trigger JIRA ticket creation for an alert
    """
    alert = get_alert_by_id(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    if alert.jira_ticket_id:
        return {"message": f"JIRA ticket already exists: {alert.jira_ticket_id}"}
    
    jira_ticket_id = await create_jira_ticket(alert)
    alert.jira_ticket_id = jira_ticket_id
    db.commit()
    
    return {"message": f"JIRA ticket created: {jira_ticket_id}"}

@app.get("/automated_response/{alert_id}")
async def get_automated_response(alert_id: int, db: Session = Depends(get_db)):
    """
    Generate an automated incident response recommendation
    """
    alert = get_alert_by_id(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    response = await generate_response_recommendation(alert)
    return {"response": response}

@app.post("/slack_alert/{alert_id}")
async def trigger_slack_alert(alert_id: int, db: Session = Depends(get_db)):
    """
    Manually trigger a Slack notification for an alert
    """
    alert = get_alert_by_id(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    result = await send_slack_alert(alert)
    return {"message": "Slack notification sent successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)