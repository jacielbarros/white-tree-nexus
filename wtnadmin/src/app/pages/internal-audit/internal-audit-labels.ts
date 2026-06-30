import { AuditChecklistResult, AuditFindingType, InternalAuditStatus } from '@app/core/models';

export const AUDIT_STATUS_LABELS: Record<InternalAuditStatus, string> = {
  planned: 'Planejada',
  in_progress: 'Em andamento',
  completed: 'Concluída',
  cancelled: 'Cancelada',
};

export const FINDING_TYPE_LABELS: Record<AuditFindingType, string> = {
  conforme: 'Conforme',
  nc_maior: 'NC maior',
  nc_menor: 'NC menor',
  oportunidade_melhoria: 'Oportunidade de melhoria',
  observacao: 'Observação',
};

export const CHECKLIST_RESULT_LABELS: Record<AuditChecklistResult, string> = {
  conforme: 'Conforme',
  nao_conforme: 'Não conforme',
  nao_aplicavel: 'Não aplicável',
  pendente: 'Pendente',
};
