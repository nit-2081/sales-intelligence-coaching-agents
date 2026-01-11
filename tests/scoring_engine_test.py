from src.shared.input_loader import InputLoader
from src.agents.ai_sales_coach.signal_extractor import SignalExtractor
from src.agents.ai_sales_coach.scoring_engine import ScoringEngine

loader = InputLoader()
call = loader.load_all_calls()[0]

signals = SignalExtractor().extract(call.text)
assessment = ScoringEngine().score(signals)

print("call:", call.call_id)
print("signals:", signals.to_dict())
print("assessment:", assessment.to_dict())
