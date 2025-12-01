import { ReactNode, HTMLAttributes } from 'react';
import clsx from 'clsx';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  className?: string;
  gradient?: 'green' | 'yellow' | 'orange';
}

export default function Card({ children, className, gradient, ...props }: CardProps) {
  const gradientClasses = {
    green: 'bg-gradient-to-br from-primary-400 to-primary-600 text-white',
    yellow: 'bg-gradient-to-br from-yellow-300 to-yellow-400 text-gray-800',
    orange: 'bg-gradient-to-br from-orange-300 to-orange-500 text-white',
  };

  return (
    <div
      className={clsx(
        'bg-white rounded-lg shadow-card p-4 transition-shadow hover:shadow-card-hover',
        gradient && gradientClasses[gradient],
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
