export type NewsSourceState = 'loading' | 'success' | 'empty' | 'unavailable';

export interface DisasterNewsItem {
  id: string;
  headline: string;
  publisher: string;
  publishedTime: string;
  sourceUrl: string;
  summary: string;
  relevanceScore: number; // 0-100
  relevanceTag: 'High' | 'Medium' | 'Informational';
  category: 'Landslide' | 'Flooding' | 'Infrastructure' | 'Road Status' | 'Weather Impact';
  locationMentioned: string;
}
