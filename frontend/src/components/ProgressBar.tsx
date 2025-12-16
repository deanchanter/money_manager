interface ProgressBarProps {
  percentage: number;
  color?: string;
  showLabel?: boolean;
  height?: string;
}

export default function ProgressBar({ percentage, color = '#3B82F6', showLabel = true, height = 'h-2' }: ProgressBarProps) {
  const clampedPercentage = Math.min(100, Math.max(0, percentage));
  const isOverBudget = percentage > 100;

  return (
    <div className="w-full">
      <div className={`w-full bg-gray-200 rounded-full ${height}`}>
        <div
          className={`${height} rounded-full transition-all duration-300`}
          style={{
            width: `${clampedPercentage}%`,
            backgroundColor: isOverBudget ? '#EF4444' : color,
          }}
        />
      </div>
      {showLabel && (
        <p className={`text-sm mt-1 ${isOverBudget ? 'text-red-600 font-medium' : 'text-gray-600'}`}>
          {percentage.toFixed(1)}%{isOverBudget && ' - Over budget!'}
        </p>
      )}
    </div>
  );
}
