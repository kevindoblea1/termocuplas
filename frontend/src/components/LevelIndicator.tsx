import './LevelIndicator.css';

interface LevelIndicatorProps {
  level: number;
  capacity: number;
}

export function LevelIndicator({ level, capacity }: LevelIndicatorProps) {
  const clampedCapacity = Math.max(capacity, 1);
  const ratio = Math.min(Math.max(level / clampedCapacity, 0), 1);
  const percentage = Math.round(ratio * 100);

  return (
    <div className="level-indicator">
      <div className="level-indicator__bar">
        <div className="level-indicator__fill" style={{ height: `${percentage}%` }} />
      </div>
      <div className="level-indicator__labels">
        <span>{capacity.toFixed(0)} L</span>
        <span>{level.toFixed(1)} L</span>
        <span>0 L</span>
      </div>
    </div>
  );
}
