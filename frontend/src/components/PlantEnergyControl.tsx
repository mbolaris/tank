import { memo, type ChangeEvent } from 'react';
import { PlantIcon } from './ui';
import styles from './PlantEnergyControl.module.css';

interface PlantEnergyControlProps {
    value: number;
    onChange: (event: ChangeEvent<HTMLInputElement>) => void;
    isConnected: boolean;
}

export const PlantEnergyControl = memo(function PlantEnergyControl({ value, onChange, isConnected }: PlantEnergyControlProps) {
    return (
        <div className={styles.control}>
            <label htmlFor="plant-energy-input" className={styles.label}>
                <PlantIcon size={12} /> PLANT ENERGY
            </label>
            <input id="plant-energy-input" type="range" min="0" max="1" step="0.01"
                value={value} onChange={onChange} disabled={!isConnected} className={styles.slider} />
            <span className={styles.value}>{value.toFixed(2)}</span>
        </div>
    );
});
