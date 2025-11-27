/**
 * Professional playing card component with SVG rendering
 */

import { useMemo } from 'react';
import styles from './PlayingCard.module.css';

interface PlayingCardProps {
    card: string; // Format: "A♠", "K♥", "10♦", "2♣", or "BACK"
    size?: 'tiny' | 'small' | 'medium' | 'large';
    faceDown?: boolean;
    className?: string;
}

export function PlayingCard({ card, size = 'medium', faceDown = false, className = '' }: PlayingCardProps) {
    const sizeClass = styles[size] || styles.medium;

    // Parse card string (e.g., "A♠" -> rank: "A", suit: "♠")
    const { rank, suit, color } = useMemo(() => {
        if (!card || card === 'BACK' || faceDown) {
            return { rank: '', suit: '', color: 'black' };
        }

        const match = card.match(/^(.+?)([♠♥♦♣])$/);
        if (!match) {
            return { rank: card, suit: '', color: 'black' };
        }

        const [, r, s] = match;
        const c = (s === '♥' || s === '♦') ? 'red' : 'black';
        return { rank: r, suit: s, color: c };
    }, [card, faceDown]);

    if (faceDown || !card || card === 'BACK') {
        return (
            <div className={`${styles.card} ${sizeClass} ${styles.back} ${className}`}>
                <svg viewBox="0 0 100 140" xmlns="http://www.w3.org/2000/svg">
                    {/* Card background */}
                    <rect x="2" y="2" width="96" height="136" rx="8" fill="#1a3a6e" stroke="#0d2847" strokeWidth="2" />

                    {/* White border inset */}
                    <rect x="8" y="8" width="84" height="124" rx="4" fill="none" stroke="#c9a227" strokeWidth="1.5" />

                    {/* Inner pattern area */}
                    <rect x="12" y="12" width="76" height="116" rx="2" fill="#1e4785" />

                    {/* Diamond lattice pattern */}
                    <defs>
                        <pattern id="cardPattern" x="0" y="0" width="16" height="16" patternUnits="userSpaceOnUse">
                            <path d="M8 0 L16 8 L8 16 L0 8 Z" fill="none" stroke="#2d6bb3" strokeWidth="0.8" opacity="0.6" />
                        </pattern>
                    </defs>
                    <rect x="12" y="12" width="76" height="116" rx="2" fill="url(#cardPattern)" />

                    {/* Center ornament */}
                    <ellipse cx="50" cy="70" rx="18" ry="24" fill="#1a3a6e" stroke="#c9a227" strokeWidth="1.5" />
                    <ellipse cx="50" cy="70" rx="12" ry="16" fill="none" stroke="#c9a227" strokeWidth="1" opacity="0.7" />

                    {/* Small diamond in center */}
                    <path d="M50 58 L58 70 L50 82 L42 70 Z" fill="#c9a227" opacity="0.8" />
                </svg>
            </div>
        );
    }

    return (
        <div className={`${styles.card} ${sizeClass} ${styles.face} ${className}`}>
            <svg viewBox="0 0 100 140" xmlns="http://www.w3.org/2000/svg">
                {/* Card background */}
                <rect x="2" y="2" width="96" height="136" rx="8" fill="white" stroke="#ddd" strokeWidth="1" />

                {/* Top-left corner */}
                <text x="12" y="22" fontSize="16" fontWeight="bold" fill={color} fontFamily="Arial, sans-serif">
                    {rank}
                </text>
                <text x="12" y="38" fontSize="14" fill={color} fontFamily="Arial, sans-serif">
                    {suit}
                </text>

                {/* Center suit symbol */}
                <text x="50" y="85" fontSize="48" fill={color} fontFamily="Arial, sans-serif" textAnchor="middle">
                    {suit}
                </text>

                {/* Bottom-right corner (rotated) */}
                <g transform="rotate(180 50 70)">
                    <text x="12" y="22" fontSize="16" fontWeight="bold" fill={color} fontFamily="Arial, sans-serif">
                        {rank}
                    </text>
                    <text x="12" y="38" fontSize="14" fill={color} fontFamily="Arial, sans-serif">
                        {suit}
                    </text>
                </g>
            </svg>
        </div>
    );
}
