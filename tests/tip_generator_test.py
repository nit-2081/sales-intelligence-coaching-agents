from src.shared.input_loader import InputLoader
from src.agents.ai_sales_coach.signal_extractor import SignalExtractor
from src.agents.ai_sales_coach.scoring_engine import ScoringEngine
from src.agents.ai_sales_coach.tip_generator import TipGenerator

call = InputLoader().load_all_calls()[0]
signals = SignalExtractor().extract(call.text)
assessment = ScoringEngine().score(signals)

tips = TipGenerator().generate(assessment, signals)

print("call:", call.call_id)
print("top_gaps:", assessment.top_gaps)
print("tips:")
for i, t in enumerate(tips.tips, 1):
    print(f"{i}. {t}")

