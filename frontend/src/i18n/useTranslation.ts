import { useContext } from 'react';
import { LanguageContext } from './context';

export const useTranslation = () => useContext(LanguageContext);
