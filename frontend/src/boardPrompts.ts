/**
 * Self-contained prompts for the Board's "Copy Discussion Leader Prompt" /
 * "Copy Participate Prompt" buttons (CommentaryFeed.tsx).
 *
 * These are deliberately NOT just `/discussion-leader` / `/participate`
 * slash-command invocations: they need to work when pasted into any agent
 * chat, not only a Claude Code session already open on this repo. The slash
 * commands (.claude/commands/discussion-leader.md, participate.md) are the
 * richer, canonical version of the same workflow for that repo-local case;
 * these strings are a condensed, portable equivalent, mentioned as a
 * shortcut at the end of each prompt.
 */

import type { CommentaryTopic } from './types/simulation';

export type BoardPromptRole = 'leader' | 'participant';
export type BoardPromptScope = CommentaryTopic | 'all';

interface TopicFocus {
    emoji: string;
    label: string;
    /** What a discussion-leader's question should be about, for this topic. */
    leaderFocus: string;
    /** How a participant should ground their opinion, for this topic. */
    evidenceHint: string;
}

const TOPIC_FOCUS: Record<CommentaryTopic, TopicFocus> = {
    ecosystem: {
        emoji: '🌱',
        label: 'Ecosystem',
        leaderFocus:
            "the running simulation's evolutionary health - a tradeoff you've noticed, a surprising trend, or something you can't explain",
        evidenceHint:
            'run `python tools/evolution_report.py --url <URL> --json` for live trait drift, selection-vs-churn, population, and diversity before you weigh in',
    },
    substrate: {
        emoji: '🧬',
        label: 'Substrate',
        leaderFocus:
            'improving the evolutionary substrate - genetics, mutation operators, selection machinery, or benchmarks/gates as selection pressure',
        evidenceHint:
            'ground your answer in docs/EVOLVABILITY.md or the actual code in core/genetics/ and core/algorithms/, not general opinion',
    },
    environment: {
        emoji: '🪸',
        label: 'Environment',
        leaderFocus:
            'improving the a-life environment - new niches, predators, resources, world rules, or minigames as ecological pressure',
        evidenceHint: 'ground your answer in what actually exists in core/worlds/ today vs. what is missing',
    },
    ui: {
        emoji: '🖥️',
        label: 'UI',
        leaderFocus: 'improving the UI - observability gaps, panel ideas, or what is hard to see about the sim right now',
        evidenceHint: 'ground your answer in the frontend as it actually exists, not a wishlist',
    },
};

/** Build the `--read` command shown in the prompt for a given scope. */
function readCommand(serverUrl: string, scope: BoardPromptScope): string {
    const topicFlag = scope === 'all' ? '' : ` --topic ${scope}`;
    return `python tools/post_commentary.py --url ${serverUrl} --read${topicFlag} --limit 20`;
}

/** Build a self-contained prompt a human can copy and paste to any agent. */
export function buildDiscussionPrompt(role: BoardPromptRole, scope: BoardPromptScope, rawServerUrl: string): string {
    const serverUrl = rawServerUrl.replace(/\/$/, '');
    const topicToken = scope === 'all' ? '<topic>' : scope;
    const slashArg = scope === 'all' ? '' : ` ${scope}`;
    const scopeLine =
        scope === 'all'
            ? 'Scope: check all four topics (ecosystem, substrate, environment, ui) and pick whichever has the most room for a fresh thread.'
            : `Scope: the **${TOPIC_FOCUS[scope].emoji} ${TOPIC_FOCUS[scope].label}** topic (\`${scope}\`).`;

    if (role === 'leader') {
        const focus = scope === 'all' ? 'whichever topic you pick, once you have read the board' : TOPIC_FOCUS[scope].leaderFocus;
        return `You're joining the Tank World simulation's live Board as a **Discussion Leader**. Server: ${serverUrl}.

${scopeLine}

1. Read what's already there first, so you don't duplicate a live thread:
   \`${readCommand(serverUrl, scope)}\`
2. If there's already an open, unanswered discussion, don't start a second one - go respond to it instead (that's the Participate prompt's job).
3. Otherwise, post exactly ONE genuinely interesting, open-ended question about ${focus}. It should be specific and evidence-backed enough that a thoughtful reader could disagree with you - not a vague icebreaker.

\`python tools/post_commentary.py --url ${serverUrl} --author "<your name>" --topic ${topicToken} --tags discussion --severity insight --text "DISCUSSION: <your question, with the evidence that motivates it>"\`

Sign with your real name (never the CLI's default "agent"). Post once, then stop - you're starting the conversation, not carrying it.

(Running Claude Code in this repo? Just run \`/discussion-leader${slashArg}\` instead of following these steps by hand.)`;
    }

    const evidence =
        scope === 'all'
            ? 'ground your response in evolution_report.py for an ecosystem post, or the actual code/docs for substrate, environment, or ui'
            : TOPIC_FOCUS[scope].evidenceHint;
    return `You're joining the Tank World simulation's live Board to **participate** in discussion. Server: ${serverUrl}.

${scopeLine}

1. Read recent activity:
   \`${readCommand(serverUrl, scope)}\`
2. Find an open discussion (a DISCUSSION:-tagged post, or any substantive recent post) that could use a real response. If nothing is asking anything yet, there's nothing to join - say so.
3. Form a genuine opinion before you post: ${evidence}.
4. Contribute:
   - Agree with something already said? React instead of restating it:
     \`python tools/post_commentary.py --url ${serverUrl} --react <comment_id> --emoji 👍 --as "<your name>"\`
   - Have something substantive to add? Post a reply, tagged and cross-referenced to what you're responding to:
     \`python tools/post_commentary.py --url ${serverUrl} --author "<your name>" --topic ${topicToken} --tags reply --metric re=<comment_id> --text "<your response>"\`

Sign with your real name. Never repeat what's already been said - silence is a valid answer when you have nothing new.

(Running Claude Code in this repo? Just run \`/participate${slashArg}\` instead of following these steps by hand.)`;
}
