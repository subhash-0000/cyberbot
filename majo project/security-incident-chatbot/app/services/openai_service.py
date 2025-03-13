import os
from openai import AsyncOpenAI
from dotenv import load_dotenv
from typing import Dict, Any
from app.models import Alert

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def classify_alert_severity(message: str) -> str:
    """
    Use OpenAI to classify the severity of an alert
    Returns: "Critical", "High", "Medium", or "Low"
    """
    prompt = f"""
    As a security analyst, classify the following security alert message into one of these categories:
    - Critical: Immediate action required, potential breach in progress
    - High: Urgent action required, high risk of breach
    - Medium: Action recommended, moderate risk
    - Low: Routine alert, low risk
    
    Alert message: "{message}"
    
    Provide only the category name as response (Critical, High, Medium, or Low).
    """
    
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a security alert classifier that only responds with a single word severity level."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=10,
        temperature=0.3
    )
    
    severity = response.choices[0].message.content.strip()
    
    # Ensure we return one of the expected severity levels
    valid_severities = ["Critical", "High", "Medium", "Low"]
    if severity not in valid_severities:
        # Default to Medium if response doesn't match expected values
        return "Medium"
    
    return severity

async def generate_response_recommendation(alert: Alert) -> str:
    """
    Generate an automated incident response recommendation using OpenAI
    """
    prompt = f"""
    As a security incident response expert, provide a concise recommendation for responding to the following security alert:
    
    Severity: {alert.severity}
    Source: {alert.source}
    Alert Message: "{alert.message}"
    
    Provide a structured response with:
    1. Initial assessment
    2. Recommended immediate actions
    3. Follow-up steps
    """
    
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a security incident response expert providing actionable recommendations."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        temperature=0.7
    )
    
    return response.choices[0].message.content.strip()