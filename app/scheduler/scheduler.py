import logging
from datetime import datetime, date, timedelta
from calendar import monthrange
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal, Base, engine
from app.services.market_data_service import MarketDataService
from app.services.indicator_service import IndicatorService
from app.services.ai_report_service import AIReportService
from app.services.git_service import GitService
from app.services.alert_service import AlertService
from app.repositories.report_repository import ReportRepository

logger = logging.getLogger(__name__)
ist_tz = timezone("Asia/Kolkata")

scheduler = BackgroundScheduler(timezone=ist_tz)

def run_daily_pipeline() -> bool:
    """Executes the daily market intelligence workflow."""
    today = date.today()
    logger.info(f"Starting daily pipeline for {today}...")
    # Ensure database schema is created
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        # Step 1: Fetch and store latest market data
        md_service = MarketDataService(db)
        logger.info("Daily Pipeline Step 1: Fetching market data...")
        md_results = md_service.fetch_and_store_all()
        logger.info(f"Market data fetched: {md_results}")

        # Step 2: Calculate and store indicators
        ind_service = IndicatorService(db)
        logger.info("Daily Pipeline Step 2: Calculating indicators...")
        ind_results = ind_service.calculate_and_store_all()
        logger.info(f"Indicators calculated: {ind_results}")

        # Step 3: Generate Market Summaries
        ai_service = AIReportService(db)
        logger.info("Daily Pipeline Step 3: Generating summaries...")
        summaries = ai_service.get_all_summaries()
        logger.info("Summaries generated successfully.")

        # Step 4: Generate AI Report
        logger.info("Daily Pipeline Step 4: Generating AI report via Groq...")
        report_content = ai_service.generate_daily_report(today)

        # Step 5: Store Report locally on disk and index in database
        logger.info("Daily Pipeline Step 5: Storing report...")
        git_service = GitService()
        file_path = git_service.save_report_to_disk(today, report_content)
        
        report_repo = ReportRepository(db)
        rel_path = file_path.relative_to(git_service.workspace_root).as_posix()
        report_repo.save_or_update(today, rel_path)

        # Step 6: GitHub automation (commit & push)
        logger.info("Daily Pipeline Step 6: Pushing to GitHub...")
        git_success = git_service.commit_and_push_report(today, file_path)
        logger.info(f"Git push success: {git_success}")

        # Step 7: Send Alerts (Telegram & Email)
        logger.info("Daily Pipeline Step 7: Dispatching alerts...")
        alert_service = AlertService()
        
        # Build a nice condensed summary for Telegram
        telegram_intro = f"*Market Summary - {today}*\n\n"
        telegram_body = "\n".join([f"• {val}" for val in summaries.values() if "No complete data" not in val])
        if not telegram_body:
            telegram_body = "Daily data collection complete, but no asset indicators were computed."
        alert_service.send_telegram_alert(telegram_intro + telegram_body)
        
        # Email the PDF report
        alert_service.send_email_report(today, report_content)

        logger.info(f"Daily pipeline completed successfully for {today}!")
        return True

    except Exception as e:
        logger.error(f"Error in daily pipeline: {e}", exc_info=True)
        return False
    finally:
        db.close()

def run_weekly_pipeline() -> bool:
    """Executes the weekly analysis workflow on Sunday evenings."""
    today = date.today()
    logger.info(f"Starting weekly pipeline for {today}...")
    # Ensure database schema is created
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        # For weekly, we generate a report summing up past week's indicators
        # In a real system, we'd prompt the LLM with the week's data points
        # For the portfolio demo, we generate a weekly summary using the AI service
        ai_service = AIReportService(db)
        logger.info("Weekly Pipeline: Generating Weekly AI Report...")
        
        prompt = f"""
You are a senior financial analyst. Generate a Weekly Market Intelligence Summary for the week ending {today}.
Summarize the macro trends, key support/resistance levels tested during the week, and top trading opportunities for next week.
Focus on: NIFTY, BANKNIFTY, Gold, Silver, Bitcoin, and Ethereum.
Provide a clean Markdown output with sections:
1. Weekly Executive Summary
2. Key Market Movers
3. Technical Highlights
4. Risk Management & Outlook
"""
        # Call Groq or program mock
        report_content = ""
        if settings.groq_key:
            client = Groq(api_key=settings.groq_key)
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}]
            )
            report_content = completion.choices[0].message.content
        else:
            report_content = f"# Weekly Market Summary - Week Ending {today}\n\n*This is a fallback weekly report placeholder demonstrating the Sunday 8 PM IST execution.*"

        # Save to disk in reports/weekly/YYYY-MM-DD.md
        git_service = GitService()
        weekly_dir = git_service.workspace_root / "reports" / "weekly"
        weekly_dir.mkdir(parents=True, exist_ok=True)
        file_path = weekly_dir / f"weekly_{today}.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(report_content)
            
        logger.info(f"Weekly report saved to {file_path}")
        
        # Commit to Git
        git_service.commit_and_push_report(today, file_path)

        # Notify Telegram
        alert_service = AlertService()
        alert_service.send_telegram_alert(f"📢 *Weekly Market Summary Ready!*\nDate: {today}\nWeekly summary PDF sent to email.")
        alert_service.send_email_report(today, report_content)

        logger.info("Weekly pipeline completed.")
        return True
    except Exception as e:
        logger.error(f"Error in weekly pipeline: {e}", exc_info=True)
        return False
    finally:
        db.close()

def run_monthly_pipeline() -> bool:
    """Executes the monthly summary workflow on the last day of the month."""
    today = date.today()
    logger.info(f"Starting monthly pipeline for {today}...")
    # Ensure database schema is created
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        # Verify if today is actually the last day of the month
        # In manual triggers this check might be skipped, but for scheduled trigger it is ideal
        year, month = today.year, today.month
        last_day = monthrange(year, month)[1]
        
        # If running via scheduled cron we only execute on the last day
        logger.info(f"Monthly Pipeline: Generating Monthly AI Report for {today}...")
        
        prompt = f"""
You are a senior financial analyst. Generate a Monthly Market Intelligence Summary for {today.strftime('%B %Y')}.
Summarize the monthly performance, changes in 200-day moving average structures, commodity safe-haven flows, and crypto trends.
Provide a clean Markdown output with sections:
1. Monthly Market Overview
2. Asset Class Performance Breakdowns
3. Macro Trends Analysis
4. Strategic Opportunities
"""
        report_content = ""
        if settings.groq_key:
            client = Groq(api_key=settings.groq_key)
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}]
            )
            report_content = completion.choices[0].message.content
        else:
            report_content = f"# Monthly Market Summary - {today.strftime('%B %Y')}\n\n*This is a fallback monthly report placeholder demonstrating the last day of month execution.*"

        # Save to disk in reports/monthly/YYYY-MM.md
        git_service = GitService()
        monthly_dir = git_service.workspace_root / "reports" / "monthly"
        monthly_dir.mkdir(parents=True, exist_ok=True)
        file_path = monthly_dir / f"monthly_{today.strftime('%Y_%m')}.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(report_content)
            
        logger.info(f"Monthly report saved to {file_path}")
        
        # Commit to Git
        git_service.commit_and_push_report(today, file_path)

        # Alerts
        alert_service = AlertService()
        alert_service.send_telegram_alert(f"📊 *Monthly Market Review Ready!*\nMonth: {today.strftime('%B %Y')}\nPDF copy sent to email.")
        alert_service.send_email_report(today, report_content)

        logger.info("Monthly pipeline completed.")
        return True
    except Exception as e:
        logger.error(f"Error in monthly pipeline: {e}", exc_info=True)
        return False
    finally:
        db.close()

def start_scheduler():
    """Starts the APScheduler background jobs."""
    if not scheduler.running:
        # 1. Daily report at 7:00 PM IST (19:00)
        scheduler.add_job(
            run_daily_pipeline,
            trigger=CronTrigger(hour=19, minute=0, second=0, timezone=ist_tz),
            id="daily_market_report",
            name="Daily Market Intelligence Report Pipeline",
            replace_existing=True
        )
        
        # 2. Weekly report every Sunday at 8:00 PM IST (20:00)
        scheduler.add_job(
            run_weekly_pipeline,
            trigger=CronTrigger(day_of_week="sun", hour=20, minute=0, second=0, timezone=ist_tz),
            id="weekly_market_report",
            name="Weekly Market Summary Pipeline",
            replace_existing=True
        )

        # 3. Monthly report on the last day of the month at 8:00 PM IST (20:00)
        # Note: 'last' day is expressed as 'last' in day expression or calculated programmatically.
        # CronTrigger doesn't have a direct 'last' keyword in standard python trigger,
        # so we schedule a check every day at 8:00 PM IST, and in the task we verify if today is the last day.
        # Alternatively, run on day 28-31 and check. A clean way is to run a wrapper daily at 20:00:
        def monthly_check_wrapper():
            today = date.today()
            year, month = today.year, today.month
            last_day = monthrange(year, month)[1]
            if today.day == last_day:
                run_monthly_pipeline()
            else:
                logger.debug(f"Monthly check: Today ({today}) is not the last day of the month ({last_day}). Skipping.")

        scheduler.add_job(
            monthly_check_wrapper,
            trigger=CronTrigger(hour=20, minute=0, second=0, timezone=ist_tz),
            id="monthly_market_report_check",
            name="Monthly Market Summary Daily Check Pipeline",
            replace_existing=True
        )

        scheduler.start()
        logger.info("APScheduler background jobs started successfully.")

def shutdown_scheduler():
    """Stops the APScheduler background jobs."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler background jobs stopped.")
