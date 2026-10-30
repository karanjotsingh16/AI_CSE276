export type Language = 'en' | 'hi';

export interface TranslationDictionary {
  // Brand & Header
  brandTitle: string;
  brandSubtitle: string;
  endpoints: string;
  details: string;
  workspace: string;
  changeRoute: string;
  fieldReport: string;
  dispatchCargo: string;
  notifications: string;
  syncQueue: string;
  online: string;
  offline: string;
  pendingSync: string;

  // Stages & Prompts
  welcomeTitle: string;
  welcomeSubtitle: string;
  planRouteButton: string;
  selectOrigin: string;
  selectDestination: string;
  calculatingRoute: string;
  calculatingSubtitle: string;

  // Route Priorities
  priorityFastest: string;
  priorityShortest: string;
  priorityBalanced: string;
  priorityAccessibility: string;

  // Drawers & Panes
  drawerAccessibility: string;
  drawerTracking: string;
  drawerScoreBreakdown: string;
  drawerMlRanking: string;
  drawerDemandZones: string;

  // Route Summary Details
  recommendedRoute: string;
  alternativeRoute: string;
  estimatedTravelTime: string;
  totalDistance: string;
  roadHierarchy: string;
  weatherExposure: string;
  advisoriesReported: string;
  clearOfAdvisories: string;

  // Disclaimers & Provenance
  academicDisclaimer: string;
  syntheticDemandNotice: string;
  simulatedGpsNotice: string;
  offlineSyncReady: string;

  // Actions
  retry: string;
  close: string;
  submit: string;
  cancel: string;
  syncNow: string;
  saveOffline: string;
}

export const translations: Record<Language, TranslationDictionary> = {
  en: {
    brandTitle: "NER SmartRoute",
    brandSubtitle: "AI Logistics & Accessibility Intelligence — North-East India",
    endpoints: "Endpoints",
    details: "Details",
    workspace: "Workspace",
    changeRoute: "Change Route",
    fieldReport: "Field Report",
    dispatchCargo: "Dispatch Delivery",
    notifications: "Advisories & Alerts",
    syncQueue: "Sync Queue",
    online: "Online",
    offline: "Offline",
    pendingSync: "pending draft",

    welcomeTitle: "Intelligent Route Planning & Logistics for North-East India",
    welcomeSubtitle: "Terrain-aware routing, automated multi-hazard alerts, GPS fleet tracking, and road accessibility intelligence across Meghalaya and the 8 NER states.",
    planRouteButton: "Plan Logistics Corridor",
    selectOrigin: "Select Origin Hub",
    selectDestination: "Select Destination Hub",
    calculatingRoute: "Calculating Optimal Corridors...",
    calculatingSubtitle: "Evaluating OSM road network, terrain grade, Open-Meteo weather hazard, and regional road advisories.",

    priorityFastest: "Fastest (Time)",
    priorityShortest: "Shortest (Dist)",
    priorityBalanced: "Balanced",
    priorityAccessibility: "Accessibility",

    drawerAccessibility: "Corridors & Incidents",
    drawerTracking: "GPS Fleet & Deliveries",
    drawerScoreBreakdown: "Score Breakdown",
    drawerMlRanking: "AI / ML Ranking",
    drawerDemandZones: "K-Means Demand",

    recommendedRoute: "Recommended Route",
    alternativeRoute: "Alternative Corridor",
    estimatedTravelTime: "Est. Travel Time",
    totalDistance: "Total Distance",
    roadHierarchy: "Road Class Quality",
    weatherExposure: "Weather Hazard Score",
    advisoriesReported: "advisories reported",
    clearOfAdvisories: "100% Clear of Known Closures",

    academicDisclaimer: "Academic Integrity: Static travel estimates derived from OSM design speeds. Live traffic scoring is strictly disabled.",
    syntheticDemandNotice: "DEMONSTRATION DATA — Synthetic demand dataset. Silhouette metrics reflect cluster compactness, not predictive accuracy.",
    simulatedGpsNotice: "DEMONSTRATION MODE — Telemetry advances simulated along verified OSM road coordinates.",
    offlineSyncReady: "Offline-first sync active. Field reports saved in local storage will auto-sync when cellular network resumes.",

    retry: "Retry",
    close: "Close",
    submit: "Submit Report",
    cancel: "Cancel",
    syncNow: "Sync Now",
    saveOffline: "Save Offline Draft",
  },
  hi: {
    brandTitle: "पूर्वोत्तर स्मार्टरूट",
    brandSubtitle: "एआई लॉजिस्टिक्स एवं पहुंच मार्ग निगरानी — पूर्वोत्तर भारत",
    endpoints: "स्थान चयन",
    details: "विवरण",
    workspace: "कार्यक्षेत्र",
    changeRoute: "मार्ग बदलें",
    fieldReport: "फील्ड रिपोर्ट दर्ज करें",
    dispatchCargo: "डिलीवरी रवाना करें",
    notifications: "सूचनाएं व अलर्ट",
    syncQueue: "सिंक कतार",
    online: "ऑनलाइन",
    offline: "ऑफ़लाइन",
    pendingSync: "लंबित ड्राफ्ट",

    welcomeTitle: "पूर्वोत्तर भारत हेतु बौद्धिक मार्ग नियोजन एवं लॉजिस्टिक्स",
    welcomeSubtitle: "मेघालय और सभी 8 पूर्वोत्तर राज्यों के लिए स्थलाकृति-अनुकूल नेविगेशन, मौसम जोखिम आकलन, जीपीएस फ्लीट ट्रैकिंग और सड़क सुगम्यता।",
    planRouteButton: "लॉजिस्टिक्स मार्ग प्रारंभ करें",
    selectOrigin: "प्रारंभिक हब चुनें",
    selectDestination: "गंतव्य हब चुनें",
    calculatingRoute: "सर्वोत्तम मार्ग की गणना हो रही है...",
    calculatingSubtitle: "ओपनस्ट्रीटमैप नेटवर्क, ढलान, ओपन-मेटियो मौसम पूर्वानुमान और क्षेत्रीय सड़क प्रतिबंधों का विश्लेषण जारी है।",

    priorityFastest: "तीव्रतम (समय)",
    priorityShortest: "लघुतम (दूरी)",
    priorityBalanced: "संतुलित",
    priorityAccessibility: "सुगम्यता / गुणवत्ता",

    drawerAccessibility: "कॉरिडोर एवं घटनाएं",
    drawerTracking: "जीपीएस फ्लीट एवं मिशन",
    drawerScoreBreakdown: "स्कोर का विवरण",
    drawerMlRanking: "एआई / एमएल रैंकिंग",
    drawerDemandZones: "मांग क्षेत्र (K-Means)",

    recommendedRoute: "अनुशंसित मार्ग",
    alternativeRoute: "वैकल्पिक गलियारा",
    estimatedTravelTime: "अनुमानित यात्रा समय",
    totalDistance: "कुल दूरी",
    roadHierarchy: "सड़क श्रेणी गुणवत्ता",
    weatherExposure: "मौसम सुरक्षा स्कोर",
    advisoriesReported: "सड़क रुकावट दर्ज",
    clearOfAdvisories: "सभी ज्ञात अवरोधों से 100% मुक्त",

    academicDisclaimer: "शैक्षणिक सत्यनिष्ठा: यात्रा समय अनुमान स्थिर सड़क गति मानकों पर आधारित है। लाइव ट्रैफिक स्कोर अक्षम है।",
    syntheticDemandNotice: "प्रदर्शन डेटा — सिंथेटिक मांग सेट। सिल्हूट मान केवल क्लस्टर घनत्व दर्शाते हैं।",
    simulatedGpsNotice: "प्रदर्शन मोड — जीपीएस टेलीमेट्री सत्यापित सड़क निर्देशांकों के साथ सिमुलेट की गई है।",
    offlineSyncReady: "ऑफ़लाइन सिंक सक्रिय। नेटवर्क कनेक्टिविटी बहाल होते ही फील्ड रिपोर्ट स्वतः सिंक हो जाएगी।",

    retry: "पुनः प्रयास करें",
    close: "बंद करें",
    submit: "रिपोर्ट जमा करें",
    cancel: "रद्द करें",
    syncNow: "अभी सिंक करें",
    saveOffline: "ऑफ़लाइन ड्राफ्ट सहेजें",
  },
};

