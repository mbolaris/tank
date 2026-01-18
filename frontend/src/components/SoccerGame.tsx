import React, { useState, useEffect } from 'react';
import { SoccerPitch } from './SoccerPitch';
import { Button } from './ui';
import type { Command, SoccerMatchState } from '../types/simulation';

interface SoccerGameProps {
    sendCommandWithResponse: (command: Command) => Promise<SoccerCommandResponse>;
}

interface SoccerCommandResponse {
    success: boolean;
    state?: SoccerMatchState;
    error?: string;
}

export const SoccerGame: React.FC<SoccerGameProps> = ({ sendCommandWithResponse }) => {
    const [gameState, setGameState] = useState<SoccerMatchState | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isPlaying, setIsPlaying] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleStartMatch = async (numPlayers: number) => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await sendCommandWithResponse({
                command: 'start_soccer',
                data: { num_players: numPlayers }
            });
            if (response.success) {
                setGameState(response.state);
                setIsPlaying(true);
            } else {
                setError(response.error || "Failed to start match");
            }
        } catch (e) {
            setError("Start error: " + String(e));
        } finally {
            setIsLoading(false);
        }
    };

    const handleEndMatch = async () => {
        try {
            await sendCommandWithResponse({ command: 'end_soccer', data: {} });
        } catch (e) {
            console.error("End error", e);
        }
        setIsPlaying(false);
        setGameState(null);
    };

    useEffect(() => {
        if (!isPlaying || !gameState || gameState.game_over) return;

        let active = true;
        const step = async () => {
            if (!active) return;
            try {
                const response = await sendCommandWithResponse({ command: 'soccer_step', data: {} });
                if (response.success && active) {
                    setGameState(response.state);
                }
            } catch (e) {
                console.error("Step error", e);
            }
        };

        // Run step loop at 10 FPS
        const timer = setInterval(step, 100);
        return () => {
            active = false;
            clearInterval(timer);
        };
    }, [isPlaying, gameState, sendCommandWithResponse]);

    if (!isPlaying) {
        return (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '16px' }}>
                <div style={{ marginBottom: '16px', color: '#e5e7eb', fontSize: '1.125rem', fontWeight: 600 }}>Start Match</div>
                {error && <div style={{ color: '#ef4444', marginBottom: '8px' }}>{error}</div>}

                <div style={{ display: 'flex', gap: '16px' }}>
                    <Button
                        onClick={() => handleStartMatch(22)}
                        disabled={isLoading}
                        variant="primary"
                        style={{ padding: '8px 16px' }}
                    >
                        {isLoading ? 'Starting...' : 'Start 11 vs 11'}
                    </Button>
                    <Button
                        onClick={() => handleStartMatch(10)}
                        disabled={isLoading}
                        variant="secondary"
                        style={{ padding: '8px 16px' }}
                    >
                        {isLoading ? 'Starting...' : 'Start 5 vs 5'}
                    </Button>
                </div>
            </div>
        );
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%' }}>
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                width: '100%',
                maxWidth: '800px',
                marginBottom: '8px',
                padding: '0 16px',
                fontSize: '0.875rem'
            }}>
                <div style={{ color: '#60a5fa', fontWeight: 700, fontSize: '1.25rem' }}>
                    {gameState?.score?.left ?? 0}
                </div>
                <div style={{ color: '#d1d5db' }}>
                    {gameState?.message || "Match in Progress"}
                    {gameState?.game_over && " (Game Over)"}
                </div>
                <div style={{ color: '#f87171', fontWeight: 700, fontSize: '1.25rem' }}>
                    {gameState?.score?.right ?? 0}
                </div>
            </div>

            <SoccerPitch gameState={gameState} width={800} height={450} />

            <div style={{ marginTop: '16px', display: 'flex', gap: '16px' }}>
                <Button
                    onClick={handleEndMatch}
                    variant="danger"
                    style={{ padding: '8px 16px' }}
                >
                    End Match
                </Button>
            </div>
        </div>
    );
};
