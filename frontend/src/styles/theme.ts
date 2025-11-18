/**
 * Shared theme and styling constants for the application
 */

export const colors = {
  // Background colors
  bgPrimary: 'linear-gradient(145deg, rgba(30,41,59,0.92), rgba(15,23,42,0.95))',
  bgSecondary: 'rgba(51,65,85,0.4)',
  bgDark: '#0f172a',

  // Text colors
  textPrimary: '#e2e8f0',
  textSecondary: '#94a3b8',
  textTertiary: '#cbd5e1',

  // Border colors
  borderPrimary: 'rgba(148,163,184,0.18)',
  borderSecondary: 'rgba(148,163,184,0.1)',
  borderTertiary: 'rgba(148,163,184,0.08)',

  // Status colors
  success: '#4ade80',
  danger: '#ef4444',
  warning: '#fbbf24',
  info: '#3b82f6',

  // Button colors
  buttonPrimary: '#3b82f6',
  buttonSuccess: '#10b981',
  buttonSecondary: '#8b5cf6',
  buttonDanger: '#ef4444',
};

export const shadows = {
  card: '0 35px 55px rgba(2,6,23,0.65)',
  button: '0 10px 25px rgba(15,23,42,0.45)',
};

export const commonStyles = {
  panelContainer: {
    padding: '24px',
    background: colors.bgPrimary,
    borderRadius: '20px',
    color: colors.textPrimary,
    border: `1px solid ${colors.borderPrimary}`,
    boxShadow: shadows.card,
  },
  panelTitle: {
    margin: '0 0 16px 0',
    fontSize: '20px',
    fontWeight: 600,
  },
  button: {
    padding: '12px 16px',
    fontSize: '14px',
    fontWeight: 500,
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    boxShadow: shadows.button,
  },
};
