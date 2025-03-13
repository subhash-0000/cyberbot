from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List
from datetime import datetime
from app.models import Alert, AlertCreate

def create_alert(db: Session, alert: AlertCreate, severity: str) -> Alert:
    """
    Create a new alert in the database
    """
    db_alert = Alert(
        source=alert.source,
        severity=severity,
        message=alert.message
    )
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert

def get_alert_by_id(db: Session, alert_id: int) -> Optional[Alert]:
    """
    Get an alert by its ID
    """
    return db.query(Alert).filter(Alert.id == alert_id).first()

def get_alerts_by_filter(
    db: Session, 
    severity: Optional[str] = None,
    source: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Alert]:
    """
    Get alerts with optional filtering
    """
    query = db.query(Alert)
    
    # Apply filters if provided
    filters = []
    if severity:
        filters.append(Alert.severity == severity)
    if source:
        filters.append(Alert.source == source)
    if start_date:
        filters.append(Alert.created_at >= start_date)
    if end_date:
        filters.append(Alert.created_at <= end_date)
    
    if filters:
        query = query.filter(and_(*filters))
    
    return query.order_by(Alert.created_at.desc()).all()

def update_alert_jira_ticket(db: Session, alert_id: int, jira_ticket_id: str) -> Optional[Alert]:
    """
    Update an alert with JIRA ticket ID
    """
    alert = get_alert_by_id(db, alert_id)
    if alert:
        alert.jira_ticket_id = jira_ticket_id
        db.commit()
        db.refresh(alert)
    return alert