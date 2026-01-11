from src.agents.ai_sales_coach.feedback_logger import FeedbackLogger, FeedbackEvent

logger = FeedbackLogger()

event = FeedbackEvent(
    agent_name="ai_sales_coach",
    rep_id="rep_01",
    call_id="call_01",
    tips_shown=[
        "Tip 1...",
        "Tip 2...",
        "Tip 3..."
    ],
    action="helpful",
    notes="These were useful today."
)

logger.log(event)
print("logged 1 event")
