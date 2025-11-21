/**
 * Professional playing card component with SVG rendering
 */

import { useMemo } from 'react';
import styles from './PlayingCard.module.css';

interface PlayingCardProps {
    card: string; // Format: "A♠", "K♥", "10♦", "2♣", or "BACK"
    size?: 'tiny' | 'small' | 'medium' | 'large';
    faceDown?: boolean;
}

export function PlayingCard({ card, size = 'medium', faceDown = false }: PlayingCardProps) {
    const sizeClass = styles[size] || styles.medium;

    // Parse card string (e.g., "A♠" -> rank: "A", suit: "♠")
    const { rank, suit, color } = useMemo(() => {
        if (card === 'BACK' || faceDown) {
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

    if (faceDown || card === 'BACK') {
        return (
            <div className={`${styles.card} ${sizeClass} ${styles.back}`}>
                <svg viewBox="0 0 100 140" xmlns="http://www.w3.org/2000/svg">
                    {/* Card border */}
                    <rect x="2" y="2" width="96" height="136" rx="8" fill="#1a4d8f" stroke="#0d2847" strokeWidth="2" />

                    {/* Decorative pattern */}
                    <circle cx="50" cy="70" r="30" fill="none" stroke="#2d6bb3" strokeWidth="2" opacity="0.6" />
                    <circle cx="50" cy="70" r="20" fill="none" stroke="#2d6bb3" strokeWidth="1.5" opacity="0.4" />
                    <circle cx="50" cy="70" r="10" fill="none" stroke="#2d6bb3" strokeWidth="1" opacity="0.3" />
                </svg>
            </div>
        );
    }

    return (
        <div className={`${styles.card} ${sizeClass} ${styles.face}`}>
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
