/**
 * Reusable StatRow component for consistent stat display
 */

import React from 'react';
import styles from './StatRow.module.css';

interface StatRowProps {
  label: string;
  value: string | number;
  valueColor?: string;
  valueStyle?: React.CSSProperties;
}

export function StatRow({ label, value, valueColor, valueStyle }: StatRowProps) {
  return (
    <div className={styles.row}>
      <span className={styles.label}>{label}</span>
      <span
        className={styles.value}
        style={{
          color: valueColor,
          ...valueStyle
        }}
      >
        {value}
      </span>
    </div>
  );
}
