from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Dict, Any, List, Optional
import calendar

from app.models.models import (
    ComplianceProfile, ComplianceTask, ComplianceHistory, ComplianceAlert,
    Client, User, ClientTimelineEvent
)

class ComplianceService:
    @staticmethod
    def generate_recurring_tasks(db: Session, profile: ComplianceProfile) -> List[ComplianceTask]:
        tasks = []
        now = datetime.utcnow()
        year = now.year

        if profile.frequency == "MONTHLY":
            # Generate tasks for the next 12 months
            for month in range(1, 13):
                # Calculate target year and month
                t_month = month
                t_year = year
                if t_month < now.month:
                    t_year = year + 1
                
                # Number of days in target month
                _, max_days = calendar.monthrange(t_year, t_month)
                due_day = min(profile.due_day or 20, max_days)
                due_date = datetime(t_year, t_month, due_day, 18, 30, 0) # 6:30 PM standard India cut-off

                task_name = f"File {profile.compliance_type} - {calendar.month_name[t_month]} {t_year}"
                
                # Check if duplicate exists
                exists = db.query(ComplianceTask).filter(
                    ComplianceTask.profile_id == profile.id,
                    ComplianceTask.task_name == task_name
                ).first()
                
                if not exists:
                    task = ComplianceTask(
                        organization_id=profile.organization_id,
                        client_id=profile.client_id,
                        profile_id=profile.id,
                        task_name=task_name,
                        due_date=due_date,
                        priority="MEDIUM",
                        status="PENDING",
                        notes=f"Recurring monthly filing for {profile.compliance_type}."
                    )
                    db.add(task)
                    tasks.append(task)

        elif profile.frequency == "QUARTERLY":
            # Generate tasks for next 4 quarters
            quarters = [
                ("Q1 (Apr-Jun)", datetime(year, 7, 31, 18, 30, 0)),
                ("Q2 (Jul-Sep)", datetime(year, 10, 31, 18, 30, 0)),
                ("Q3 (Oct-Dec)", datetime(year + 1 if now.month >= 11 else year, 1, 31, 18, 30, 0)),
                ("Q4 (Jan-Mar)", datetime(year + 1 if now.month >= 11 else year, 5, 31, 18, 30, 0))
            ]
            for q_label, due in quarters:
                # Adjust years if due dates are in the past
                due_date = due
                if due_date < now:
                    due_date = datetime(due_date.year + 1, due_date.month, due_date.day, 18, 30, 0)

                task_name = f"File {profile.compliance_type} - {q_label} {due_date.year}"
                
                exists = db.query(ComplianceTask).filter(
                    ComplianceTask.profile_id == profile.id,
                    ComplianceTask.task_name == task_name
                ).first()

                if not exists:
                    task = ComplianceTask(
                        organization_id=profile.organization_id,
                        client_id=profile.client_id,
                        profile_id=profile.id,
                        task_name=task_name,
                        due_date=due_date,
                        priority="HIGH",
                        status="PENDING",
                        notes=f"Recurring quarterly filing for {profile.compliance_type}."
                    )
                    db.add(task)
                    tasks.append(task)

        elif profile.frequency == "ANNUALLY":
            # Generate annual task
            due_month = 7 if "Income Tax" in profile.compliance_type else 10
            due_date = datetime(year, due_month, 31, 18, 30, 0)
            if due_date < now:
                due_date = datetime(year + 1, due_month, 31, 18, 30, 0)

            task_name = f"File Annual {profile.compliance_type} - FY {due_date.year - 1}-{str(due_date.year)[2:]}"
            
            exists = db.query(ComplianceTask).filter(
                ComplianceTask.profile_id == profile.id,
                ComplianceTask.task_name == task_name
            ).first()

            if not exists:
                task = ComplianceTask(
                    organization_id=profile.organization_id,
                    client_id=profile.client_id,
                    profile_id=profile.id,
                    task_name=task_name,
                    due_date=due_date,
                    priority="HIGH",
                    status="PENDING",
                    notes=f"Annual return filing for {profile.compliance_type}."
                )
                db.add(task)
                tasks.append(task)

        db.commit()
        return tasks

    @staticmethod
    def complete_task(
        db: Session, 
        task_id: str, 
        ack_num: Optional[str] = None, 
        notes: Optional[str] = None
    ) -> ComplianceTask:
        task = db.query(ComplianceTask).filter(ComplianceTask.id == task_id).first()
        if not task:
            raise ValueError("Compliance task not found")

        # Mark completed
        task.status = "COMPLETED"
        task.updated_at = datetime.utcnow()

        # Log timeline event
        timeline = ClientTimelineEvent(
            organization_id=task.organization_id,
            client_id=task.client_id,
            event_type="COMPLIANCE_FILED",
            title=f"Filed: {task.task_name}",
            description=f"Acknowledgement number: {ack_num or 'N/A'}"
        )
        db.add(timeline)

        # Log to ComplianceHistory
        now = datetime.utcnow()
        history_status = "ON_TIME" if now <= task.due_date else "LATE"
        hist = ComplianceHistory(
            organization_id=task.organization_id,
            client_id=task.client_id,
            task_id=task.id,
            filing_date=now,
            acknowledgement_number=ack_num,
            status=history_status,
            notes=notes
        )
        db.add(hist)

        # Trigger auto-rollover: if there are no pending tasks left for this profile, generate new ones!
        profile = db.query(ComplianceProfile).filter(ComplianceProfile.id == task.profile_id).first()
        if profile:
            pending_left = db.query(ComplianceTask).filter(
                ComplianceTask.profile_id == profile.id,
                ComplianceTask.status != "COMPLETED"
            ).count()
            if pending_left == 0:
                ComplianceService.generate_recurring_tasks(db, profile)

        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def compute_health_score(db: Session, client_id: str) -> tuple[str, float]:
        # 1. Total History filings
        history = db.query(ComplianceHistory).filter(ComplianceHistory.client_id == client_id).all()
        
        on_time_pct = 100.0
        if history:
            on_time_count = sum(1 for h in history if h.status == "ON_TIME")
            on_time_pct = (on_time_count / len(history)) * 100.0

        # 2. Overdue tasks
        now = datetime.utcnow()
        overdue_count = db.query(ComplianceTask).filter(
            ComplianceTask.client_id == client_id,
            ComplianceTask.status != "COMPLETED",
            ComplianceTask.due_date < now
        ).count()

        # baseline score
        score = on_time_pct
        score -= overdue_count * 10.0
        score = min(100.0, max(0.0, score))

        if score >= 80:
            classification = "Excellent"
        elif score >= 60:
            classification = "Good"
        elif score >= 40:
            classification = "Needs Attention"
        else:
            classification = "Critical"

        return classification, round(score, 1)

    @staticmethod
    def generate_daily_alerts(db: Session, org_id: str) -> List[ComplianceAlert]:
        now = datetime.utcnow()
        today_start = datetime(now.year, now.month, now.day)
        tomorrow_end = today_start + timedelta(days=2)

        # Retrieve all pending/in_progress tasks
        tasks = db.query(ComplianceTask).filter(
            ComplianceTask.organization_id == org_id,
            ComplianceTask.status != "COMPLETED"
        ).all()

        alerts = []
        for t in tasks:
            # 1. Check Overdue
            if t.due_date < now:
                msg = f"Filing return {t.task_name} is OVERDUE."
                alert_type = "OVERDUE"
            # 2. Check Due Today
            elif today_start <= t.due_date < (today_start + timedelta(days=1)):
                msg = f"Filing return {t.task_name} is due TODAY."
                alert_type = "DUE_TODAY"
            # 3. Check Due Tomorrow
            elif (today_start + timedelta(days=1)) <= t.due_date < tomorrow_end:
                msg = f"Filing return {t.task_name} is due TOMORROW."
                alert_type = "DUE_TOMORROW"
            else:
                continue

            # Check if active alert already exists to prevent duplicates
            exists = db.query(ComplianceAlert).filter(
                ComplianceAlert.task_id == t.id,
                ComplianceAlert.alert_type == alert_type,
                ComplianceAlert.is_resolved == False
            ).first()

            if not exists:
                alert = ComplianceAlert(
                    organization_id=t.organization_id,
                    client_id=t.client_id,
                    task_id=t.id,
                    alert_type=alert_type,
                    message=msg
                )
                db.add(alert)
                alerts.append(alert)

        db.commit()
        return alerts

    @staticmethod
    def get_dashboard_data(db: Session, org_id: str) -> Dict[str, Any]:
        # 1. Clean/generate alerts
        ComplianceService.generate_daily_alerts(db, org_id)

        # 2. Status counts
        total_completed = db.query(ComplianceTask).filter(
            ComplianceTask.organization_id == org_id,
            ComplianceTask.status == "COMPLETED"
        ).count()

        total_pending = db.query(ComplianceTask).filter(
            ComplianceTask.organization_id == org_id,
            ComplianceTask.status != "COMPLETED"
        ).count()

        now = datetime.utcnow()
        total_overdue = db.query(ComplianceTask).filter(
            ComplianceTask.organization_id == org_id,
            ComplianceTask.status != "COMPLETED",
            ComplianceTask.due_date < now
        ).count()

        # 3. On-time filing rate
        history = db.query(ComplianceHistory).filter(ComplianceHistory.organization_id == org_id).all()
        on_time_filing_pct = 100.0
        if history:
            on_time_count = sum(1 for h in history if h.status == "ON_TIME")
            on_time_filing_pct = (on_time_count / len(history)) * 100.0

        # Calculate average health score across clients
        clients = db.query(Client).filter(Client.organization_id == org_id, Client.deleted_at.is_(None)).all()
        total_health_val = 0.0
        for c in clients:
            _, val = ComplianceService.compute_health_score(db, c.id)
            total_health_val += val
        
        avg_health_val = (total_health_val / len(clients)) if clients else 100.0
        if avg_health_val >= 80:
            health_score = "Excellent"
        elif avg_health_val >= 60:
            health_score = "Good"
        elif avg_health_val >= 40:
            health_score = "Needs Attention"
        else:
            health_score = "Critical"

        # 4. Upcoming deadlines
        upcoming = db.query(ComplianceTask).filter(
            ComplianceTask.organization_id == org_id,
            ComplianceTask.status != "COMPLETED",
            ComplianceTask.due_date >= now
        ).order_by(ComplianceTask.due_date.asc()).limit(15).all()

        # 5. Alerts list
        alerts = db.query(ComplianceAlert).filter(
            ComplianceAlert.organization_id == org_id,
            ComplianceAlert.is_resolved == False
        ).order_by(desc(ComplianceAlert.created_at)).limit(15).all()

        return {
            "health_score": health_score,
            "health_score_value": round(avg_health_val, 1),
            "on_time_filing_percentage": round(on_time_filing_pct, 1),
            "total_returns_completed": total_completed,
            "total_returns_pending": total_pending,
            "total_returns_overdue": total_overdue,
            "upcoming_deadlines": upcoming,
            "recent_alerts": alerts
        }
