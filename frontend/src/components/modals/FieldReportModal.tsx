import React, { useState } from 'react';
import {
  X,
  AlertTriangle,
  MapPin,
  Camera,
  Upload,
  CheckCircle2,
  Navigation,
  Loader2,
  ShieldAlert,
  WifiOff,
  Save,
} from 'lucide-react';
import {
  IncidentType,
  IncidentSeverity,
  IncidentReport,
} from '../../types/accessibility';
import {
  submitIncidentReport,
  uploadIncidentPhoto,
} from '../../services/accessibilityService';
import { queueIncidentDraft } from '../../services/offlineQueueService';
import { useTranslation } from '../../i18n';

interface FieldReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultCoords?: [number, number];
  defaultLocationName?: string;
  onReportSubmitted?: (report: IncidentReport) => void;
}

export const FieldReportModal: React.FC<FieldReportModalProps> = ({
  isOpen,
  onClose,
  defaultCoords,
  defaultLocationName,
  onReportSubmitted,
}) => {
  const { t } = useTranslation();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [incidentType, setIncidentType] = useState<IncidentType>('landslide');
  const [severity, setSeverity] = useState<IncidentSeverity>('severe');
  const [latitude, setLatitude] = useState<string>(
    defaultCoords ? defaultCoords[0].toFixed(5) : '25.5788'
  );
  const [longitude, setLongitude] = useState<string>(
    defaultCoords ? defaultCoords[1].toFixed(5) : '91.8933'
  );
  const [district, setDistrict] = useState('East Khasi Hills');
  const [locationName, setLocationName] = useState(defaultLocationName || 'Shillong Corridor');
  const [reporterName, setReporterName] = useState('');
  const [reporterRole, setReporterRole] = useState('field_worker');
  const [contactNumber, setContactNumber] = useState('');

  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);

  const [isGpsLoading, setIsGpsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [submittedReport, setSubmittedReport] = useState<IncidentReport | null>(null);
  const [isOfflineSaved, setIsOfflineSaved] = useState(false);

  if (!isOpen) return null;

  const handleCaptureGps = () => {
    if (!navigator.geolocation) {
      setErrorMsg('Geolocation is not supported by this browser.');
      return;
    }
    setIsGpsLoading(true);
    setErrorMsg(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLatitude(pos.coords.latitude.toFixed(5));
        setLongitude(pos.coords.longitude.toFixed(5));
        setIsGpsLoading(false);
      },
      (err) => {
        setIsGpsLoading(false);
        setErrorMsg(`GPS Capture failed: ${err.message}. Please enter coordinates manually.`);
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  };

  const handlePhotoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.size > 5 * 1024 * 1024) {
        setErrorMsg('Photo size exceeds 5 MB limit. Please select a smaller image.');
        return;
      }
      setPhotoFile(file);
      setPhotoPreview(URL.createObjectURL(file));
      setErrorMsg(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    const latNum = parseFloat(latitude);
    const lngNum = parseFloat(longitude);

    if (isNaN(latNum) || isNaN(lngNum)) {
      setErrorMsg('Please enter valid numeric latitude and longitude coordinates.');
      return;
    }
    if (!title.trim() || !description.trim() || !reporterName.trim() || !locationName.trim()) {
      setErrorMsg('Please complete all required fields.');
      return;
    }

    setIsSubmitting(true);
    const payload = {
      title: title.trim(),
      description: description.trim(),
      incident_type: incidentType,
      severity,
      latitude: latNum,
      longitude: lngNum,
      district: district.trim(),
      location_name: locationName.trim(),
      reporter_name: reporterName.trim(),
      reporter_role: reporterRole,
      contact_number: contactNumber.trim() || undefined,
    };

    if (!navigator.onLine) {
      queueIncidentDraft(payload);
      setIsOfflineSaved(true);
      setIsSubmitting(false);
      return;
    }

    try {
      let photoUrl: string | undefined = undefined;
      if (photoFile) {
        try {
          photoUrl = await uploadIncidentPhoto(photoFile);
        } catch (uploadErr) {
          console.warn('Photo upload failed, continuing with report submission:', uploadErr);
        }
      }

      const report = await submitIncidentReport({
        ...payload,
        photo_url: photoUrl,
      });

      setSubmittedReport(report);
      if (onReportSubmitted) {
        onReportSubmitted(report);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes('Failed to fetch') || msg.includes('NetworkError') || !navigator.onLine) {
        queueIncidentDraft(payload);
        setIsOfflineSaved(true);
      } else {
        setErrorMsg(msg);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveOfflineDraft = () => {
    const latNum = parseFloat(latitude);
    const lngNum = parseFloat(longitude);
    if (isNaN(latNum) || isNaN(lngNum)) {
      setErrorMsg('Please enter valid numeric latitude and longitude coordinates.');
      return;
    }
    if (!title.trim() || !description.trim() || !reporterName.trim() || !locationName.trim()) {
      setErrorMsg('Please complete all required fields before saving offline draft.');
      return;
    }
    queueIncidentDraft({
      title: title.trim(),
      description: description.trim(),
      incident_type: incidentType,
      severity,
      latitude: latNum,
      longitude: lngNum,
      district: district.trim(),
      location_name: locationName.trim(),
      reporter_name: reporterName.trim(),
      reporter_role: reporterRole,
      contact_number: contactNumber.trim() || undefined,
    });
    setIsOfflineSaved(true);
  };

  const handleReset = () => {
    setSubmittedReport(null);
    setIsOfflineSaved(false);
    setTitle('');
    setDescription('');
    setPhotoFile(null);
    setPhotoPreview(null);
    setErrorMsg(null);
  };

  return (
    <div className="fixed inset-0 z-[2000] flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-xl max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-rose-500/20 border border-rose-500/40 flex items-center justify-center text-rose-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold tracking-wide">
                Submit Field Incident Report (Module E)
              </h2>
              <p className="text-[11px] text-slate-300">
                Logistics & Road Accessibility Field Intelligence
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            type="button"
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-4 text-xs">
          {isOfflineSaved ? (
            <div className="py-6 text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-amber-50 text-amber-600 flex items-center justify-center mx-auto border border-amber-200">
                <WifiOff className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-slate-900">
                  Incident Report Saved to Offline Queue
                </h3>
                <p className="text-xs text-slate-600">
                  Network connection is unavailable or intermittent.
                </p>
                <div className="inline-block mt-2 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-100 text-amber-800 border border-amber-200">
                  PERSISTENT LOCAL STORAGE DRAFT
                </div>
              </div>
              <p className="text-[11px] text-slate-500 max-w-md mx-auto leading-relaxed">
                Your report has been queued locally. As soon as your device reconnects to cellular or WiFi coverage, NER SmartRoute will automatically transmit it to the central authority.
              </p>
              <div className="pt-2 flex items-center justify-center gap-3">
                <button
                  type="button"
                  onClick={handleReset}
                  className="px-4 py-2 rounded-lg border border-slate-300 hover:bg-slate-50 text-slate-700 font-medium transition-colors cursor-pointer"
                >
                  File Another Report
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-medium transition-colors cursor-pointer"
                >
                  Close & View Map
                </button>
              </div>
            </div>
          ) : submittedReport ? (
            <div className="py-6 text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto border border-emerald-200">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-slate-900">
                  Incident Report Filed Successfully
                </h3>
                <p className="text-xs text-slate-600">
                  Report ID:{' '}
                  <span className="font-mono font-semibold text-slate-800">
                    {submittedReport.report_id}
                  </span>
                </p>
                <div className="inline-block mt-2 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-amber-100 text-amber-800 border border-amber-200">
                  Status: PENDING REVIEW
                </div>
              </div>
              <p className="text-[11px] text-slate-500 max-w-md mx-auto leading-relaxed">
                As per operational guidelines, submitted reports remain pending
                until validated by authorized field engineers or disaster authorities.
                The road status will update upon administrative review.
              </p>
              <div className="flex justify-center gap-3 pt-2">
                <button
                  type="button"
                  onClick={handleReset}
                  className="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium transition-colors cursor-pointer"
                >
                  File Another Report
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-medium transition-colors cursor-pointer"
                >
                  Close & View Map
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              {errorMsg && (
                <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{errorMsg}</span>
                </div>
              )}

              {/* Title & Type */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="font-medium text-slate-700">Incident Title *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Major Landslide on NH-6"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-slate-800"
                  />
                </div>

                <div className="space-y-1">
                  <label className="font-medium text-slate-700">Incident Category *</label>
                  <select
                    value={incidentType}
                    onChange={(e) => setIncidentType(e.target.value as IncidentType)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-slate-800 bg-white"
                  >
                    <option value="landslide">Landslide / Mudslip</option>
                    <option value="road_blockage">Road Blockage / Debris</option>
                    <option value="flood">Flash Flood / Waterlogging</option>
                    <option value="bridge_damage">Bridge Damage / Load Limit</option>
                    <option value="road_damage">Road Cave-in / Pothole</option>
                    <option value="other">Other Road Disruption</option>
                  </select>
                </div>
              </div>

              {/* Severity & Location Name */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="font-medium text-slate-700">Severity Level *</label>
                  <div className="grid grid-cols-4 gap-1.5">
                    {(['low', 'moderate', 'severe', 'critical'] as IncidentSeverity[]).map(
                      (sev) => (
                        <button
                          key={sev}
                          type="button"
                          onClick={() => setSeverity(sev)}
                          className={`py-1.5 rounded-lg text-center font-medium capitalize border transition-all cursor-pointer ${
                            severity === sev
                              ? sev === 'critical'
                                ? 'bg-rose-600 text-white border-rose-600'
                                : sev === 'severe'
                                ? 'bg-amber-600 text-white border-amber-600'
                                : 'bg-slate-900 text-white border-slate-900'
                              : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                          }`}
                        >
                          {sev}
                        </button>
                      )
                    )}
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="font-medium text-slate-700">Location Landmark *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Sonapur Tunnel North Portal"
                    value={locationName}
                    onChange={(e) => setLocationName(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-slate-800"
                  />
                </div>
              </div>

              {/* Coordinates & District */}
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-700 flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-rose-500" />
                    Geographic Coordinates *
                  </span>
                  <button
                    type="button"
                    onClick={handleCaptureGps}
                    disabled={isGpsLoading}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-white border border-slate-300 text-slate-700 hover:bg-slate-100 font-medium cursor-pointer"
                  >
                    {isGpsLoading ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <Navigation className="w-3 h-3 text-sky-600" />
                    )}
                    Use Device GPS
                  </button>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <label className="text-[10px] text-slate-500">Latitude</label>
                    <input
                      type="number"
                      step="any"
                      required
                      value={latitude}
                      onChange={(e) => setLatitude(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-500">Longitude</label>
                    <input
                      type="number"
                      step="any"
                      required
                      value={longitude}
                      onChange={(e) => setLongitude(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-500">District</label>
                    <select
                      value={district}
                      onChange={(e) => setDistrict(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white"
                    >
                      <option value="East Khasi Hills">East Khasi Hills</option>
                      <option value="Ri-Bhoi">Ri-Bhoi</option>
                      <option value="West Khasi Hills">West Khasi Hills</option>
                      <option value="East Jaintia Hills">East Jaintia Hills</option>
                      <option value="West Jaintia Hills">West Jaintia Hills</option>
                      <option value="Kamrup Metropolitan">Kamrup Metro (Assam)</option>
                      <option value="Cachar">Cachar (Assam)</option>
                      <option value="Papum Pare">Papum Pare (Arunachal)</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Photo Upload */}
              <div className="space-y-1">
                <label className="font-medium text-slate-700 flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <Camera className="w-3.5 h-3.5 text-slate-500" />
                    Evidence Photograph (Optional, max 5 MB)
                  </span>
                  {photoFile && (
                    <span className="text-[10px] text-slate-400 font-mono">
                      {(photoFile.size / 1024 / 1024).toFixed(2)} MB
                    </span>
                  )}
                </label>
                <div className="flex items-center gap-3">
                  <label className="flex-1 border-2 border-dashed border-slate-300 hover:border-slate-400 rounded-xl p-3 text-center cursor-pointer bg-slate-50 hover:bg-slate-100 transition-colors">
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      onChange={handlePhotoSelect}
                      className="hidden"
                    />
                    <div className="flex items-center justify-center gap-2 text-slate-600">
                      <Upload className="w-4 h-4 text-slate-500" />
                      <span className="font-medium">
                        {photoFile ? photoFile.name : 'Choose file (JPG, PNG, WebP)'}
                      </span>
                    </div>
                  </label>
                  {photoPreview && (
                    <img
                      src={photoPreview}
                      alt="Preview"
                      className="w-12 h-12 rounded-lg object-cover border border-slate-200"
                    />
                  )}
                </div>
              </div>

              {/* Reporter Details */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <div className="space-y-1">
                  <label className="font-medium text-slate-700">Reporter Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Officer Lyngdoh"
                    value={reporterName}
                    onChange={(e) => setReporterName(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300"
                  />
                </div>
                <div className="space-y-1">
                  <label className="font-medium text-slate-700">Role</label>
                  <select
                    value={reporterRole}
                    onChange={(e) => setReporterRole(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white"
                  >
                    <option value="field_worker">Field Worker / Patrol</option>
                    <option value="driver">Logistics Driver</option>
                    <option value="local_authority">Local Authority / PWD</option>
                    <option value="citizen">Local Citizen</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="font-medium text-slate-700">Contact Number</label>
                  <input
                    type="tel"
                    placeholder="e.g. +91 98765 43210"
                    value={contactNumber}
                    onChange={(e) => setContactNumber(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300"
                  />
                </div>
              </div>

              {/* Description */}
              <div className="space-y-1">
                <label className="font-medium text-slate-700">Incident Details & Observations *</label>
                <textarea
                  required
                  rows={2}
                  placeholder="Describe obstruction extent, single-lane flow status, ongoing clearing machinery..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-slate-800 text-xs"
                />
              </div>

              {/* Disclaimer */}
              <div className="text-[10px] text-amber-800 bg-amber-50 border border-amber-200/70 rounded-lg p-2 leading-relaxed">
                <span className="font-semibold">Academic Integrity Notice:</span> Unverified field
                reports do not automatically modify official route scores or mark highways blocked.
                Authorised review is mandatory.
              </div>

              {/* Actions */}
              <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 rounded-lg text-slate-600 hover:bg-slate-100 font-medium transition-colors cursor-pointer"
                >
                  {t.cancel}
                </button>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleSaveOfflineDraft}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg border border-amber-300 bg-amber-50 text-amber-900 font-medium hover:bg-amber-100 transition-colors cursor-pointer text-xs"
                  >
                    <Save className="w-3.5 h-3.5" />
                    {t.saveOffline}
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="inline-flex items-center gap-1.5 px-5 py-2 rounded-lg bg-slate-900 text-white font-medium hover:bg-slate-800 disabled:opacity-50 transition-colors cursor-pointer"
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        Submitting...
                      </>
                    ) : (
                      t.submit
                    )}
                  </button>
                </div>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

