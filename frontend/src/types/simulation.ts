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
  food_type?: number;

  // Plant-specific
  plant_type?: number;
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
}

export interface SimulationUpdate {
  type: 'update';
  frame: number;
  entities: EntityData[];
  stats: StatsData;
}

export interface Command {
  command: 'add_food' | 'pause' | 'resume' | 'reset';
  data?: Record<string, any>;
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
