import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { LivingWorldToasts } from './LivingWorldToasts';

describe('LivingWorldToasts', () => {
    it('renders nothing before any commentary has loaded (SSR: effects do not run)', () => {
        const html = renderToString(<LivingWorldToasts worldId="world-1" onOpenBoard={() => undefined} />);
        expect(html).toBe('');
    });

    it('does not crash when worldId is undefined', () => {
        const html = renderToString(<LivingWorldToasts worldId={undefined} onOpenBoard={() => undefined} />);
        expect(html).toBe('');
    });
});
