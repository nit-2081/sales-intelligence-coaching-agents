from src.shared.input_loader import InputLoader
from src.agents.ai_sales_coach.signal_extractor import SignalExtractor

loader = InputLoader()
calls = loader.load_all_calls()

extractor = SignalExtractor()
signals = extractor.extract(calls[0].text)

print("call:", calls[0].call_id)
print(signals.to_dict())
