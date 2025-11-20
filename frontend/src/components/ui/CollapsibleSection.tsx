/**
 * Reusable CollapsibleSection component for expandable content sections
 */

import { useState } from 'react';
import styles from './CollapsibleSection.module.css';

interface CollapsibleSectionProps {
  title: string;
  children: React.ReactNode;
  defaultExpanded?: boolean;
}

export function CollapsibleSection({ title, children, defaultExpanded = true }: CollapsibleSectionProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className={styles.section}>
      <h3
        className={styles.title}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className={styles.icon}>
          {isExpanded ? '▼' : '▶'}
        </span>
        {title}
      </h3>
      {isExpanded && <div className={styles.content}>{children}</div>}
    </div>
  );
}
