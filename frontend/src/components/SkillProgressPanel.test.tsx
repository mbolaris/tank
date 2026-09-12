/**
 * The panel's contract at render time. Effects do not run under
 * `renderToString`, so this covers the states that must be right before any
 * fetch resolves, plus the presentation rules that keep a verdict readable.
 */

import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { SkillProgressPanel } from './SkillProgressPanel';

describe('SkillProgressPanel', () => {
    it('names itself before any data arrives, so the surface is not a blank box', () => {
        const html = renderToString(<SkillProgressPanel worldId="world-1" />);
        expect(html).toContain('Evolution progress');
    });

    it('says it is measuring rather than implying an answer it does not have', () => {
        const html = renderToString(<SkillProgressPanel worldId="world-1" />);
        expect(html).toContain('Measuring');
        // The worst possible default: a confident verdict nobody computed.
        expect(html).not.toContain('Stalled');
        expect(html).not.toContain('Progressing');
    });

    it('carries an accessible name for the region', () => {
        const html = renderToString(<SkillProgressPanel worldId="world-1" />);
        expect(html).toContain('aria-label="Evolution progress by skill domain"');
    });

    it('does not crash without a world id', () => {
        expect(() => renderToString(<SkillProgressPanel />)).not.toThrow();
    });
});
