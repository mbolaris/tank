
import { rendererRegistry } from '../rendering/registry';
import { TankSideRenderer } from './tank/TankSideRenderer';
import { TankTopDownRenderer } from './tank/TankTopDownRenderer';

let initialized = false;

export function initRenderers() {
    if (initialized) return;
    initialized = true;

    rendererRegistry.register('tank', 'side', () => new TankSideRenderer());
    rendererRegistry.register('tank', 'topdown', () => new TankTopDownRenderer());

    console.debug('[Renderer] Registered default renderers');
}
