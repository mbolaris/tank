
import { rendererRegistry } from '../rendering/registry';
import { TankSideRenderer } from './tank/TankSideRenderer';
import { TankTopDownRenderer } from './tank/TankTopDownRenderer';
import { PetriTopDownRenderer } from './petri/PetriTopDownRenderer';
import { SoccerTopDownRenderer } from './soccer/SoccerTopDownRenderer';

let initialized = false;

export function initRenderers() {
    if (initialized) return;
    initialized = true;

    rendererRegistry.register('tank', 'side', () => new TankSideRenderer());
    rendererRegistry.register('tank', 'topdown', () => new TankTopDownRenderer());
    rendererRegistry.register('petri', 'topdown', () => new PetriTopDownRenderer());
    rendererRegistry.register('soccer', 'topdown', () => new SoccerTopDownRenderer());

    console.debug('[Renderer] Registered default renderers');
}
