import { renderToString } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

import { TankPokerTab } from './TankPokerTab';
import type { CommandResponse } from '../../types/simulation';

describe('TankPokerTab', () => {
    it('does not present a poker game as active before state exists', () => {
        const html = renderToString(
            <TankPokerTab
                worldId="world-1"
                isConnected={false}
                pokerLeaderboard={[]}
                pokerEvents={[]}
                pokerStats={undefined}
                currentFrame={0}
                sendCommandWithResponse={vi.fn<() => Promise<CommandResponse>>()}
                worldType="tank"
            />
        );

        expect(html).toContain('Sit Down &amp; Play');
        expect(html).not.toContain('Active Game');
        expect(html).not.toContain('Loading Poker Game');
    });
});
