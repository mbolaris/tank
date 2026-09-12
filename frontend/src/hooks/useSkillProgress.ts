import { useEffect, useState } from 'react';
import type { SkillProgressResponse } from '../types/skillProgress';

/** The backend re-evaluates on a multi-minute cadence, so polling hard is waste. */
const POLL_INTERVAL_MS = 30_000;

export interface UseSkillProgressResult {
    domains: SkillProgressResponse['domains'];
    loading: boolean;
    error: string | null;
}

/**
 * Polls GET /api/world/{id}/skill/progress - one verdict per evolving domain.
 *
 * The verdict is computed server-side on purpose. It is a statistical claim
 * about a noisy series, and putting it in one tested Python function keeps the
 * UI from growing a second, subtly different opinion about what "progressing"
 * means.
 */
export function useSkillProgress(worldId?: string): UseSkillProgressResult {
    const [domains, setDomains] = useState<SkillProgressResponse['domains']>(undefined);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let cancelled = false;
        const path = worldId
            ? `/api/world/${encodeURIComponent(worldId)}/skill/progress`
            : '/api/skill/progress';

        const fetchProgress = async () => {
            try {
                const response = await fetch(path);
                if (!response.ok) throw new Error(`Skill progress returned ${response.status}`);
                const payload = (await response.json()) as SkillProgressResponse;
                if (cancelled) return;
                setDomains(payload.domains);
                setError(null);
            } catch (reason) {
                if (!cancelled) {
                    setError(reason instanceof Error ? reason.message : 'Skill progress unavailable');
                }
            } finally {
                if (!cancelled) setLoading(false);
            }
        };

        setLoading(true);
        fetchProgress();
        const interval = window.setInterval(fetchProgress, POLL_INTERVAL_MS);
        return () => {
            cancelled = true;
            window.clearInterval(interval);
        };
    }, [worldId]);

    return { domains, loading, error };
}
