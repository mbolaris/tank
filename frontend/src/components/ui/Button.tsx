/**
 * Reusable Button component with consistent styling and variants
 */

import React from 'react';
import styles from './Button.module.css';

export type ButtonVariant = 'primary' | 'success' | 'secondary' | 'danger' | 'special' | 'poker' | 'evaluate';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  children: React.ReactNode;
}

export function Button({ variant = 'primary', children, className = '', ...props }: ButtonProps) {
  const variantClass = styles[variant] || styles.primary;

  return (
    <button
      className={`${styles.button} ${variantClass} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
