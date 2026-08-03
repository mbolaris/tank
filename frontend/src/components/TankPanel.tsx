import type { ReactNode } from 'react';
import styles from './TankView.module.css';

export function PanelLoading() {
    return (
        <div style={{ minHeight: '96px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-muted)', fontSize: '12px', fontWeight: 600 }}>
            Loading panel...
        </div>
    );
}

export function Panel({ title, icon, onClose, children }: { title: string; icon: string; onClose: () => void; children: ReactNode }) {
    return (
        <div className={styles.dashboardPanel} style={{ padding: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div className={styles.panelHeader}>
                <div className={styles.panelHeaderTitle}><span style={{ fontSize: '16px' }}>{icon}</span><span>{title}</span></div>
                <button className={styles.panelClose} onClick={onClose} aria-label={`Hide ${title} panel`} title={`Hide ${title} panel`}>×</button>
            </div>
            <div className={styles.panelBody}>{children}</div>
        </div>
    );
}
