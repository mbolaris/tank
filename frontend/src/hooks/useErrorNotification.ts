/**
 * Hook for displaying error notifications to users
 * Replaces silent console.error calls with user-visible feedback
 */

import { useState, useCallback } from 'react';

export interface ErrorNotification {
    message: string;
    timestamp: number;
}

export function useErrorNotification() {
    const [errors, setErrors] = useState<ErrorNotification[]>([]);

    const addError = useCallback((error: unknown, context?: string) => {
        const message = error instanceof Error ? error.message : String(error);
        const fullMessage = context ? `${context}: ${message}` : message;

        // Log to console for debugging
        console.error(fullMessage, error);

        // Add to user-visible errors
        const notification: ErrorNotification = {
            message: fullMessage,
            timestamp: Date.now()
        };

        setErrors(prev => [...prev, notification]);

        // Auto-dismiss after 10 seconds
        setTimeout(() => {
            setErrors(prev => prev.filter(e => e.timestamp !== notification.timestamp));
        }, 10000);
    }, []);

    const clearError = useCallback((timestamp: number) => {
        setErrors(prev => prev.filter(e => e.timestamp !== timestamp));
    }, []);

    const clearAll = useCallback(() => {
        setErrors([]);
    }, []);

    return {
        errors,
        addError,
        clearError,
        clearAll
    };
}
