import { useEffect, useState } from 'react';
import type { SkillSnapshotsResponse } from '../types/skill';

export interface UseSkillSnapshotsResult {
    data: SkillSnapshotsResponse | null;
    loading: boolean;
    error: string | null;
}

export function useSkillSnapshots(worldId?: string, limit = 20): UseSkillSnapshotsResult {
    const [data, setData] = useState<SkillSnapshotsResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let cancelled = false;
        const path = worldId
            ? `/api/world/${encodeURIComponent(worldId)}/skill/snapshots`
            : '/api/skill/snapshots';
        const fetchSnapshots = async () => {
            try {
                const response = await fetch(`${path}?domain=soccer&limit=${limit}`);
                if (!response.ok) throw new Error(`Skill snapshots returned ${response.status}`);
                const payload = await response.json() as SkillSnapshotsResponse;
                if (!cancelled) {
                    setData(payload);
                    setError(null);
                }
            } catch (reason) {
                if (!cancelled) setError(reason instanceof Error ? reason.message : 'Skill snapshots unavailable');
            } finally {
                if (!cancelled) setLoading(false);
            }
        };
        setLoading(true);
        fetchSnapshots();
        const interval = window.setInterval(fetchSnapshots, 30000);
        return () => {
            cancelled = true;
            window.clearInterval(interval);
        };
    }, [limit, worldId]);

    return { data, loading, error };
}
