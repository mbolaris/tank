import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { ControlPanel } from './ControlPanel';

describe('ControlPanel groups', () => {
    it('names the control groups and keeps reset under closed Advanced options', () => {
        const html = renderToString(<ControlPanel onCommand={() => {}} isConnected />);
        expect(html).toContain('role="group" aria-label="World actions"');
        expect(html).toContain('role="group" aria-label="Simulation"');
        expect(html).toContain('role="group" aria-label="View"');
        expect(html).toMatch(/<details[^>]*><summary>Advanced<\/summary>/);
        expect(html).toContain('Reset world');
        expect(html).not.toContain('<details open');
    });

    it('accepts world view and plant energy controls in their corresponding groups', () => {
        const html = renderToString(<ControlPanel onCommand={() => {}} isConnected
            viewOptions={<span>World view selector</span>}
            advancedOptions={<label>Plant energy setting</label>} />);
        expect(html).toContain('World view selector');
        expect(html).toMatch(/<details[\s\S]*Plant energy setting[\s\S]*Reset world/);
    });

    it('keeps simulation-changing buttons disabled while disconnected', () => {
        const html = renderToString(<ControlPanel onCommand={() => {}} isConnected={false} />);
        expect((html.match(/disabled=""/g) ?? []).length).toBe(5);
    });
});
