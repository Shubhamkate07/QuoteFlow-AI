import React from 'react';
import { Badge } from '../../../components/ui/Badge';
import type { RfqStatus } from '../types';

interface RfqStatusBadgeProps {
  status: RfqStatus;
  size?: 'sm' | 'md';
}

export const RfqStatusBadge: React.FC<RfqStatusBadgeProps> = ({ status, size = 'md' }) => {
  const configMap: Record<
    RfqStatus,
    { label: string; variant: 'neutral' | 'info' | 'warning' | 'success' | 'danger' }
  > = {
    draft: { label: 'Draft', variant: 'neutral' },
    open: { label: 'Open for Bids', variant: 'info' },
    under_review: { label: 'Under Review', variant: 'warning' },
    awarded: { label: 'Awarded', variant: 'success' },
    closed: { label: 'Closed', variant: 'neutral' },
  };

  const config = configMap[status] || { label: status, variant: 'neutral' };

  return (
    <Badge variant={config.variant} dot size={size}>
      {config.label}
    </Badge>
  );
};
