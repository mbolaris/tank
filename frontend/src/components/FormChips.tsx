import styles from './TeamProgressPanel.module.css';

export function FormChips({ form }: { form: readonly string[] }) {
    if (!form.length) return <span className={styles.muted}>No league form yet</span>;
    return (
        <span className={styles.formChips} aria-label="Recent league form">
            {form.map((result, index) => <span className={`${styles.formChip} ${styles[`form${result}` as keyof typeof styles]}`} key={`${result}-${index}`}>{result}</span>)}
        </span>
    );
}
