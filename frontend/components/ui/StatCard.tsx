import { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StatCardProps {
  title: string;
  value: string | number;
  change?: number;
  icon: LucideIcon;
  iconColor?: string;
}

export const StatCard = ({ title, value, change, icon: Icon, iconColor = 'text-primary-600' }: StatCardProps) => {
  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {change !== undefined && (
            <p className={cn(
              'text-sm mt-1',
              change >= 0 ? 'text-success-600' : 'text-danger-600'
            )}>
              {change >= 0 ? '+' : ''}{change.toFixed(1)}% from yesterday
            </p>
          )}
        </div>
        <div className={cn('p-3 rounded-lg bg-gray-50', iconColor)}>
          <Icon className="h-6 w-6" />
        </div>
      </div>
    </div>
  );
};

