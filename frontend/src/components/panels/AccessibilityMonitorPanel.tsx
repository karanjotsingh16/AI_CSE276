import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldAlert,
  AlertOctagon,
  CheckCircle2,
  Clock,
  Filter,
  RefreshCw,
  Eye,
  FileCheck2,
  XCircle,
  FileText,
  UserCheck,
} from 'lucide-react';
import {
  RoadSegment,
  IncidentReport,
  AccessibilityAuditLog,
  SegmentStatus,
  IncidentStatus,
} from '../../types/accessibility';
import {
  fetchRoadSegments,
  fetchIncidents,
  fetchAuditLogs,
  reviewIncident,
} from '../../services/accessibilityService';

interface AccessibilityMonitorPanelProps {
  onSelectSegment?: (segment: RoadSegment) => void;
  onSelectIncident?: (incident: IncidentReport) => void;
  onRequestNewReport?: () => void;
}

export const AccessibilityMonitorPanel: React.FC<AccessibilityMonitorPanelProps> = ({
  onSelectSegment,
  onSelectIncident,
  onRequestNewReport,
}) => {
  const [activeTab, setActiveTab] = useState<'corridors' | 'incidents' | 'audit'>('corridors');

  // Corridors State
  const [segments, setSegments] = useState<RoadSegment[]>([]);
  const [segmentDistrictFilter, setSegmentDistrictFilter] = useState<string>('');
  const [segmentStatusFilter, setSegmentStatusFilter] = useState<string>('');
  const [isSegmentsLoading, setIsSegmentsLoading] = useState<boolean>(false);

  // Incidents State
  const [incidents, setIncidents] = useState<IncidentReport[]>([]);
  const [incidentStatusFilter, setIncidentStatusFilter] = useState<string>('');
  const [isIncidentsLoading, setIsIncidentsLoading] = useState<boolean>(false);

  // Audit Logs State
  const [auditLogs, setAuditLogs] = useState<AccessibilityAuditLog[]>([]);
  const [isAuditLoading, setIsAuditLoading] = useState<boolean>(false);

  // Verification Action Dialog State
  const [reviewingIncident, setReviewingIncident] = useState<IncidentReport | null>(null);
  const [reviewAction, setReviewAction] = useState<'verified' | 'rejected' | 'resolved'>('verified');
  const [reviewNotes, setReviewNotes] = useState<string>('');
  const [reviewerActor, setReviewerActor] = useState<string>('PWD Executive Engineer');
  const [cascadeSegmentStatus, setCascadeSegmentStatus] = useState<string>('restricted');
  const [isReviewSubmitting, setIsReviewSubmitting] = useState<boolean>(false);

  const loadSegments = useCallback(async () => {
    setIsSegmentsLoading(true);
    try {
      const segs = await fetchRoadSegments(
        segmentDistrictFilter || undefined,
        (segmentStatusFilter as SegmentStatus) || undefined
      );
      setSegments(segs);
    } catch (e) {
      console.error('Error fetching segments:', e);
    } finally {
      setIsSegmentsLoading(false);
    }
  }, [segmentDistrictFilter, segmentStatusFilter]);

  const loadIncidents = useCallback(async () => {
    setIsIncidentsLoading(true);
    try {
      const incs = await fetchIncidents(
        (incidentStatusFilter as IncidentStatus) || undefined
      );
      setIncidents(incs);
    } catch (e) {
      console.error('Error fetching incidents:', e);
    } finally {
      setIsIncidentsLoading(false);
    }
  }, [incidentStatusFilter]);

  const loadAuditLogs = useCallback(async () => {
    setIsAuditLoading(true);
    try {
      const logs = await fetchAuditLogs(40);
      setAuditLogs(logs);
    } catch (e) {
      console.error('Error fetching audit logs:', e);
    } finally {
      setIsAuditLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'corridors') {
      loadSegments();
    } else if (activeTab === 'incidents') {
      loadIncidents();
    } else if (activeTab === 'audit') {
      loadAuditLogs();
    }
  }, [activeTab, loadSegments, loadIncidents, loadAuditLogs]);

  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reviewingIncident) return;
    setIsReviewSubmitting(true);
    try {
      await reviewIncident(reviewingIncident.report_id, {
        new_status: reviewAction,
        actor: reviewerActor.trim() || 'Authorized Reviewer',
        review_notes: reviewNotes.trim() || `Reviewed and set to ${reviewAction}`,
        cascade_to_segment:
          reviewAction === 'verified' && cascadeSegmentStatus !== 'none'
            ? (cascadeSegmentStatus as 'open' | 'restricted' | 'blocked')
            : reviewAction === 'resolved'
            ? 'open'
            : undefined,
      });
      setReviewingIncident(null);
      setReviewNotes('');
      loadIncidents();
      loadSegments();
    } catch (err) {
      console.error('Failed to review incident:', err);
    } finally {
      setIsReviewSubmitting(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'open':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
            OPEN
          </span>
        );
      case 'restricted':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-800 border border-amber-200">
            RESTRICTED
          </span>
        );
      case 'blocked':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-100 text-rose-800 border border-rose-200">
            BLOCKED
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            {status.toUpperCase()}
          </span>
        );
    }
  };

  const getIncidentBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-800 border border-amber-200 flex items-center gap-1">
            <Clock className="w-2.5 h-2.5" /> PENDING
          </span>
        );
      case 'verified':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-100 text-blue-800 border border-blue-200 flex items-center gap-1">
            <UserCheck className="w-2.5 h-2.5" /> VERIFIED
          </span>
        );
      case 'resolved':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center gap-1">
            <CheckCircle2 className="w-2.5 h-2.5" /> RESOLVED
          </span>
        );
      case 'rejected':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-200 text-slate-700 border border-slate-300 flex items-center gap-1">
            <XCircle className="w-2.5 h-2.5" /> REJECTED
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-3 text-xs">
      {/* Header & Tabs */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-2">
        <div className="flex items-center gap-1.5 font-medium text-slate-700">
          <ShieldAlert className="w-4 h-4 text-rose-600" />
          <span>Road Accessibility & Field Intelligence</span>
        </div>
        {onRequestNewReport && (
          <button
            type="button"
            onClick={onRequestNewReport}
            className="px-2.5 py-1 rounded-md bg-slate-900 text-white font-medium hover:bg-slate-800 cursor-pointer text-[11px]"
          >
            + File Field Report
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1 p-0.5 rounded-lg bg-slate-100 border border-slate-200 text-[11px]">
          <button
            type="button"
            onClick={() => setActiveTab('corridors')}
            className={`px-3 py-1 rounded-md font-medium transition-colors cursor-pointer ${
              activeTab === 'corridors' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Corridors ({segments.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('incidents')}
            className={`px-3 py-1 rounded-md font-medium transition-colors cursor-pointer ${
              activeTab === 'incidents' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Field Reports ({incidents.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('audit')}
            className={`px-3 py-1 rounded-md font-medium transition-colors cursor-pointer ${
              activeTab === 'audit' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Audit Trail
          </button>
        </div>

        <button
          type="button"
          onClick={() => {
            if (activeTab === 'corridors') loadSegments();
            else if (activeTab === 'incidents') loadIncidents();
            else loadAuditLogs();
          }}
          className="p-1.5 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
          title="Refresh Data"
        >
          <RefreshCw
            className={`w-3.5 h-3.5 ${
              isSegmentsLoading || isIncidentsLoading || isAuditLoading ? 'animate-spin' : ''
            }`}
          />
        </button>
      </div>

      {/* Tab 1: Corridors */}
      {activeTab === 'corridors' && (
        <div className="space-y-2">
          {/* Filters */}
          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <select
              value={segmentDistrictFilter}
              onChange={(e) => setSegmentDistrictFilter(e.target.value)}
              className="px-2 py-1 rounded-md border border-slate-200 bg-white text-[11px] flex-1"
            >
              <option value="">All Districts</option>
              <option value="East Khasi Hills">East Khasi Hills</option>
              <option value="Ri-Bhoi">Ri-Bhoi</option>
              <option value="West Khasi Hills">West Khasi Hills</option>
              <option value="East Jaintia Hills">East Jaintia Hills</option>
              <option value="West Jaintia Hills">West Jaintia Hills</option>
            </select>
            <select
              value={segmentStatusFilter}
              onChange={(e) => setSegmentStatusFilter(e.target.value)}
              className="px-2 py-1 rounded-md border border-slate-200 bg-white text-[11px] w-28"
            >
              <option value="">All Statuses</option>
              <option value="open">Open</option>
              <option value="restricted">Restricted</option>
              <option value="blocked">Blocked</option>
            </select>
          </div>

          <div className="space-y-2 max-h-72 overflow-y-auto pr-0.5">
            {segments.map((seg) => (
              <div
                key={seg.segment_id}
                className="p-2.5 rounded-xl bg-white border border-slate-200/90 shadow-2xs space-y-1.5 hover:border-slate-300 transition-colors"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h4 className="font-semibold text-slate-900 leading-tight">{seg.name}</h4>
                    <p className="text-[10px] text-slate-500">
                      {seg.district} • Class: {seg.road_class.toUpperCase()}
                    </p>
                  </div>
                  {getStatusBadge(seg.status)}
                </div>

                {seg.restriction_details && (
                  <p className="text-[11px] text-slate-600 bg-slate-50 border border-slate-100 rounded-md p-1.5 leading-snug">
                    {seg.restriction_details}
                  </p>
                )}

                <div className="flex items-center justify-between text-[10px] text-slate-400 pt-0.5">
                  <span>ID: {seg.segment_id}</span>
                  {onSelectSegment && (
                    <button
                      type="button"
                      onClick={() => onSelectSegment(seg)}
                      className="text-sky-600 hover:text-sky-800 font-medium inline-flex items-center gap-1 cursor-pointer"
                    >
                      <Eye className="w-3 h-3" /> Focus Map
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 2: Incidents Queue */}
      {activeTab === 'incidents' && (
        <div className="space-y-2">
          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <div className="flex gap-1 text-[11px]">
              {['', 'pending', 'verified', 'resolved'].map((st) => (
                <button
                  key={st}
                  type="button"
                  onClick={() => setIncidentStatusFilter(st)}
                  className={`px-2.5 py-0.5 rounded-md font-medium capitalize cursor-pointer ${
                    incidentStatusFilter === st
                      ? 'bg-slate-800 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {st || 'All'}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2 max-h-72 overflow-y-auto pr-0.5">
            {incidents.length === 0 ? (
              <div className="py-6 text-center text-slate-400 text-xs">
                No incident reports match filter.
              </div>
            ) : (
              incidents.map((inc) => (
                <div
                  key={inc.report_id}
                  className="p-2.5 rounded-xl bg-white border border-slate-200/90 shadow-2xs space-y-2 hover:border-slate-300 transition-colors"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-1.5">
                        <AlertOctagon
                          className={`w-3.5 h-3.5 ${
                            inc.severity === 'critical'
                              ? 'text-rose-600'
                              : inc.severity === 'severe'
                              ? 'text-amber-600'
                              : 'text-slate-600'
                          }`}
                        />
                        <h4 className="font-semibold text-slate-900 leading-tight">
                          {inc.title}
                        </h4>
                      </div>
                      <p className="text-[10px] text-slate-500">
                        {inc.location_name} ({inc.district}) • {inc.incident_type.replace('_', ' ')}
                      </p>
                    </div>
                    {getIncidentBadge(inc.status)}
                  </div>

                  <p className="text-[11px] text-slate-600 leading-snug">{inc.description}</p>

                  {/* Photo Thumbnail if present */}
                  {inc.photo_url && (
                    <div className="flex items-center gap-2">
                      <img
                        src={inc.photo_url}
                        alt="Evidence"
                        className="w-16 h-12 rounded-lg object-cover border border-slate-200"
                      />
                      <span className="text-[10px] text-slate-400">Attached Field Photo</span>
                    </div>
                  )}

                  <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-100">
                    <span>
                      Reporter: {inc.reporter_name} ({inc.reporter_role})
                    </span>
                    <div className="flex items-center gap-2">
                      {onSelectIncident && (
                        <button
                          type="button"
                          onClick={() => onSelectIncident(inc)}
                          className="text-sky-600 hover:text-sky-800 font-medium inline-flex items-center gap-1 cursor-pointer"
                        >
                          <Eye className="w-3 h-3" /> Map
                        </button>
                      )}
                      {inc.status === 'pending' && (
                        <button
                          type="button"
                          onClick={() => {
                            setReviewingIncident(inc);
                            setReviewAction('verified');
                            setReviewNotes('');
                          }}
                          className="px-2 py-0.5 rounded bg-blue-600 text-white font-medium hover:bg-blue-700 cursor-pointer inline-flex items-center gap-1"
                        >
                          <FileCheck2 className="w-2.5 h-2.5" /> Review / Verify
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Immutable Audit Trail */}
      {activeTab === 'audit' && (
        <div className="space-y-2">
          <div className="text-[10px] text-slate-500">
            Immutable log of all corridor changes and verified incident reviews.
          </div>
          <div className="space-y-1.5 max-h-72 overflow-y-auto pr-0.5">
            {auditLogs.map((log) => (
              <div
                key={log.audit_id}
                className="p-2 rounded-lg bg-white border border-slate-200/80 text-[11px] space-y-1"
              >
                <div className="flex items-center justify-between font-medium">
                  <span className="text-slate-800 flex items-center gap-1">
                    <FileText className="w-3 h-3 text-slate-400" />
                    {log.action} ({log.entity_type})
                  </span>
                  <span className="text-[10px] text-slate-400">
                    {new Date(log.timestamp).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>
                <div className="text-slate-600 text-[10px] leading-tight">
                  <span className="font-semibold">{log.entity_id}:</span> {log.previous_status || 'None'} →{' '}
                  <span className="font-semibold text-slate-900">{log.new_status}</span> by{' '}
                  <span className="text-slate-800">{log.actor}</span>
                </div>
                {log.review_notes && (
                  <p className="text-[10px] text-slate-500 italic bg-slate-50 rounded px-1.5 py-0.5">
                    "{log.review_notes}"
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Admin Review Modal */}
      {reviewingIncident && (
        <div className="fixed inset-0 z-[2100] flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-in fade-in">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-md p-5 space-y-4 text-xs">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <h3 className="font-bold text-slate-900 flex items-center gap-1.5">
                <FileCheck2 className="w-4 h-4 text-blue-600" />
                Administrative Review: {reviewingIncident.report_id}
              </h3>
              <button
                type="button"
                onClick={() => setReviewingIncident(null)}
                className="text-slate-400 hover:text-slate-600 cursor-pointer"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleReviewSubmit} className="space-y-3">
              <div className="space-y-1">
                <label className="font-medium text-slate-700">Review Decision</label>
                <div className="grid grid-cols-3 gap-1.5">
                  {(['verified', 'rejected', 'resolved'] as const).map((act) => (
                    <button
                      key={act}
                      type="button"
                      onClick={() => setReviewAction(act)}
                      className={`py-1.5 rounded-lg text-center font-medium capitalize border cursor-pointer ${
                        reviewAction === act
                          ? act === 'verified'
                            ? 'bg-blue-600 text-white border-blue-600'
                            : act === 'rejected'
                            ? 'bg-rose-600 text-white border-rose-600'
                            : 'bg-emerald-600 text-white border-emerald-600'
                          : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      {act}
                    </button>
                  ))}
                </div>
              </div>

              {reviewAction === 'verified' && (
                <div className="space-y-1 bg-amber-50 border border-amber-200/80 p-2.5 rounded-lg">
                  <label className="font-medium text-amber-900 block">
                    Update Associated Road Corridor Status?
                  </label>
                  <select
                    value={cascadeSegmentStatus}
                    onChange={(e) => setCascadeSegmentStatus(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded-md border border-amber-300 bg-white text-slate-800"
                  >
                    <option value="none">Do not alter corridor status</option>
                    <option value="restricted">Mark corridor as RESTRICTED (Load/Speed Limit)</option>
                    <option value="blocked">Mark corridor as BLOCKED (Full Closure)</option>
                  </select>
                </div>
              )}

              <div className="space-y-1">
                <label className="font-medium text-slate-700">Reviewing Authority / Official *</label>
                <input
                  type="text"
                  required
                  value={reviewerActor}
                  onChange={(e) => setReviewerActor(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300"
                />
              </div>

              <div className="space-y-1">
                <label className="font-medium text-slate-700">Official Review Notes *</label>
                <textarea
                  required
                  rows={2}
                  placeholder="Record on-site findings, clearing schedule, or rationale for decision..."
                  value={reviewNotes}
                  onChange={(e) => setReviewNotes(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setReviewingIncident(null)}
                  className="px-3 py-1.5 rounded-lg text-slate-600 hover:bg-slate-100 cursor-pointer font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isReviewSubmitting}
                  className="px-4 py-1.5 rounded-lg bg-slate-900 text-white font-medium hover:bg-slate-800 cursor-pointer disabled:opacity-50"
                >
                  {isReviewSubmitting ? 'Recording Audit...' : 'Confirm Review'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

