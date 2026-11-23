import React from 'react';
import { Link } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../../components/ui/Card';
import { Badge } from '../../../components/ui/Badge';
import { Button } from '../../../components/ui/Button';
import { GitCompare, ArrowRight, ShieldAlert, Award, Clock } from 'lucide-react';
import { formatCurrency } from '../../../utils/formatters';
import type { SupplierComparisonSummary } from '../types';
import { ROUTES } from '../../../routes/paths';

interface RecentComparisonsCardProps {
  comparisons: SupplierComparisonSummary[];
}

export const RecentComparisonsCard: React.FC<RecentComparisonsCardProps> = ({ comparisons }) => {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Recent Supplier Comparisons</CardTitle>
            <CardDescription>
              Completed bid matrices with recommended suppliers and risk assessments
            </CardDescription>
          </div>
          <Link to={ROUTES.COMPARISON}>
            <Button variant="ghost" size="sm" rightIcon={<ArrowRight className="w-3.5 h-3.5" />}>
              All Matrices
            </Button>
          </Link>
        </div>
      </CardHeader>

      <CardContent className="divide-y divide-slate-100 p-0">
        {comparisons.map((comp) => {
          return (
            <div
              key={comp.id}
              className="p-5 hover:bg-slate-50/70 transition-colors flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
            >
              <div className="space-y-1.5 flex-1 min-w-0">
                <div className="flex items-center space-x-2">
                  <span className="font-mono text-xs font-semibold text-slate-500">
                    {comp.rfqCode}
                  </span>
                  <Badge variant="neutral" size="sm" className="text-[10px]">
                    Spec Match: {comp.specMatchScore}%
                  </Badge>
                  {comp.riskLevel === 'moderate' && (
                    <Badge variant="warning" dot size="sm" className="text-[10px]">
                      Risk Review
                    </Badge>
                  )}
                  {comp.riskLevel === 'low' && (
                    <Badge variant="success" dot size="sm" className="text-[10px]">
                      Low Risk
                    </Badge>
                  )}
                </div>

                <div className="font-semibold text-sm text-slate-900 truncate">
                  {comp.title}
                </div>

                <div className="flex items-center space-x-3 text-xs text-slate-500">
                  <span className="flex items-center text-slate-700 font-medium">
                    <Award className="w-3.5 h-3.5 text-amber-500 mr-1 shrink-0" />
                    Top Offer: <span className="text-slate-900 font-semibold ml-1">{comp.recommendedSupplier}</span>
                  </span>
                  {comp.deliveryDaysVariance !== 0 && (
                    <span className="flex items-center text-slate-500">
                      <Clock className="w-3 h-3 mr-1" />
                      {comp.deliveryDaysVariance > 0
                        ? `+${comp.deliveryDaysVariance}d delivery lead`
                        : `${comp.deliveryDaysVariance}d faster delivery`}
                    </span>
                  )}
                </div>

                {comp.riskSummary && (
                  <div className="text-[11px] text-amber-700 bg-amber-50/80 px-2.5 py-1 rounded-md border border-amber-200/60 inline-flex items-center gap-1.5 mt-1">
                    <ShieldAlert className="w-3 h-3 text-amber-600 shrink-0" />
                    <span>{comp.riskSummary}</span>
                  </div>
                )}
              </div>

              {/* Price & Action */}
              <div className="flex items-center justify-between sm:flex-col sm:items-end gap-2 shrink-0">
                <div className="text-right">
                  <div className="text-base font-bold text-slate-900">
                    {formatCurrency(comp.bestCost)}
                  </div>
                  <div className="text-xs font-semibold text-emerald-600">
                    Save {formatCurrency(comp.savingsAmount)} ({comp.savingsPercentage}%)
                  </div>
                </div>

                <Link to={ROUTES.COMPARISON}>
                  <Button variant="outline" size="sm" className="h-8 text-xs gap-1.5">
                    <GitCompare className="w-3.5 h-3.5 text-slate-500" />
                    <span>Open Matrix</span>
                  </Button>
                </Link>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
};
