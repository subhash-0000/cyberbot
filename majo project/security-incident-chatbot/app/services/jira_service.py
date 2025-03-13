import os
from jira import JIRA
from dotenv import load_dotenv
from app.models import Alert

# Load environment variables
load_dotenv()

# JIRA configuration
JIRA_SERVER = os.getenv("JIRA_SERVER")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

def get_jira_client():
    """
    Create and return a JIRA client
    """
    return JIRA(
        server=JIRA_SERVER,
        basic_auth=(JIRA_USERNAME, JIRA_API_TOKEN)
    )

async def create_jira_ticket(alert: Alert) -> str:
    """
    Create a JIRA ticket for a high-severity security alert
    Returns the JIRA issue key
    """
    # Create JIRA client
    jira = get_jira_client()
    
    # Determine issue type based on severity
    issue_type = "Bug"
    if alert.severity == "Critical":
        issue_type = "Critical Bug"
    
    # Create issue
    issue_dict = {
        'project': {'key': JIRA_PROJECT_KEY},
        'summary': f"[{alert.severity}] Security Alert from {alert.source}",
        'description': f"""
        Security Alert Details:
        -----------------------
        Severity: {alert.severity}
        Source: {alert.source}
        Alert ID: {alert.id}
        Time: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
        
        Message:
        {alert.message}
        """,
        'issuetype': {'name': issue_type},
        'priority': {'name': get_jira_priority(alert.severity)},
        'labels': ['security-alert', alert.source.lower(), alert.severity.lower()]
    }
    
    new_issue = jira.create_issue(fields=issue_dict)
    
    return new_issue.key

def get_jira_priority(severity: str) -> str:
    """
    Map security alert severity to JIRA priority
    """
    priority_map = {
        "Critical": "Highest",
        "High": "High",
        "Medium": "Medium",
        "Low": "Low"
    }
    
    return priority_map.get(severity, "Medium")