const RUNG_HUMAN_NAMES: Record<string, string> = {
    stationary_v1: 'Stationary',
    random_walk_v1: 'Random Walk',
    chase_shoot_v1: 'Chase-and-Shoot',
    formation_v1: 'Formation',
};

export function getRungHumanName(rungId: string, fallbackName?: string): string {
    if (RUNG_HUMAN_NAMES[rungId]) {
        return RUNG_HUMAN_NAMES[rungId];
    }
    if (fallbackName) {
        return fallbackName;
    }
    return rungId;
}
