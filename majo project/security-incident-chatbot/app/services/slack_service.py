import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
from app.models import Alert

# Load environment variables
load_dotenv()

# Slack configuration
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")

# Initialize Slack client
slack_client = WebClient(token=SLACK_BOT_TOKEN)

async def send_slack_alert(alert: Alert):
    """
    Send security alert notification to Slack
    """
    # Define emoji based on severity
    severity_emoji = {
        "Critical": ":rotating_light:",
        "High": ":warning:",
        "Medium": ":warning:",
        "Low": ":information_source:"
    }
    
    emoji = severity_emoji.get(alert.severity, ":information_source:")
    
    # Create message blocks
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} Security Alert: {alert.severity} Severity",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Source:*\n{alert.source}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Alert ID:*\n{alert.id}"
                }
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Alert Message:*\n{alert.message}"
            }
        }
    ]
    
    # Add JIRA ticket reference if exists
    if alert.jira_ticket_id:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*JIRA Ticket:* <{os.getenv('JIRA_SERVER')}/browse/{alert.jira_ticket_id}|{alert.jira_ticket_id}>"
            }
        })
    
    # Add divider and timestamp
    blocks.extend([
        {
            "type": "divider"
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Alert created at {alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                }
            ]
        }
    ])
    
    try:
        # Send the message
        response = slack_client.chat_postMessage(
            channel=SLACK_CHANNEL_ID,
            text=f"Security Alert: {alert.severity} severity from {alert.source}",
            blocks=blocks
        )
        return True
    except SlackApiError as e:
        print(f"Error sending message to Slack: {e.response['error']}")
        return False