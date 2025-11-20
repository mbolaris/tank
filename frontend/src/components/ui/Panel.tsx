/**
 * Reusable Panel component for consistent styling across the app
 */

import React from 'react';
import styles from './Panel.module.css';

interface PanelProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export function Panel({ title, children, className = '' }: PanelProps) {
  return (
    <div className={`${styles.panel} ${className}`}>
      {title && <h2 className={styles.title}>{title}</h2>}
      {children}
    </div>
  );
}
