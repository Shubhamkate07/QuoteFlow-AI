import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ComparisonMatrixTable } from '../components/ComparisonMatrixTable';
import type { ComparisonSupplierBid } from '../types';
import type { Rfq } from '../../rfq/types';
import { renderWithProviders } from '../../../test/test-utils';

describe('ComparisonMatrixTable Component', () => {
  const mockRfq: Rfq = {
    id: 'rfq-comp-1',
    rfqNumber: 'RFQ-2026-0088',
    title: 'CNC Aluminum Housings',
    status: 'under_review',
    currency: 'USD',
    targetBudget: 25000,
    createdAt: '2026-11-20',
    requiredDeliveryDate: '2026-12-31',
    itemsCount: 2,
    quotationCount: 2,
    invitedSupplierIds: [],
    items: [],
  };

  const mockBids: ComparisonSupplierBid[] = [
    {
      quotationId: 'quote-1',
      supplierId: 'supp-1',
      supplierName: 'Apex Precision Ltd',
      quoteReference: 'QT-2026-001',
      fileName: 'Apex_Quote.pdf',
      fileSize: '1.2 MB',
      status: 'approved',
      currency: 'USD',
      isApproved: true,
      rank: 1,
      overallScore: 92.5,
      totalAmount: 22000,
      isLowestTotalAmount: true,
      varianceVsBudget: -3000,
      variancePercentage: -12.0,
      subtotal: 22000,
      taxAmount: 0,
      shippingAmount: 0,
      discountAmount: 0,
      paymentTerms: 'Net 30',
      deliveryLeadWeeks: 3,
      isShortestLeadTime: true,
      onTimeStatus: 'On Schedule',
      incoterms: 'DDP Chicago',
      warrantyTerms: '12 Months',
      specMatchPercentage: 80,
      isHighestSpecMatch: true,
      criticalMismatchesCount: 0,
      materialDeviations: [],
      missingFields: [],
      riskLevel: 'low',
      riskFlags: [],
      riskFlagDetails: [],
      lineItemsMap: {},
      scoreBreakdown: [
        { id: 'price', factorName: 'Price', weightPercentage: 40, rawScore: 95, weightedScore: 38, rationale: 'Lowest' },
        { id: 'spec_match', factorName: 'Specs', weightPercentage: 30, rawScore: 90, weightedScore: 27, rationale: 'High' },
        { id: 'delivery', factorName: 'Delivery', weightPercentage: 15, rawScore: 88, weightedScore: 13.2, rationale: 'On time' },
        { id: 'payment_terms', factorName: 'Terms', weightPercentage: 10, rawScore: 100, weightedScore: 10, rationale: 'Net 30' },
        { id: 'warranty', factorName: 'Warranty', weightPercentage: 5, rawScore: 85, weightedScore: 4.25, rationale: '12 Months' },
      ],
    },
    {
      quotationId: 'quote-2',
      supplierId: 'supp-2',
      supplierName: 'Global Machining Co',
      quoteReference: 'QT-2026-002',
      fileName: 'Global_Quote.pdf',
      fileSize: '850 KB',
      status: 'under_review',
      currency: 'USD',
      isApproved: false,
      rank: 2,
      overallScore: 81.0,
      totalAmount: 26500,
      isLowestTotalAmount: false,
      varianceVsBudget: 1500,
      variancePercentage: 6.0,
      subtotal: 26500,
      taxAmount: 0,
      shippingAmount: 0,
      discountAmount: 0,
      paymentTerms: '50% Advance',
      deliveryLeadWeeks: 5,
      isShortestLeadTime: false,
      onTimeStatus: 'Delayed',
      incoterms: 'FOB Berlin',
      warrantyTerms: '24 Months',
      specMatchPercentage: 60,
      isHighestSpecMatch: false,
      criticalMismatchesCount: 1,
      materialDeviations: ['Material mismatch'],
      missingFields: [],
      riskLevel: 'high',
      riskFlags: ['High Advance Payment', 'Delivery Delay'],
      riskFlagDetails: [],
      lineItemsMap: {},
      scoreBreakdown: [
        { id: 'price', factorName: 'Price', weightPercentage: 40, rawScore: 78, weightedScore: 31.2, rationale: 'Higher' },
        { id: 'spec_match', factorName: 'Specs', weightPercentage: 30, rawScore: 85, weightedScore: 25.5, rationale: 'Moderate' },
        { id: 'delivery', factorName: 'Delivery', weightPercentage: 15, rawScore: 80, weightedScore: 12, rationale: '5 weeks' },
        { id: 'payment_terms', factorName: 'Terms', weightPercentage: 10, rawScore: 80, weightedScore: 8, rationale: 'Advance' },
        { id: 'warranty', factorName: 'Warranty', weightPercentage: 5, rawScore: 90, weightedScore: 4.5, rationale: '24 Months' },
      ],
    },
  ];

  it('renders empty state when bids array is empty', () => {
    renderWithProviders(
      <ComparisonMatrixTable
        rfq={mockRfq}
        bids={[]}
        onOpenExplainScore={vi.fn()}
        onOpenSupplierDossier={vi.fn()}
      />
    );

    expect(screen.getByText('No Bids Match Current Filters')).toBeInTheDocument();
  });

  it('renders supplier bids with rankings and prices', () => {
    renderWithProviders(
      <ComparisonMatrixTable
        rfq={mockRfq}
        bids={mockBids}
        onOpenExplainScore={vi.fn()}
        onOpenSupplierDossier={vi.fn()}
      />
    );

    expect(screen.getByText('Apex Precision Ltd')).toBeInTheDocument();
    expect(screen.getByText('Global Machining Co')).toBeInTheDocument();
    expect(screen.getByText('Rank #1')).toBeInTheDocument();
    expect(screen.getByText('Rank #2')).toBeInTheDocument();
    expect(screen.getByText('$22,000.00')).toBeInTheDocument();
  });

  it('triggers onOpenExplainScore when Score button is clicked', async () => {
    const user = userEvent.setup();
    const handleExplain = vi.fn();

    renderWithProviders(
      <ComparisonMatrixTable
        rfq={mockRfq}
        bids={mockBids}
        onOpenExplainScore={handleExplain}
        onOpenSupplierDossier={vi.fn()}
      />
    );

    const scoreButtons = screen.getAllByRole('button', { name: /explain/i });
    expect(scoreButtons.length).toBeGreaterThan(0);
    await user.click(scoreButtons[0]);

    expect(handleExplain).toHaveBeenCalledWith(mockBids[0]);
  });
});
