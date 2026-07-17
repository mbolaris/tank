import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { CommentaryFeed } from './CommentaryFeed';

describe('CommentaryFeed', () => {
    it('renders the Board intro before any comments load', () => {
        // useEffect (and thus the polling fetch) does not run under SSR, so this
        // exercises the static initial render without needing to mock fetch.
        const html = renderToString(<CommentaryFeed worldId="world-1" />);

        expect(html).toContain('Live observations posted by agents');
        expect(html).toContain('/observe-sim');
    });

    it('does not crash when worldId is undefined', () => {
        const html = renderToString(<CommentaryFeed worldId={undefined} />);
        expect(html).toContain('post_commentary.py');
    });

    it('renders topic filter chips', () => {
        const html = renderToString(<CommentaryFeed worldId="world-1" />);
        expect(html).toContain('All');
        expect(html).toContain('Ecosystem');
        expect(html).toContain('Substrate');
        expect(html).toContain('Environment');
        expect(html).toContain('UI');
    });

    it('renders discussion prompt copy buttons', () => {
        const html = renderToString(<CommentaryFeed worldId="world-1" />);
        expect(html).toContain('Copy Discussion Leader Prompt');
        expect(html).toContain('Copy Participate Prompt');
    });
});
