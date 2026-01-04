from core.ecosystem import EcosystemManager

m = EcosystemManager()
print("Poker summary keys:", list(m.get_poker_stats_summary().keys())[:10])
print("Total games:", m.get_poker_stats_summary().get("total_games"))
