import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { EnergyEconomyPanel } from './EnergyEconomyPanel';

const flows = {
    fallingFood: 100, liveFood: 0, plantNectar: 0, soupSpawn: 0, migrationIn: 0,
    autoEval: 0, baseMetabolism: 40, traitMaintenance: 0, movementCost: 0,
    turningCost: 0, fishDeaths: 0, migrationOut: 0, overflowFood: 0,
    overflowReproduction: 0, reproductionCost: 200, birthEnergy: 150,
    pokerTotalPot: 0, pokerHouseCut: 0, plantPokerNet: 0, energyDelta: 80,
};

describe('EnergyEconomyPanel explanation', () => {
    it('distinguishes measured change from the flow ledger and internal transfers', () => {
        const html = renderToString(<EnergyEconomyPanel data={flows} />).replace(/<!-- -->/g, '');
        expect(html).toContain('Why can the energy totals differ?');
        expect(html).toContain('Internal transfers');
        expect(html).toContain('Ledger net: +60');
        expect(html).toContain('Measured minus ledger: +20');
    });

    it('preserves the sign of a negative measured-minus-ledger difference', () => {
        const html = renderToString(<EnergyEconomyPanel data={{ ...flows, energyDelta: 10 }} />).replace(/<!-- -->/g, '');
        expect(html).toContain('Measured minus ledger: -50');
    });
});
