import {
  CorrectiveActionStatus,
  ImprovementOrigin,
  ImprovementStatus,
  NCOrigin,
  NCSeverity,
  NCStatus,
  VerificationResult,
} from '@app/core/models';

export const NC_ORIGIN_LABELS: Record<NCOrigin, string> = {
  audit_finding: 'Constatação de auditoria',
  external_audit: 'Auditoria externa',
  incident: 'Incidente',
  management_review: 'Análise crítica',
  other: 'Outra',
};

export const NC_SEVERITY_LABELS: Record<NCSeverity, string> = {
  maior: 'Maior',
  menor: 'Menor',
  observacao: 'Observação',
};

export const NC_STATUS_LABELS: Record<NCStatus, string> = {
  open: 'Aberta',
  in_progress: 'Em tratamento',
  in_verification: 'Em verificação',
  closed: 'Encerrada',
  cancelled: 'Cancelada',
};

export const ACTION_STATUS_LABELS: Record<CorrectiveActionStatus, string> = {
  planned: 'Planejada',
  in_progress: 'Em andamento',
  done: 'Concluída',
  cancelled: 'Cancelada',
};

export const VERIFICATION_LABELS: Record<VerificationResult, string> = {
  effective: 'Eficaz',
  ineffective: 'Não eficaz',
};

export const IMPROVEMENT_ORIGIN_LABELS: Record<ImprovementOrigin, string> = {
  audit: 'Auditoria',
  nonconformity: 'Não conformidade',
  management_review: 'Análise crítica',
  suggestion: 'Sugestão',
};

export const IMPROVEMENT_STATUS_LABELS: Record<ImprovementStatus, string> = {
  proposed: 'Proposta',
  in_progress: 'Em andamento',
  implemented: 'Implementada',
  rejected: 'Rejeitada',
};
