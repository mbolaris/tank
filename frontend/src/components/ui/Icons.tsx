/**
 * Unified SVG icon system for consistent UI iconography.
 * All icons use currentColor for seamless theming.
 */

import type { CSSProperties } from 'react';

interface IconProps {
    size?: number;
    className?: string;
    style?: CSSProperties;
}

const defaultSize = 16;

export function FoodIcon({ size = defaultSize, className, style }: IconProps) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={className}
            style={style}
        >
            {/* Burger/food icon */}
            <path d="M3 11h18a2 2 0 0 1 0 4H3a2 2 0 0 1 0-4z" />
            <path d="M12 2C6.5 2 2 5.5 2 9.5c0 .5.4 1.5.4 1.5h19.2s.4-1 .4-1.5C22 5.5 17.5 2 12 2z" />
            <path d="M2 17.5c0 1.7 1.3 3 3 3h14c1.7 0 3-1.3 3-3v-1H2v1z" />
        </svg>
    );
}

export function FishIcon({ size = defaultSize, className, style }: IconProps) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={className}
            style={style}
        >
            <path d="M6.5 12c6-6 14-3 14 0s-8 6-14 0z" />
            <path d="M2.5 12L6.5 8v8l-4-4z" />
            <circle cx="16" cy="12" r="1" fill="currentColor" />
        </svg>
    );
}

export function PlayIcon({ size = defaultSize, className, style }: IconProps) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="currentColor"
            className={className}
            style={style}
        >
            <polygon points="5,3 19,12 5,21" />
        </svg>
    );
}

export function PauseIcon({ size = defaultSize, className, style }: IconProps) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="currentColor"
            className={className}
            style={style}
        >
            <rect x="6" y="4" width="4" height="16" rx="1" />
            <rect x="14" y="4" width="4" height="16" rx="1" />
        </svg>
    );
}

export function FastForwardIcon({ size = defaultSize, className, style }: IconProps) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="currentColor"
            className={className}
            style={style}
        >
            <polygon points="3,4 12,12 3,20" />
            <polygon points="12,4 21,12 12,20" />
        </svg>
    );
}

export function ResetIcon({ size = defaultSize, className, style }: IconProps) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={className}
            style={style}
        >
            <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
            <path d="M3 3v5h5" />
        </svg>
    );
}

export function PlantIcon({ size = defaultSize, className, style }: IconProps) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={className}
            style={style}
        >
            <path d="M12 22V10" />
            <path d="M12 10C12 6 8 2 4 2c0 4 4 8 8 8" />
            <path d="M12 14c0-4 4-8 8-8 0 4-4 8-8 8" />
        </svg>
    );
}

export function ChartIcon({ size = defaultSize, className, style }: IconProps) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={className}
            style={style}
        >
            <line x1="18" y1="20" x2="18" y2="10" />
            <line x1="12" y1="20" x2="12" y2="4" />
            <line x1="6" y1="20" x2="6" y2="14" />
        </svg>
    );
}

export function WaveIcon({ size = defaultSize, className, style }: IconProps) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={className}
            style={style}
        >
            <path d="M2 12c1.5-2.5 3-4 5-4s3 4 5 4 3.5-4 5-4 3.5 1.5 5 4" />
            <path d="M2 17c1.5-2.5 3-4 5-4s3 4 5 4 3.5-4 5-4 3.5 1.5 5 4" />
        </svg>
    );
}

export function GlobeIcon({ size = defaultSize, className, style }: IconProps) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={className}
            style={style}
        >
            <circle cx="12" cy="12" r="10" />
            <line x1="2" y1="12" x2="22" y2="12" />
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
        </svg>
    );
}

export function EyeIcon({ size = defaultSize, className, style }: IconProps) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={className}
            style={style}
        >
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
            <circle cx="12" cy="12" r="3" fill="currentColor" />
        </svg>
    );
}

export function EyeOffIcon({ size = defaultSize, className, style }: IconProps) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={className}
            style={style}
        >
            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
            <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
            <line x1="1" y1="1" x2="23" y2="23" />
        </svg>
    );
}

export function ChevronLeftIcon({ size = defaultSize, className, style }: IconProps) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={className}
            style={style}
        >
            <polyline points="15,18 9,12 15,6" />
        </svg>
    );
}

export function ChevronRightIcon({ size = defaultSize, className, style }: IconProps) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={className}
            style={style}
        >
            <polyline points="9,6 15,12 9,18" />
        </svg>
    );
}

export function SlotsIcon({ size = defaultSize, className, style }: IconProps) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={className}
            style={style}
        >
            <rect x="3" y="5" width="18" height="14" rx="2" />
            <line x1="9" y1="5" x2="9" y2="19" />
            <line x1="15" y1="5" x2="15" y2="19" />
            <circle cx="6" cy="12" r="1.5" fill="currentColor" />
            <circle cx="12" cy="12" r="1.5" fill="currentColor" />
            <circle cx="18" cy="12" r="1.5" fill="currentColor" />
        </svg>
    );
}

export function CardsIcon({ size = defaultSize, className, style }: IconProps) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={className}
            style={style}
        >
            <rect x="4" y="2" width="12" height="16" rx="2" />
            <rect x="8" y="6" width="12" height="16" rx="2" />
        </svg>
    );
}
