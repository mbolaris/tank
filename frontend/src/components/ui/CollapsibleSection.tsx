/**
 * Reusable CollapsibleSection component for expandable content sections
 */

import { useState } from 'react';
import styles from './CollapsibleSection.module.css';

interface CollapsibleSectionProps {
    title: React.ReactNode;
    children: React.ReactNode;
    defaultExpanded?: boolean;
    expanded?: boolean;
    onToggle?: (expanded: boolean) => void;
}

export function CollapsibleSection({ title, children, defaultExpanded = true, expanded, onToggle }: CollapsibleSectionProps) {
    const [internalExpanded, setInternalExpanded] = useState(defaultExpanded);

    const isExpanded = expanded !== undefined ? expanded : internalExpanded;
    const handleToggle = () => {
        if (onToggle) {
            onToggle(!isExpanded);
        } else {
            setInternalExpanded(!isExpanded);
        }
    };

    return (
        <div className={styles.section}>
            <h3
                className={styles.title}
                onClick={handleToggle}
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
