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
  };

  // Food-specific
  food_type?: string;

  // Plant-specific
  plant_type?: number;
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
}

export interface StatsData {
  frame: number;
  population: number;
  generation: number;
  births: number;
  deaths: number;
  capacity: string;
  time: string;
  death_causes: Record<string, number>;
  fish_count: number;
  food_count: number;
  plant_count: number;
  poker_stats: PokerStatsData;
}

export interface SimulationUpdate {
  type: 'update';
  frame: number;
  elapsed_time: number;
  entities: EntityData[];
  stats: StatsData;
}

export interface Command {
  command: 'add_food' | 'pause' | 'resume' | 'reset';
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
