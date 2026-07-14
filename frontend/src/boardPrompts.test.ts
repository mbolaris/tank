import { describe, expect, it } from 'vitest';

import { buildDiscussionPrompt } from './boardPrompts';
import type { CommentaryTopic } from './types/simulation';

const URL = 'http://127.0.0.1:8000';
const TOPICS: CommentaryTopic[] = ['ecosystem', 'substrate', 'environment', 'ui'];

describe('buildDiscussionPrompt', () => {
    it('leader prompt scopes the read/post commands to the given topic', () => {
        const text = buildDiscussionPrompt('leader', 'ecosystem', URL);
        expect(text).toContain('Discussion Leader');
        expect(text).toContain('--read --topic ecosystem --limit 20');
        expect(text).toContain('--topic ecosystem --tags discussion');
        expect(text).toContain('DISCUSSION:');
        expect(text).toContain('/discussion-leader ecosystem');
    });

    it('participant prompt references reply tagging and cross-referencing', () => {
        const text = buildDiscussionPrompt('participant', 'substrate', URL);
        expect(text).toContain('participate');
        expect(text).toContain('--read --topic substrate --limit 20');
        expect(text).toContain('--topic substrate --tags reply --metric re=<comment_id>');
        expect(text).toContain('--react <comment_id> --emoji');
        expect(text).toContain('/participate substrate');
    });

    it('"all" scope omits a --topic filter on read and uses a placeholder on post', () => {
        const leaderText = buildDiscussionPrompt('leader', 'all', URL);
        expect(leaderText).toContain('--read --limit 20');
        expect(leaderText).not.toContain('--read --topic');
        expect(leaderText).toContain('--topic <topic> --tags discussion');
        expect(leaderText).toContain('/discussion-leader');
        expect(leaderText).not.toContain('/discussion-leader ');

        const participantText = buildDiscussionPrompt('participant', 'all', URL);
        expect(participantText).toContain('--topic <topic> --tags reply');
    });

    it('trims a trailing slash from the server URL', () => {
        const text = buildDiscussionPrompt('leader', 'ecosystem', 'http://127.0.0.1:8000/');
        expect(text).toContain('--url http://127.0.0.1:8000 ');
        expect(text).not.toContain('8000/');
    });

    it('covers every topic without crashing and names it', () => {
        for (const topic of TOPICS) {
            const leaderText = buildDiscussionPrompt('leader', topic, URL);
            const participantText = buildDiscussionPrompt('participant', topic, URL);
            expect(leaderText).toContain(`\`${topic}\``);
            expect(participantText).toContain(`\`${topic}\``);
        }
    });
});
