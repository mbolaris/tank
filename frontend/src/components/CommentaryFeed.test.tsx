import { renderToString } from 'react-dom/server';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const feed = vi.hoisted(() => ({
    comments: { comments: [], setComments: vi.fn(), loaded: false, error: null as string | null },
    events: { events: [], loaded: false, error: null as string | null },
}));
vi.mock('../hooks/useCommentary', () => ({ useCommentary: () => feed.comments }));
vi.mock('../hooks/useStoryEvents', () => ({ useStoryEvents: () => feed.events }));

import { CommentaryFeed } from './CommentaryFeed';

describe('CommentaryFeed', () => {
    beforeEach(() => {
        vi.unstubAllGlobals();
        feed.comments.loaded = false;
        feed.comments.error = null;
        feed.events.loaded = false;
        feed.events.error = null;
    });

    it('renders the Board intro before any comments load', () => {
        // useEffect (and thus the polling fetch) does not run under SSR, so this
        // exercises the static initial render without needing to mock fetch.
        const html = renderToString(<CommentaryFeed worldId="world-1" />);

        expect(html).toContain('World events and observations from this tank');
        expect(html).toContain('Loading tank activity');
        expect(html).not.toContain('Watch the tank.');
    });

    it('does not crash when worldId is undefined', () => {
        const html = renderToString(<CommentaryFeed worldId={undefined} />);
        expect(html).toContain('Invite an agent');
    });

    it('renders topic filter chips', () => {
        const html = renderToString(<CommentaryFeed worldId="world-1" />);
        expect(html).toContain('All');
        expect(html).toContain('Ecosystem');
        expect(html).toContain('Substrate');
        expect(html).toContain('Environment');
        expect(html).toContain('UI');
    });

    it('offers a World events filter alongside the conversation topics (U7)', () => {
        // Story events are measurements, not a conversation, so they get their
        // own chip rather than being folded into a topic.
        const html = renderToString(<CommentaryFeed worldId="world-1" />);
        expect(html).toContain('World events');
    });

    it('renders discussion prompt copy buttons', () => {
        const html = renderToString(<CommentaryFeed worldId="world-1" />);
        expect(html).toContain('Copy Discussion Leader Prompt');
        expect(html).toContain('Copy Participate Prompt');
        expect(html).toMatch(/<details[^>]*><summary>Invite an agent/);
        expect(html).not.toContain('<details open');
    });

    it('invites observation only after both sources finish loading', () => {
        feed.comments.loaded = true;
        let html = renderToString(<CommentaryFeed worldId="world-1" />);
        expect(html).not.toContain('Watch the tank.');
        feed.events.loaded = true;
        html = renderToString(<CommentaryFeed worldId="world-1" />);
        expect(html).toContain('Watch the tank. World events and observations will appear here.');
        expect(html).not.toContain('post_commentary.py');
    });

    it('does not describe a failed world-event request as an empty tank', () => {
        feed.comments.loaded = feed.events.loaded = true;
        feed.events.error = 'HTTP 503';
        const html = renderToString(<CommentaryFeed worldId="world-1" />);
        expect(html).toContain('Could not load world events:');
        expect(html).toContain('HTTP 503');
        expect(html).not.toContain('Watch the tank.');
    });

    it('explains an empty topic filter and offers a way back to all activity', () => {
        feed.comments.loaded = feed.events.loaded = true;
        vi.stubGlobal('localStorage', { getItem: (key: string) => key === 'tank.boardTopicFilter' ? 'ecosystem' : null });
        const html = renderToString(<CommentaryFeed worldId="world-1" />);
        expect(html).toContain('No observations in Ecosystem yet.');
        expect(html).toContain('Show all activity');
        expect(html).toContain('aria-pressed="true"');
    });
});
