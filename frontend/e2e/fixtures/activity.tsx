import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { CommentaryFeed } from '../../src/components/CommentaryFeed';
import { LivingWorldToasts } from '../../src/components/LivingWorldToasts';
import { useCommentary } from '../../src/hooks/useCommentary';
import { useStoryEvents } from '../../src/hooks/useStoryEvents';
import { ControlPanel } from '../../src/components/ControlPanel';
import type { CommandResponse } from '../../src/types/simulation';

export function Consumers({ world }: { world: string }) {
    const commentary = useCommentary(world);
    const story = useStoryEvents(world);
    return <>
        <pre data-testid="commentary">{JSON.stringify(commentary)}</pre>
        <pre data-testid="story">{JSON.stringify(story)}</pre>
        <CommentaryFeed worldId={world} />
        <LivingWorldToasts worldId={world} onOpenBoard={() => {}} />
    </>;
}
export function Harness() {
    const [world, setWorld] = useState('A');
    const [mounted, setMounted] = useState(true);
    return <>
        <button onClick={() => setWorld('B')}>Switch to B</button>
        <button onClick={() => setMounted(false)}>Unmount consumers</button>
        {mounted && <Consumers world={world} />}
    </>;
}

export function PauseHarness() {
    const [paused, setPaused] = useState(false);
    const [connected, setConnected] = useState(true);
    const [world, setWorld] = useState('A');
    const send = () => new Promise<CommandResponse>((resolve, reject) => {
        Object.assign(window, { settlePause: resolve, failPause: reject });
    });
    return <>
        <button onClick={() => setPaused(true)}>Server paused</button>
        <button onClick={() => setConnected(false)}>Disconnect</button>
        <button onClick={() => { setWorld('B'); setConnected(true); }}>Switch pause world</button>
        <ControlPanel key={world} onCommand={() => {}} onPauseCommand={send} paused={paused} isConnected={connected} />
    </>;
}
createRoot(document.getElementById('root')!).render(location.search === '?pause' ? <PauseHarness /> : <Harness />);
