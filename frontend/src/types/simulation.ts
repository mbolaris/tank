/**
 * TypeScript types for simulation data
 */

export interface FishGenomeData {
    speed: number;
    size: number;
    color_hue: number;
    // Visual traits for parametric fish templates
    template_id: number;
    fin_size: number;
    tail_size: number;
    body_aspect: number;
    eye_size: number;
    pattern_intensity: number;
    pattern_type: number;
}

/**
 * Plant genome data for L-system fractal rendering.
 */
export interface PlantGenomeData {
    axiom: string;
    angle: number;
    length_ratio: number;
    branch_probability: number;
    curve_factor: number;
    color_hue: number;
    color_saturation: number;
    stem_thickness: number;
    leaf_density: number;
    fractal_type?:
    | 'lsystem'
    | 'mandelbrot'
    | 'claude'
    | 'antigravity'
    | 'gpt'
    | 'gpt_codex'
    | 'sonnet'
    | 'gemini';
    aggression: number;
    bluff_frequency: number;
    risk_tolerance: number;
    base_energy_rate: number;
    growth_efficiency: number;
    nectar_threshold_ratio: number;
    fitness_score: number;
    production_rules: Array<{
        input: string;
        output: string;
        prob: number;
    }>;
}

export interface EntityData {
    id: number;
    type: 'fish' | 'food' | 'plant' | 'crab' | 'castle' | 'fractal_plant' | 'plant_nectar';
    x: number;
    y: number;
    width: number;
    height: number;

    // Velocity for animation
    vel_x?: number;
    vel_y?: number;

    // Fish-specific
    energy?: number;
    species?: 'solo' | 'algorithmic' | 'neural' | 'schooling';
    generation?: number;
    age?: number;
    genome_data?: FishGenomeData;
    poker_effect_state?: {
        status: 'playing' | 'won' | 'lost' | 'tie';
        amount: number;
        target_id?: number;
        target_type?: 'fish' | 'fractal_plant';
    };
    birth_effect_timer?: number;  // Frames remaining for birth visual effect

    // Food-specific
    food_type?: string;

    // Plant-specific (original static plants)
    plant_type?: number;

    // Fractal plant-specific
    genome?: PlantGenomeData;
    max_energy?: number;
    size_multiplier?: number;
    iterations?: number;
    nectar_ready?: boolean;

    // Plant nectar-specific
    source_plant_id?: number;
    source_plant_x?: number;
    source_plant_y?: number;
    // Floral genome for nectar rendering
    floral_type?: string;  // rose, mandelbrot, dahlia, sunflower, chrysanthemum
    floral_petals?: number;
    floral_layers?: number;
    floral_spin?: number;
    floral_hue?: number;
    floral_saturation?: number;

    // Crab-specific
    can_hunt?: boolean;  // True if crab can kill fish (not on cooldown)
}

export interface PokerEventData {
    frame: number;
    winner_id: number;  // -1 for tie
    loser_id: number;
    winner_hand: string;
    loser_hand: string;
    energy_transferred: number;
    message: string;
    is_plant?: boolean;  // True if this is a plant poker game
}

export interface PokerLeaderboardEntry {
    rank: number;
    fish_id: number;
    generation: number;
    algorithm: string;
    energy: number;
    age: number;
    total_games: number;
    wins: number;
    losses: number;
    ties: number;
    win_rate: number;  // Percentage (0-100)
    net_energy: number;
    roi: number;
    current_streak: number;
    best_streak: number;
    best_hand: string;
    best_hand_rank: number;
    showdown_win_rate: number;  // Percentage (0-100)
    fold_rate: number;  // Percentage (0-100)
    positional_advantage: number;  // Percentage (0-100)
    recent_win_rate: number;  // Recent win rate (0-100)
    skill_trend: string;  // "improving", "declining", or "stable"
}

export interface PokerStatsData {
    total_games: number;
    total_fish_games?: number;
    total_plant_games?: number;
    total_plant_energy_transferred?: number;
    total_wins: number;
    total_losses: number;
    total_ties: number;
    total_energy_won: number;
    total_energy_lost: number;
    net_energy: number;
    best_hand_rank: number;
    best_hand_name: string;
    total_house_cuts?: number;
    // Advanced metrics for evaluating poker skill
    win_rate?: number;
    win_rate_pct?: string;
    roi?: number;
    vpip?: number;
    vpip_pct?: string;
    bluff_success_rate?: number;
    bluff_success_pct?: string;
    button_win_rate?: number;
    button_win_rate_pct?: string;
    off_button_win_rate?: number;
    off_button_win_rate_pct?: string;
    positional_advantage?: number;
    positional_advantage_pct?: string;
    aggression_factor?: number;
    avg_hand_rank?: number;
    total_folds?: number;
    preflop_folds?: number;
    postflop_folds?: number;
    showdown_win_rate?: string;
    avg_fold_rate?: string;
}

export interface StatsData {
    frame: number;
    population: number;
    generation: number;
    max_generation: number;
    births: number;
    deaths: number;
    capacity: string;
    time: string;
    death_causes: Record<string, number>;
    fish_count: number;
    food_count: number;
    food_energy: number; // Total energy in regular food (pellets/nectar)
    live_food_count: number;  // Count of active LiveFood entities
    live_food_energy: number;  // Total energy in LiveFood
    plant_count: number;
    total_energy: number;
    fish_energy: number;  // Total energy of all fish
    plant_energy: number; // Total energy of all plants
    energy_sources: Record<string, number>;
    energy_sources_recent?: Record<string, number>;
    energy_from_nectar: number;
    energy_from_live_food: number;
    energy_from_falling_food: number;
    energy_from_poker: number;
    energy_from_poker_plant?: number;
    energy_from_auto_eval: number;
    energy_from_birth?: number;
    energy_from_soup_spawn?: number;
    energy_from_migration_in?: number;
    energy_burn_recent?: Record<string, number>;
    energy_burn_total?: number;
    // Energy delta (true change in fish population energy over window)
    energy_delta?: {
        energy_delta: number;  // Change in total fish energy
        energy_now: number;    // Current total fish energy
        energy_then: number;   // Total fish energy at window start
        fish_count_now: number;
        fish_count_then: number;
        avg_energy_delta: number;  // Change in average energy per fish
    };
    // Fish energy distribution
    avg_fish_energy: number;
    min_fish_energy: number;
    max_fish_energy: number;
    // Max Energy Capacity Stats (Genetic)
    min_max_energy_capacity: number;
    max_max_energy_capacity: number;
    median_max_energy_capacity: number;
    // Fish health status counts (by energy ratio)
    fish_health_critical: number;  // <15% energy
    fish_health_low: number;       // 15-30% energy
    fish_health_healthy: number;   // 30-80% energy
    fish_health_full: number;      // >80% energy
    poker_stats: PokerStatsData;
    total_sexual_births: number;
    total_asexual_births: number;
    fps?: number;
    fast_forward?: boolean;
}

export interface SimulationUpdate {
    type: 'update';
    tank_id?: string;  // Tank World Net identifier
    frame: number;
    elapsed_time: number;
    entities: EntityData[];
    stats: StatsData;
    poker_events: PokerEventData[];
    poker_leaderboard: PokerLeaderboardEntry[];
    auto_evaluation?: AutoEvaluateStats;
}

export interface DeltaUpdate {
    type: 'delta';
    tank_id?: string;  // Tank World Net identifier
    frame: number;
    elapsed_time: number;
    updates: Pick<EntityData, 'id' | 'x' | 'y' | 'vel_x' | 'vel_y' | 'poker_effect_state'>[];
    added: EntityData[];
    removed: number[];
    poker_events: PokerEventData[];
    stats?: StatsData;
}

export interface Command {
    command: 'add_food' | 'spawn_fish' | 'pause' | 'resume' | 'reset' | 'start_poker' | 'poker_process_ai_turn' | 'poker_action' | 'poker_new_round' | 'standard_poker_series' | 'poker_autopilot_action' | 'fast_forward';
    data?: Record<string, unknown>;
}

export interface CommandAck {
    type: 'ack';
    command: string;
    status: 'success' | 'error';
}

export interface ErrorMessage {
    type: 'error';
    message: string;
}

export type WebSocketMessage = SimulationUpdate | DeltaUpdate | CommandAck | ErrorMessage;

// Poker Game State
export interface PokerPlayer {
    player_id: string;
    name: string;
    balance: number;
    current_bet: number;
    is_folded: boolean;
    is_all_in: boolean;
    hand?: string[];
}

export interface PokerGamePlayer {
    player_id: string;
    name: string;
    energy: number;
    current_bet: number;
    total_bet: number;
    folded: boolean;
    is_human: boolean;
    fish_id?: number;
    generation?: number;
    algorithm?: string;
    genome_data?: FishGenomeData;
    hole_cards: string[];
    last_action?: string | null;
}

export interface PokerGameState {
    game_id: string;
    pot: number;
    current_round: string;
    community_cards: string[];
    current_player: string;
    is_your_turn: boolean;
    game_over: boolean;
    session_over: boolean;
    hands_played: number;
    message: string;
    winner: string | null;
    players: PokerGamePlayer[];
    your_cards: string[];
    call_amount: number;
    min_raise: number;
    last_move?: { player: string; action: string } | null;
}

// Auto-Evaluation Stats
export interface AutoEvaluatePlayerStats {
    player_id: string;
    name: string;
    is_standard: boolean;
    fish_id?: number;
    fish_generation?: number;
    plant_id?: number;
    species?: 'fish' | 'plant';
    energy: number;
    hands_won: number;
    hands_lost: number;
    total_energy_won: number;
    total_energy_lost: number;
    net_energy: number;
    win_rate: number;
}

export interface PokerPerformanceSnapshot {
    hand: number;
    players: {
        player_id: string;
        name: string;
        is_standard: boolean;
        species?: 'fish' | 'plant';
        energy: number;
        net_energy: number;
        hands_won?: number;
        hands_lost?: number;
        win_rate?: number;
    }[];
}

export interface AutoEvaluateStats {
    hands_played: number;
    hands_remaining: number;
    players: AutoEvaluatePlayerStats[];
    game_over: boolean;
    winner: string | null;
    reason: string;
    performance_history?: PokerPerformanceSnapshot[];
}

// Command Response Types
export interface CommandResponse {
    success: boolean;
    error?: string;
    state?: PokerGameState;
    stats?: AutoEvaluateStats;
    action_taken?: boolean;
}
