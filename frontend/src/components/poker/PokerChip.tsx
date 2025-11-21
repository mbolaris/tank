/**
 * Poker chip component with realistic design
 */

import styles from './PokerChip.module.css';

interface PokerChipProps {
    value: number;
    count?: number;
    size?: 'small' | 'medium' | 'large';
}

export function PokerChip({ value, count = 1, size = 'medium' }: PokerChipProps) {
    // Determine chip color based on value
    const getChipColor = (val: number): { primary: string; secondary: string; text: string } => {
        if (val >= 100) return { primary: '#1a1a1a', secondary: '#333', text: '#fff' }; // Black
        if (val >= 25) return { primary: '#2d5016', secondary: '#3d6b1f', text: '#fff' }; // Green
        if (val >= 10) return { primary: '#1e3a8a', secondary: '#2563eb', text: '#fff' }; // Blue
        if (val >= 5) return { primary: '#dc2626', secondary: '#ef4444', text: '#fff' }; // Red
        return { primary: '#f3f4f6', secondary: '#e5e7eb', text: '#1f2937' }; // White
    };

    const colors = getChipColor(value);
    const sizeClass = styles[size] || styles.medium;

    return (
        <div className={`${styles.chipStack} ${sizeClass}`}>
            {Array.from({ length: Math.min(count, 5) }).map((_, i) => (
                <div
                    key={i}
                    className={styles.chip}
                    style={{
                        transform: `translateY(${-i * 4}px)`,
                        zIndex: 5 - i,
                    }}
                >
                    <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                        {/* Outer ring */}
                        <circle cx="50" cy="50" r="48" fill={colors.primary} stroke={colors.secondary} strokeWidth="2" />

                        {/* Inner circle */}
                        <circle cx="50" cy="50" r="38" fill={colors.secondary} stroke={colors.primary} strokeWidth="1" />

                        {/* Edge markers (8 around the edge) */}
                        {[0, 45, 90, 135, 180, 225, 270, 315].map((angle, idx) => {
                            const rad = (angle * Math.PI) / 180;
                            const x = 50 + 43 * Math.cos(rad);
                            const y = 50 + 43 * Math.sin(rad);
                            return (
                                <rect
                                    key={idx}
                                    x={x - 2}
                                    y={y - 4}
                                    width="4"
                                    height="8"
                                    fill="white"
                                    opacity="0.9"
                                    transform={`rotate(${angle} ${x} ${y})`}
                                />
                            );
                        })}

                        {/* Center value */}
                        <text
                            x="50"
                            y="58"
                            fontSize="24"
                            fontWeight="bold"
                            fill={colors.text}
                            textAnchor="middle"
                            fontFamily="Arial, sans-serif"
                        >
                            {value}
                        </text>
                    </svg>
                </div>
            ))}
            {count > 5 && (
                <div className={styles.countBadge}>+{count - 5}</div>
            )}
        </div>
    );
}

interface ChipStackProps {
    totalValue: number;
    size?: 'small' | 'medium' | 'large';
}

export function ChipStack({ totalValue, size = 'medium' }: ChipStackProps) {
    // Break down total into chip denominations
    const denominations = [100, 25, 10, 5, 1];
    const chips: { value: number; count: number }[] = [];

    let remaining = totalValue;
    for (const denom of denominations) {
        const count = Math.floor(remaining / denom);
        if (count > 0) {
            chips.push({ value: denom, count });
            remaining -= count * denom;
        }
    }

    return (
        <div className={styles.chipStackContainer}>
            {chips.map(({ value, count }) => (
                <PokerChip key={value} value={value} count={count} size={size} />
            ))}
        </div>
    );
}
