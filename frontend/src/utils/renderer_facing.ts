/**
 * Per-entity facing-direction state for the fish renderer.
 *
 * Tracks the *committed* left/right facing and a pending-flip counter so
 * that a direction change only takes effect after it has persisted for
 * FLIP_THROTTLE_FRAMES consecutive frames.  During that window the caller
 * receives `isTurning = true` and should show the front-view instead of
 * flipping the side-view sprite.
 *
 * Extracted from renderer.ts to keep that file within the god-class pin.
 */

// Minimum horizontal velocity magnitude before we consider a direction change.
export const MIN_FLIP_SPEED = 0.5;

// Frames a direction change must persist before we commit the flip (~500 ms at 30 FPS).
export const FLIP_THROTTLE_FRAMES = 15;

export interface FacingResult {
    facingLeft: boolean;
    isTurning: boolean;
}

interface PendingFlip {
    pendingLeft: boolean;
    frames: number;
}

/**
 * Stateful tracker for one scene's worth of entities.
 * Create one instance per Renderer; call `prune` each frame to prevent leaks.
 */
export class EntityFacingTracker {
    private facingLeft: Map<number, boolean> = new Map();
    private pendingFlip: Map<number, PendingFlip> = new Map();

    /**
     * Determine the stable facing direction for an entity, throttling rapid
     * flips.  Returns both the committed facing direction and a flag
     * indicating that the fish is mid-turn (front view should be shown).
     */
    getStableFacingLeft(entityId: number, velX?: number): FacingResult {
        const committedFacing = this.facingLeft.get(entityId) ?? false;

        if (velX === undefined || Math.abs(velX) < MIN_FLIP_SPEED) {
            // Speed too low — clear any pending flip, hold current facing
            this.pendingFlip.delete(entityId);
            return { facingLeft: committedFacing, isTurning: false };
        }

        const wantsLeft = velX < 0;

        if (wantsLeft === committedFacing) {
            // Same direction — cancel any pending flip
            this.pendingFlip.delete(entityId);
            return { facingLeft: committedFacing, isTurning: false };
        }

        // Direction has changed — increment the pending counter
        const pending = this.pendingFlip.get(entityId);
        if (!pending || pending.pendingLeft !== wantsLeft) {
            // Fresh direction change — start counting
            this.pendingFlip.set(entityId, { pendingLeft: wantsLeft, frames: 1 });
            return { facingLeft: committedFacing, isTurning: true };
        }

        pending.frames += 1;

        if (pending.frames >= FLIP_THROTTLE_FRAMES) {
            // Throttle window expired — commit the new direction
            this.pendingFlip.delete(entityId);
            this.facingLeft.set(entityId, wantsLeft);
            return { facingLeft: wantsLeft, isTurning: false };
        }

        // Still within throttle window — show front view
        return { facingLeft: committedFacing, isTurning: true };
    }

    /** Remove stale entries for entities that no longer exist. */
    prune(activeIds: Set<number>) {
        for (const id of this.facingLeft.keys()) {
            if (!activeIds.has(id)) this.facingLeft.delete(id);
        }
        for (const id of this.pendingFlip.keys()) {
            if (!activeIds.has(id)) this.pendingFlip.delete(id);
        }
    }

    /** Release all state (call on Renderer.dispose). */
    clear() {
        this.facingLeft.clear();
        this.pendingFlip.clear();
    }
}
