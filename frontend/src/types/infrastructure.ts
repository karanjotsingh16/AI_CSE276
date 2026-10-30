export type InfraCategory = 'hospital' | 'relief' | 'logistics';

export interface CriticalFacility {
  id: string;
  name: string;
  category: InfraCategory;
  lat: number;
  lng: number;
  address: string;
  capacityOrType: string;
  operationalStatus: 'Operational' | 'Standby' | 'Active Depot';
  source: string;
  disclaimer: string;
}
