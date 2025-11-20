export function getEnergyColor(totalEnergy: number): string {
  if (totalEnergy < 2000) {
    return '#ef4444'; // Red - Critical/Starvation (double food spawn)
  } else if (totalEnergy < 4000) {
    return '#4ade80'; // Green - Normal (normal food spawn)
  } else if (totalEnergy < 6000) {
    return '#fbbf24'; // Yellow - High (reduced food spawn)
  } else {
    return '#fb923c'; // Orange - Very High (very reduced food spawn)
  }
}
