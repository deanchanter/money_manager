interface StatCardProps {
  title: string;
  value: string;
  icon: string;
  color: 'green' | 'red' | 'blue' | 'purple';
  subtitle?: string;
}

const colorClasses = {
  green: 'bg-green-100 text-green-800',
  red: 'bg-red-100 text-red-800',
  blue: 'bg-blue-100 text-blue-800',
  purple: 'bg-purple-100 text-purple-800',
};

export default function StatCard({ title, value, icon, color, subtitle }: StatCardProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm p-6 border">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
        </div>
        <div className={`w-12 h-12 rounded-full flex items-center justify-center text-2xl ${colorClasses[color]}`}>
          {icon}
        </div>
      </div>
    </div>
  );
}
