import './StateBadge.css';

interface StateBadgeProps {
  label: string;
  active: boolean;
  type?: 'fill' | 'drain' | 'heater' | 'safe';
}

export function StateBadge({ label, active, type = 'fill' }: StateBadgeProps) {
  const badgeClass = ['state-badge'];
  if (active) {
    badgeClass.push('state-badge--active');
  } else {
    badgeClass.push('state-badge--inactive');
  }
  badgeClass.push(`state-badge--${type}`);
  if (type === 'safe' && active) {
    badgeClass.push('state-badge--danger');
  }

  return <span className={badgeClass.join(' ')}>{label}</span>;
}
