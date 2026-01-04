from core.root_spots import RootSpotManager

mgr = RootSpotManager()
print("Root spot count:", len(mgr.spots))
print("First spot id:", mgr.spots[0].spot_id if mgr.spots else None)
print("Last spot id:", mgr.spots[-1].spot_id if mgr.spots else None)
