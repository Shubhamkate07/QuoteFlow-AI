import type { Rfq } from '../../rfq/types';
import type { Quotation } from '../../quotations/types';
import type {
  ComparisonSupplierBid,
  ScoreFactorBreakdown,
  ComparisonLineItemCell,
  BackendComparisonResponse,
  BackendRiskFlag,
} from '../types';

/**
 * Transforms Backend Comprehensive Comparison API response into rich UI bids
 */
export const adaptBackendComparisonToBids = (
  backendData: BackendComparisonResponse,
  rfq?: Rfq | null
): ComparisonSupplierBid[] => {
  if (!backendData || !backendData.supplier_comparison || backendData.supplier_comparison.length === 0) {
    return [];
  }

  const cards = backendData.supplier_comparison;
  const itemsMatrix = backendData.price_comparison?.items_matrix || (backendData as any).items_matrix || [];
  const matrixBudget = itemsMatrix.reduce((sum: number, it: any) => sum + (it.target_quantity || 0) * (it.target_unit_price || 0), 0);
  const targetBudget = (rfq?.targetBudget && rfq.targetBudget > 0) ? rfq.targetBudget : matrixBudget;

  // Find min lead time across suppliers
  const minLeadWeeks = Math.min(...cards.map((c) => c.delivery.lead_time_weeks || 99));

  // Build risk flags map by quotationId
  const riskMapByQuoteId: Record<string, { overallLevel: string; flags: BackendRiskFlag[] }> = {};
  (backendData.risk_flags || []).forEach((r) => {
    riskMapByQuoteId[r.quotation_id] = {
      overallLevel: r.overall_risk_level,
      flags: r.flags || [],
    };
  });

  return cards.map((card) => {
    const quoteId = card.quotation_id;
    const grandTotal = card.pricing.grand_total;
    const varianceVsBudget = targetBudget > 0 ? grandTotal - targetBudget : 0;
    const variancePercentage =
      targetBudget > 0 ? Math.round((varianceVsBudget / targetBudget) * 1000) / 10 : 0;

    const riskInfo = riskMapByQuoteId[quoteId] || {
      overallLevel: card.risk_profile.overall_risk_level || 'LOW',
      flags: [],
    };

    const riskFlagsTitles = riskInfo.flags.map((f) => f.title);
    const materialDeviations: string[] = [];
    riskInfo.flags.forEach((f) => {
      if (
        f.type === 'specification_mismatch' ||
        f.type === 'missing_specifications' ||
        f.affected_field?.toLowerCase().includes('spec')
      ) {
        materialDeviations.push(f.description || f.title);
      }
    });

    // Score factors breakdown
    const factorKeys: Array<'price' | 'spec_match' | 'delivery' | 'payment_terms' | 'warranty'> = [
      'price',
      'spec_match',
      'delivery',
      'payment_terms',
      'warranty',
    ];

    const factorNames: Record<string, string> = {
      price: 'Price Competitiveness',
      spec_match: 'Technical Specification Match',
      delivery: 'Delivery Schedule & Milestone',
      payment_terms: 'Commercial Payment Terms',
      warranty: 'Warranty Coverage & Support',
    };

    const scoreBreakdown: ScoreFactorBreakdown[] = factorKeys.map((fKey) => {
      const backendFactor = card.scoring.factors?.[fKey];
      if (backendFactor) {
        return {
          id: fKey,
          factorName: backendFactor.name || factorNames[fKey] || fKey,
          weightPercentage: Math.round(backendFactor.weight),
          rawScore: Math.round(backendFactor.raw_score),
          weightedScore: Math.round(backendFactor.weighted_score * 10) / 10,
          rationale: backendFactor.explanation || 'Evaluated deterministically according to RFQ criteria.',
          metrics: backendFactor.metrics,
        };
      }
      return {
        id: fKey,
        factorName: factorNames[fKey],
        weightPercentage: 20,
        rawScore: 100,
        weightedScore: 20,
        rationale: 'Standard scoring applied.',
      };
    });

    // Line items map for this quote
    const lineItemsMap: Record<string, ComparisonLineItemCell> = {};
    itemsMatrix.forEach((matrixRow: any) => {
      let qQuote: any = null;
      if (matrixRow.bids && typeof matrixRow.bids === 'object') {
        qQuote = matrixRow.bids[card.supplier_id] || matrixRow.bids[quoteId];
        if (!qQuote) {
          qQuote = Object.values(matrixRow.bids).find(
            (b: any) => b.quotation_id === quoteId || b.supplier_id === card.supplier_id
          );
        }
      }
      if (!qQuote && Array.isArray(matrixRow.quotes)) {
        qQuote = matrixRow.quotes.find(
          (q: any) => q.quotation_id === quoteId || q.supplier_id === card.supplier_id
        );
      }

      if (qQuote) {
        const uPrice = qQuote.normalized_unit_price ?? qQuote.quoted_unit_price ?? qQuote.unit_price ?? 0;
        const totPrice = qQuote.extended_price_target_qty ?? qQuote.extended_price_quoted_qty ?? qQuote.quoted_line_total ?? qQuote.extended_price ?? 0;
        const isLowest = qQuote.is_lowest_unit_price ?? qQuote.is_lowest ?? false;
        const hasVar = qQuote.has_spec_variance ?? (qQuote.is_compatible === false);

        lineItemsMap[matrixRow.rfq_item_id] = {
          unitPrice: Number(uPrice),
          totalPrice: Number(totPrice),
          materialSpec: qQuote.material_spec_quoted || matrixRow.item_name,
          confidenceScore: 0.95,
          isLowestUnitPrice: Boolean(isLowest),
          hasVariance: Boolean(hasVar),
          discrepancyNote: qQuote.spec_variance_notes || qQuote.incompatibility_reason || (hasVar ? 'Item specification or quantity variance flagged' : undefined),
        };
      }
    });

    const isLowestTotal = card.pricing.is_lowest_price;
    const isHighestSpec = card.specifications.compliance_score >= 100;
    const rank = card.rank || 1;

    let recommendationTag: string | undefined = undefined;
    if (rank === 1) {
      recommendationTag = 'Top Evaluated Rank';
    } else if (isLowestTotal) {
      recommendationTag = 'Lowest Total Price';
    } else if (isHighestSpec && riskInfo.overallLevel.toUpperCase() === 'LOW') {
      recommendationTag = '100% Spec Compliant';
    }

    const overallRisk = (riskInfo.overallLevel || 'LOW').toLowerCase() as 'low' | 'medium' | 'high';

    return {
      quotationId: card.quotation_id,
      supplierId: card.supplier_id,
      supplierName: card.supplier_name,
      supplierCategory: 'Approved Vendor',
      quoteReference: card.quotation_number,
      quoteDate: undefined,
      fileName: `Quote-${card.quotation_number}.pdf`,
      fileSize: '1.2 MB',
      status: card.review_status.description || 'Approved',
      currency: card.pricing.currency || 'USD',
      isApproved: card.review_status.is_approved,

      totalAmount: grandTotal,
      isLowestTotalAmount: isLowestTotal,
      varianceVsBudget,
      variancePercentage,
      subtotal: card.pricing.subtotal,
      taxAmount: card.pricing.tax_amount,
      shippingAmount: card.pricing.shipping_amount,
      discountAmount: card.pricing.discount_amount,
      paymentTerms: card.commercial_terms.payment_terms || 'Net 30',

      deliveryLeadWeeks: card.delivery.lead_time_weeks || 4,
      isShortestLeadTime: (card.delivery.lead_time_weeks || 99) <= minLeadWeeks,
      onTimeStatus: card.delivery.on_time_status || 'On Schedule',
      incoterms: card.delivery.delivery_terms || 'DAP Midwest Plant',
      warrantyTerms: card.commercial_terms.warranty_information || '12 Months Standard Warranty',

      specMatchPercentage: Math.round(card.specifications.compliance_score),
      isHighestSpecMatch: isHighestSpec,
      criticalMismatchesCount: card.specifications.total_critical_mismatches || 0,
      materialDeviations,
      missingFields: [],
      riskLevel: overallRisk === 'low' || overallRisk === 'medium' || overallRisk === 'high' ? overallRisk : 'medium',
      riskFlags: riskFlagsTitles,
      riskFlagDetails: riskInfo.flags,

      overallScore: Math.round(card.scoring.final_score),
      rank,
      recommendationTag,
      scoreBreakdown,
      lineItemsMap,
    };
  });
};

/**
 * Fallback local builder when comparing mock / client-side RFQs and Quotations
 */
export const buildComparisonData = (
  rfq: Rfq,
  quotations: Quotation[]
): ComparisonSupplierBid[] => {
  const validQuotes = quotations.filter(
    (q) => q.status !== 'failed' && q.totalAmount > 0
  );

  if (validQuotes.length === 0) {
    return [];
  }

  const minTotalAmount = Math.min(...validQuotes.map((q) => q.totalAmount));
  const minLeadWeeks = Math.min(
    ...validQuotes.map((q) => q.commercialTerms.deliveryLeadWeeks || 99)
  );

  const minUnitPriceByItemId: Record<string, number> = {};
  rfq.items.forEach((rfqItem) => {
    const prices: number[] = [];
    validQuotes.forEach((q) => {
      const match = q.extractedItems.find(
        (it) =>
          it.rfqItemId === rfqItem.id ||
          it.extractedPartName.toLowerCase().includes(rfqItem.name.toLowerCase().substring(0, 10))
      );
      if (match && match.unitPrice > 0) {
        prices.push(match.unitPrice);
      }
    });
    if (prices.length > 0) {
      minUnitPriceByItemId[rfqItem.id] = Math.min(...prices);
    }
  });

  const bids: ComparisonSupplierBid[] = validQuotes.map((q) => {
    const totalAmount = q.totalAmount;
    const isLowestTotal = Math.abs(totalAmount - minTotalAmount) < 0.01;
    const varianceVsBudget = totalAmount - rfq.targetBudget;
    const variancePercentage = Math.round((varianceVsBudget / rfq.targetBudget) * 1000) / 10;

    const leadWeeks = q.commercialTerms.deliveryLeadWeeks || 4;
    const isShortestLead = leadWeeks === minLeadWeeks;

    const materialDeviations: string[] = [];
    q.extractedItems.forEach((it) => {
      if (it.status === 'variance' && it.discrepancyNote) {
        materialDeviations.push(it.discrepancyNote);
      }
    });

    const missingFields: string[] = [...(q.missingFields || [])];
    if (!q.supplierInfo?.gstVatNumber) {
      if (!missingFields.includes('gstVatNumber')) missingFields.push('gstVatNumber');
    }

    const riskFlags: string[] = [];
    const riskFlagDetails: BackendRiskFlag[] = [];

    if (materialDeviations.length > 0) {
      riskFlags.push('Specification Variance: Alternative parameter quoted');
      riskFlagDetails.push({
        type: 'specification_mismatch',
        severity: 'HIGH',
        title: 'Specification Variance',
        description: materialDeviations.join('; '),
        affected_field: 'specifications',
        evidence: materialDeviations[0],
        recommended_action: 'Verify engineering tolerance acceptance before procurement award',
      });
    }
    if (leadWeeks > 4) {
      riskFlags.push(`Delivery Delay Risk: ${leadWeeks} weeks exceeds target milestone`);
      riskFlagDetails.push({
        type: 'delivery_delay',
        severity: 'MEDIUM',
        title: 'Delivery Schedule Delay',
        description: `Lead time of ${leadWeeks} weeks exceeds target milestone`,
        affected_field: 'delivery_lead_weeks',
        evidence: `${leadWeeks} weeks`,
        recommended_action: 'Negotiate expedited production or verify project buffer',
      });
    }
    if (
      q.commercialTerms.paymentTerms.toLowerCase().includes('advance') ||
      q.commercialTerms.paymentTerms.toLowerCase().includes('upfront')
    ) {
      riskFlags.push('Payment Risk: Supplier requires advance deposit');
      riskFlagDetails.push({
        type: 'high_advance_payment',
        severity: 'MEDIUM',
        title: 'Advance Payment Required',
        description: 'Supplier requires advance deposit impacting working capital liquidity',
        affected_field: 'payment_terms',
        evidence: q.commercialTerms.paymentTerms,
        recommended_action: 'Request bank guarantee or negotiate letter of credit',
      });
    }

    const riskLevel: 'low' | 'medium' | 'high' =
      riskFlags.length === 0 ? 'low' : riskFlags.length <= 2 ? 'medium' : 'high';

    const totalItems = q.extractedItems.length;
    const matchedCount = q.extractedItems.filter((it) => it.status === 'matched').length;
    const specMatchPercentage =
      totalItems > 0 ? Math.round((matchedCount / totalItems) * 100) : 88;

    const priceDeltaPct = ((totalAmount - minTotalAmount) / minTotalAmount) * 100;
    const rawPriceScore = Math.max(50, Math.round(100 - priceDeltaPct * 2.2));
    const priceWeighted = Math.round(rawPriceScore * 0.40 * 10) / 10;
    const priceRationale = isLowestTotal
      ? `Lowest quoted total of $${totalAmount.toLocaleString()} provides $${Math.abs(varianceVsBudget).toLocaleString()} savings.`
      : `$${totalAmount.toLocaleString()} is ${priceDeltaPct.toFixed(1)}% above lowest competitive bid.`;

    const rawSpecScore = specMatchPercentage;
    const specWeighted = Math.round(rawSpecScore * 0.30 * 10) / 10;
    const specRationale =
      materialDeviations.length === 0
        ? '100% compliance with technical specifications.'
        : `Specification deviation flagged: ${materialDeviations.join('; ')}`;

    const rawLeadScore =
      leadWeeks <= 4 ? 100 : leadWeeks === 5 ? 82 : Math.max(50, 100 - (leadWeeks - 4) * 18);
    const leadWeighted = Math.round(rawLeadScore * 0.15 * 10) / 10;
    const leadRationale =
      leadWeeks <= 4
        ? `${leadWeeks} calendar weeks fulfills required delivery schedule.`
        : `${leadWeeks} calendar weeks exceeds required deadline by ${leadWeeks - 4} week(s).`;

    let rawTermsScore = 90;
    if (
      q.commercialTerms.paymentTerms.toLowerCase().includes('net 30') ||
      q.commercialTerms.paymentTerms.toLowerCase().includes('net 45')
    ) {
      rawTermsScore += 10;
    }
    if (q.commercialTerms.paymentTerms.toLowerCase().includes('advance')) {
      rawTermsScore -= 20;
    }
    const termsWeighted = Math.round(rawTermsScore * 0.10 * 10) / 10;
    const termsRationale = `${q.commercialTerms.paymentTerms}; ${q.commercialTerms.incoterms}.`;

    const rawWarrantyScore = 95;
    const warrantyWeighted = Math.round(rawWarrantyScore * 0.05 * 10) / 10;
    const warrantyRationale = q.commercialTerms.warrantyTerms || '12 Months standard warranty coverage.';

    const overallScore = Math.round(
      priceWeighted + specWeighted + leadWeighted + termsWeighted + warrantyWeighted
    );

    const scoreBreakdown: ScoreFactorBreakdown[] = [
      {
        id: 'price',
        factorName: 'Price Competitiveness',
        weightPercentage: 40,
        rawScore: rawPriceScore,
        weightedScore: priceWeighted,
        rationale: priceRationale,
      },
      {
        id: 'spec_match',
        factorName: 'Specification Match',
        weightPercentage: 30,
        rawScore: rawSpecScore,
        weightedScore: specWeighted,
        rationale: specRationale,
      },
      {
        id: 'delivery',
        factorName: 'Delivery Schedule',
        weightPercentage: 15,
        rawScore: rawLeadScore,
        weightedScore: leadWeighted,
        rationale: leadRationale,
      },
      {
        id: 'payment_terms',
        factorName: 'Payment Terms',
        weightPercentage: 10,
        rawScore: rawTermsScore,
        weightedScore: termsWeighted,
        rationale: termsRationale,
      },
      {
        id: 'warranty',
        factorName: 'Warranty Coverage',
        weightPercentage: 5,
        rawScore: rawWarrantyScore,
        weightedScore: warrantyWeighted,
        rationale: warrantyRationale,
      },
    ];

    const lineItemsMap: Record<string, ComparisonLineItemCell> = {};
    rfq.items.forEach((rfqItem) => {
      const matchedExtracted = q.extractedItems.find(
        (it) =>
          it.rfqItemId === rfqItem.id ||
          it.extractedPartName.toLowerCase().includes(rfqItem.name.toLowerCase().substring(0, 10))
      );

      if (matchedExtracted) {
        const isLowestUnitPrice =
          minUnitPriceByItemId[rfqItem.id] !== undefined &&
          Math.abs(matchedExtracted.unitPrice - minUnitPriceByItemId[rfqItem.id]) < 0.01;

        lineItemsMap[rfqItem.id] = {
          unitPrice: matchedExtracted.unitPrice,
          totalPrice: matchedExtracted.totalPrice,
          materialSpec: matchedExtracted.materialSpec,
          confidenceScore: matchedExtracted.confidenceScore,
          isLowestUnitPrice,
          hasVariance: matchedExtracted.status === 'variance',
          discrepancyNote: matchedExtracted.discrepancyNote,
        };
      }
    });

    return {
      quotationId: q.id,
      supplierId: q.supplierId,
      supplierName: q.supplierName,
      supplierCategory: q.supplierInfo?.companyName || 'Machining Vendor',
      quoteReference: q.quoteReference,
      quoteDate: q.quoteDate,
      fileName: q.fileName,
      fileSize: q.fileSize,
      status: q.status,
      currency: q.currency,
      isApproved: true,

      totalAmount,
      isLowestTotalAmount: isLowestTotal,
      varianceVsBudget,
      variancePercentage,
      subtotal: totalAmount * 0.9,
      taxAmount: totalAmount * 0.1,
      shippingAmount: 0,
      discountAmount: 0,
      paymentTerms: q.commercialTerms.paymentTerms,

      deliveryLeadWeeks: leadWeeks,
      isShortestLeadTime: isShortestLead,
      onTimeStatus: leadWeeks <= 4 ? 'On Schedule' : 'Delayed',
      incoterms: q.commercialTerms.incoterms,
      warrantyTerms: q.commercialTerms.warrantyTerms,

      specMatchPercentage,
      isHighestSpecMatch: specMatchPercentage === 100,
      criticalMismatchesCount: materialDeviations.length,
      materialDeviations,
      missingFields,
      riskLevel,
      riskFlags,
      riskFlagDetails,

      overallScore,
      rank: 1,
      scoreBreakdown,
      lineItemsMap,
    };
  });

  const sortedByScore = [...bids].sort((a, b) => b.overallScore - a.overallScore);
  const maxScore = sortedByScore[0]?.overallScore || 0;

  return bids.map((bid) => {
    const rank = sortedByScore.findIndex((b) => b.quotationId === bid.quotationId) + 1;
    let recommendationTag: string | undefined = undefined;

    if (bid.overallScore === maxScore) {
      recommendationTag = 'Top Evaluated Rank';
    } else if (bid.isLowestTotalAmount) {
      recommendationTag = 'Lowest Total Price';
    } else if (bid.isHighestSpecMatch && bid.riskLevel === 'low') {
      recommendationTag = '100% Spec Compliant';
    }

    return {
      ...bid,
      rank,
      recommendationTag,
    };
  });
};
