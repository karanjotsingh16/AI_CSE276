import { CriticalFacility, InfraCategory } from '../types/infrastructure';
import { CRITICAL_FACILITIES } from '../data/facilities';

export async function fetchCriticalInfrastructure(
  categories?: InfraCategory[]
): Promise<CriticalFacility[]> {
  if (!categories || categories.length === 0) {
    return CRITICAL_FACILITIES;
  }
  return CRITICAL_FACILITIES.filter(f => categories.includes(f.category));
}
