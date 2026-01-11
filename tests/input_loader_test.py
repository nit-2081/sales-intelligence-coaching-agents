from src.shared.input_loader import InputLoader

loader = InputLoader()
calls = loader.load_all_calls()

print("count:", len(calls))
for c in calls:
    print(c.call_id, "-", len(c.text), "chars")
