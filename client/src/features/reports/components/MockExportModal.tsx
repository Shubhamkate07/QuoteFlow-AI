import React from 'react';
import { ReportExportModal, type ReportExportModalProps } from './ReportExportModal';

export interface MockExportModalProps extends Omit<ReportExportModalProps, 'rfqId'> {
  rfqId?: string;
}

/**
 * Backwards compatibility wrapper for ReportExportModal
 */
export const MockExportModal: React.FC<MockExportModalProps> = ({
  rfqId = '',
  ...props
}) => {
  return <ReportExportModal rfqId={rfqId} {...props} />;
};
