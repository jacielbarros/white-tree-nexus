/** Rótulos PT-BR e cores do módulo de Riscos (Feature 012). */

export const RISK_STATUS_LABELS: Record<string, string> = {
  identified: 'Identificado',
  assessed: 'Avaliado',
  in_treatment: 'Em tratamento',
  accepted: 'Aceito',
  closed: 'Encerrado',
};

export const TREATMENT_LABELS: Record<string, string> = {
  mitigate: 'Mitigar',
  accept: 'Aceitar',
  transfer: 'Transferir',
  avoid: 'Evitar',
};

export const THREAT_CATEGORY_LABELS: Record<string, string> = {
  human: 'Humana',
  environmental: 'Ambiental',
  technical: 'Técnica',
  organizational: 'Organizacional',
};

export const THREAT_ORIGIN_LABELS: Record<string, string> = {
  deliberate: 'Deliberada',
  accidental: 'Acidental',
  environmental: 'Ambiental',
};

export const VULN_CATEGORY_LABELS: Record<string, string> = {
  technical: 'Técnica',
  physical: 'Física',
  organizational: 'Organizacional',
  human: 'Humana',
  process: 'Processual',
};

export const LEVEL_LABELS: Record<string, string> = {
  low: 'Baixo',
  medium: 'Médio',
  high: 'Alto',
  critical: 'Crítico',
};

export const LEVEL_COLORS: Record<string, string> = {
  low: '#2e7d32',
  medium: '#f9a825',
  high: '#ef6c00',
  critical: '#c62828',
};

export function levelLabel(key: string | null): string {
  return key ? (LEVEL_LABELS[key] ?? key) : '—';
}

export function levelColor(key: string | null | undefined): string {
  return key ? (LEVEL_COLORS[key] ?? 'var(--wtn-muted)') : 'var(--wtn-surface-2)';
}
