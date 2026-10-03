/** An effect owns its requests; cleanup invalidates even transports that
 * ignore AbortSignal. Serial polling cannot rewind a cursor. */
export class ActivityRequests {
    private active = true;
    private pending = false;
    private controller = new AbortController();

    async run<T>(read: (signal: AbortSignal) => Promise<T>, accept: (value: T) => void, fail: (error: unknown) => void) {
        if (!this.active || this.pending) return;
        this.pending = true;
        try {
            const value = await read(this.controller.signal);
            if (this.active) accept(value);
        } catch (error) {
            if (this.active) fail(error);
        } finally {
            this.pending = false;
        }
    }

    close() {
        this.active = false;
        this.controller.abort();
    }
}
