import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  RadialLinearScale,
} from 'chart.js';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  RadialLinearScale
);

interface ChartContainerProps {
  children: React.ReactNode;
  config?: any;
  className?: string;
}

export function ChartContainer({ children, config = {}, className = '' }: ChartContainerProps) {
  return (
    <div className={`w-full ${className}`}>
      {children}
    </div>
  );
} 