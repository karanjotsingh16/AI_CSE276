export type GoodsType = 
  | 'Food Supplies'
  | 'Medical Supplies'
  | 'Relief Materials'
  | 'General Cargo';

export type PriorityType = 
  | 'Low'
  | 'Normal'
  | 'High'
  | 'Emergency';

export type VehicleType = 
  | '4×4'
  | 'Van'
  | 'Small Truck'
  | 'Heavy Truck';

export interface LocationPoint {
  id: string;
  name: string;
  state: string;
  lat: number;
  lng: number;
  elevationMeters: number;
  type: 'hub' | 'depot' | 'destination' | 'outpost';
  description: string;
}

export interface LogisticsMission {
  goods: GoodsType;
  priority: PriorityType;
  quantityKg: number;
  vehicle: VehicleType;
  originId: string;
  destinationId: string;
}
