import React from 'react';
import { LoadingSpinner } from './LoadingSpinner';

interface PageLoadingProps {
  message?: string;
}

export const PageLoading: React.FC<PageLoadingProps> = ({
  message = 'Loading workspace data...',
}) => {
  return (
    <div className="min-h-[50vh] flex flex-col items-center justify-center p-8">
      <LoadingSpinner size="lg" label={message} />
    </div>
  );
};
