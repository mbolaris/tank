import { describe, expect, it, vi } from 'vitest';
import { ActivityRequests } from './activityRequests';

function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (error: Error) => void;
    const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
    return { promise, resolve, reject };
}

describe('world-owned activity requests', () => {
    it('accepts B then ignores A even if the transport ignores cancellation', async () => {
        const a = new ActivityRequests();
        const b = new ActivityRequests();
        const old = deferred<string>();
        const current = deferred<string>();
        const accept = vi.fn();
        const fail = vi.fn();
        const first = a.run(() => old.promise, accept, fail);
        a.close();
        const second = b.run(() => current.promise, accept, fail);
        current.resolve('B'); await second;
        old.resolve('A'); await first;
        expect(accept.mock.calls).toEqual([['B']]);
        expect(fail).not.toHaveBeenCalled();
    });
    it('prevents overlapping polls and recovers after a failure', async () => {
        const requests = new ActivityRequests();
        const old = deferred<string>();
        const accept = vi.fn(); const fail = vi.fn(); const read = vi.fn(() => old.promise);
        const first = requests.run(read, accept, fail);
        await requests.run(read, accept, fail);
        expect(read).toHaveBeenCalledTimes(1);
        old.reject(new Error('offline')); await first;
        await requests.run(async () => 'recovered', accept, fail);
        expect(fail).toHaveBeenCalledTimes(1);
        expect(accept).toHaveBeenCalledWith('recovered');
    });
    it('aborts on unmount and suppresses late errors', async () => {
        const requests = new ActivityRequests(); const old = deferred<string>();
        const fail = vi.fn(); const accept = vi.fn(); let signal!: AbortSignal;
        const first = requests.run(s => { signal = s; return old.promise; }, accept, fail);
        requests.close(); expect(signal.aborted).toBe(true);
        old.reject(new Error('late')); await first;
        expect(fail).not.toHaveBeenCalled(); expect(accept).not.toHaveBeenCalled();
    });
});
