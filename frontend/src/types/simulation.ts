/**
 * TypeScript types for simulation data
 */

export interface EntityData {
  id: number;
  type: 'fish' | 'food' | 'plant' | 'crab' | 'castle';
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
  genome_data?: {
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
  };

  // Food-specific
  food_type?: string;

  // Plant-specific
  plant_type?: number;

}

export interface PokerEventData {
  frame: number;
  winner_id: number;  // -1 for tie, -2 for jellyfish
  loser_id: number;  // -2 for jellyfish
  winner_hand: string;
  loser_hand: string;
  energy_transferred: number;
  message: string;
  is_jellyfish?: boolean;
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
  plant_count: number;
  total_energy: number;
  poker_stats: PokerStatsData;
}

export interface SimulationUpdate {
  type: 'update';
  frame: number;
  elapsed_time: number;
  entities: EntityData[];
  stats: StatsData;
  poker_events: PokerEventData[];
  poker_leaderboard: PokerLeaderboardEntry[];
}

export interface Command {
  command: 'add_food' | 'spawn_fish' | 'pause' | 'resume' | 'reset' | 'start_poker' | 'poker_action' | 'standard_poker_series';
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

export type WebSocketMessage = SimulationUpdate | CommandAck | ErrorMessage;

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
  algorithm?: string;
  hole_cards: string[];
}

export interface PokerGameState {
  game_id: string;
  pot: number;
  current_round: string;
  community_cards: string[];
  current_player: string;
  is_your_turn: boolean;
  game_over: boolean;
  message: string;
  winner: string | null;
  players: PokerGamePlayer[];
  your_cards: string[];
  call_amount: number;
  min_raise: number;
}

// Auto-Evaluation Stats
export interface AutoEvaluatePlayerStats {
  player_id: string;
  name: string;
  is_standard: boolean;
  fish_id?: number;
  fish_generation?: number;
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
    energy: number;
    net_energy: number;
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
}
