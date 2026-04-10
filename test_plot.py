import matplotlib
matplotlib.use('Agg')  # use non-interactive backend for testing
import matplotlib.pyplot as plt
from geoafrica import boundaries, viz

print("Fetching Nigeria...")
nigeria = boundaries.get_country("Nigeria")
print(nigeria.head())

nigeria.plot(color='lightgreen', edgecolor='black', figsize=(6, 6))
plt.title("Nigeria - Country Outline")
plt.savefig("test_nigeria.png")
print("Saved Nigeria static map.")

print("Fetching States...")
states = boundaries.get_admin("Nigeria", level=1)
print(states.head(3))

states.plot(cmap='Set3', edgecolor='black', figsize=(8, 8))
plt.title("Nigeria - State Boundaries")
plt.savefig("test_states.png")
print("Saved States static map.")

print("Creating interactive map...")
interactive_map = viz.quick_map(states)
interactive_map.save("test_map.html")
print("Saved interactive map.")

print("Tests passed.")
