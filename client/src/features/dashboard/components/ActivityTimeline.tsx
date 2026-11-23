import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../../components/ui/Card';
import {
  Sparkles,
  AlertTriangle,
  FileUp,
  CheckCircle,
  FileSpreadsheet,
  Clock,
} from 'lucide-react';
import type { ActivityItem } from '../types';

interface ActivityTimelineProps {
  activities: ActivityItem[];
}

export const ActivityTimeline: React.FC<ActivityTimelineProps> = ({ activities }) => {
  const iconConfig = {
    extraction: { icon: Sparkles, bg: 'bg-indigo-50 text-indigo-600 border-indigo-200' },
    risk_flag: { icon: AlertTriangle, bg: 'bg-amber-50 text-amber-600 border-amber-200' },
    upload: { icon: FileUp, bg: 'bg-sky-50 text-sky-600 border-sky-200' },
    approval: { icon: CheckCircle, bg: 'bg-emerald-50 text-emerald-600 border-emerald-200' },
    rfq_created: { icon: FileSpreadsheet, bg: 'bg-slate-100 text-slate-700 border-slate-200' },
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <CardTitle>Procurement Activity</CardTitle>
        <CardDescription>Real-time audit log of extractions, uploads, and decisions</CardDescription>
      </CardHeader>

      <CardContent className="flex-1 p-5">
        <div className="flow-root">
          <ul className="-mb-8">
            {activities.map((item, idx) => {
              const { icon: Icon, bg } = iconConfig[item.type] || iconConfig.upload;
              const isLast = idx === activities.length - 1;

              return (
                <li key={item.id}>
                  <div className="relative pb-6">
                    {!isLast && (
                      <span
                        className="absolute top-4 left-4 -ml-px h-full w-0.5 bg-slate-200"
                        aria-hidden="true"
                      />
                    )}

                    <div className="relative flex items-start space-x-3">
                      <div
                        className={`w-8 h-8 rounded-lg border flex items-center justify-center shrink-0 ${bg} shadow-2xs`}
                      >
                        <Icon className="w-4 h-4" />
                      </div>

                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between">
                          <p className="text-xs font-semibold text-slate-800 leading-tight">
                            {item.title}
                          </p>
                          <span className="text-[10px] text-slate-400 flex items-center shrink-0 ml-2">
                            <Clock className="w-2.5 h-2.5 mr-1" />
                            {item.timestamp}
                          </span>
                        </div>

                        <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">
                          {item.description}
                        </p>

                        {item.rfqCode && (
                          <div className="mt-1">
                            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-medium border border-slate-200/60">
                              {item.rfqCode}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      </CardContent>
    </Card>
  );
};
