from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Initialize FastAPI app
app = FastAPI()

# Environment variables (replace with actual values or use dotenv)
OPENAI_API_KEY = "API"
SLACK_BOT_TOKEN = "BOT_TOKEN"
JIRA_API_URL = "https://btcours-team-dd85r7s7.atlassian.net/rest/api/3"
JIRA_AUTH = ("EMAIL"
,"API")
DATABASE_URL = "postgresql://postgres:123@localhost:5432/mydb"

# Initialize Slack client
slack_client = WebClient(token=SLACK_BOT_TOKEN)

# OpenAI Configuration
openai.api_key = OPENAI_API_KEY

# Database connection
def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

# Models for API requests
class Alert(BaseModel):
    source: str
    severity: str
    message: str

class Ticket(BaseModel):
    alert_id: int

# Route 1: Process incoming alerts
@app.post("/process_alert/")
def process_alert(alert: Alert):
    try:
        # Step 1: Classify severity using OpenAI GPT-4
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=f"Classify the severity of this alert: {alert.message}. Options: Critical, High, Medium, Low.",
            max_tokens=10,
        )
        severity_classification = response.choices[0].text.strip()

        # Step 2: Store alert in PostgreSQL database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO alerts (source, severity, message)
            VALUES (%s, %s, %s) RETURNING id;
            """,
            (alert.source, severity_classification, alert.message),
        )
        alert_id = cursor.fetchone()["id"]
        conn.commit()
        conn.close()

        # Step 3: Trigger JIRA ticket creation for High or Critical alerts
        if severity_classification in ["High", "Critical"]:
            create_ticket(alert_id)

        return {"alert_id": alert_id, "severity": severity_classification}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Route 2: Create JIRA ticket for an alert
@app.post("/create_ticket/")
def create_ticket(alert_id: int):
    try:
        # Fetch alert details from the database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alerts WHERE id = %s;", (alert_id,))
        alert = cursor.fetchone()
        conn.close()

        if not alert or alert["severity"] not in ["High", "Critical"]:
            raise HTTPException(status_code=400, detail="Alert not eligible for ticket creation.")

        # Create JIRA issue payload
        payload = {
            "fields": {
                "project": {"key": "SEC"},  # Replace 'SEC' with your JIRA project key
                "summary": f"Security Alert - {alert['severity']}",
                "description": f"Source: {alert['source']}\nMessage: {alert['message']}",
                "issuetype": {"name": "Task"},
            }
        }

        # Send request to JIRA API
        response = requests.post(JIRA_API_URL, json=payload, auth=JIRA_AUTH)
        response.raise_for_status()

        return {"jira_ticket_id": response.json()["key"]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Route 3: Provide automated response suggestions
@app.get("/automated_response/{alert_id}")
def automated_response(alert_id: int):
    try:
        # Fetch alert details from the database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alerts WHERE id = %s;", (alert_id,))
        alert = cursor.fetchone()
        conn.close()

        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found.")

        # Get response suggestion from OpenAI GPT-4
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=f"Provide a security incident response for the following alert:\nSource: {alert['source']}\nMessage: {alert['message']}",
            max_tokens=100,
        )
        
        recommendation = response.choices[0].text.strip()
        
        return {"response_recommendation": recommendation}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Route 4: Send Slack notifications for alerts
@app.post("/slack_alert/")
def slack_alert(alert_id: int):
    try:
        # Fetch alert details from the database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alerts WHERE id = %s;", (alert_id,))
        alert = cursor.fetchone()
        conn.close()

        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found.")

        # Format and send Slack message
        message = f"*Security Alert*\nSeverity: {alert['severity']}\nSource: {alert['source']}\nMessage: {alert['message']}"
        
        response = slack_client.chat_postMessage(channel="#security-alerts", text=message)
        
        return {"slack_message_ts": response["ts"]}

    except SlackApiError as e:
        raise HTTPException(status_code=500, detail=f"Slack API Error: {e.response['error']}")

# Route 5: Fetch stored alerts with optional filters
@app.get("/alerts/")
def fetch_alerts(severity: str = None, source: str = None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM alerts WHERE TRUE"
        
        if severity:
            query += f" AND severity ILIKE '{severity}'"
        
        if source:
            query += f" AND source ILIKE '{source}'"

        cursor.execute(query)
        
        alerts = cursor.fetchall()
        
        conn.close()

        return {"alerts": alerts}

    except Exception as e:
       raise HTTPException(status_code=500, detail=str(e))
