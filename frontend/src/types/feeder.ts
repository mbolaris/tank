/** Live, non-persistent status exposed by a tank feeder. */
export interface FeederActivity {
    stock: number;
    capacity: number;
    resource_type: string;
    recent_activations: number;
    last_activation_frame: number | null;
}
