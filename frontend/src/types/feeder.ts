/** Live, non-persistent status exposed by one feeding capability. */
export interface FeederActivity {
    stock_percent: number;
    resource_type: string;
    recent_activations: number;
    last_activation_frame: number | null;
}

/** An object's feeder activity, keyed by capability_id — an object can expose more than one. */
export type FeederActivityMap = Record<string, FeederActivity>;
