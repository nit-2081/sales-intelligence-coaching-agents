# tests/kill_switch_test.py
from src.shared.kill_switch import KillSwitch

ks = KillSwitch()
print(ks.is_disabled("ai_sales_coach"))
print(ks.is_disabled("retention_agent"))