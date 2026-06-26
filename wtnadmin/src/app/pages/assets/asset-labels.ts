import {
  AssetRelationshipType,
  AssetReviewStatus,
  AssetScopeStatus,
  AssetType,
  CiaLevel,
} from '@app/core/models';

export const ASSET_TYPE_LABELS: Record<AssetType, string> = {
  information_asset: 'Ativo de informação',
  system: 'Sistema/aplicação',
  database: 'Base de dados',
  business_process: 'Processo de negócio',
  infrastructure: 'Infraestrutura',
  service: 'Serviço',
  supplier: 'Fornecedor/terceiro',
  document: 'Documento/política',
  person_team: 'Pessoa/equipe',
  physical_environment: 'Ambiente físico',
  other: 'Outro',
};

export const CIA_LABELS: Record<string, string> = {
  baixa: 'Baixa',
  media: 'Média',
  alta: 'Alta',
  critica: 'Crítica',
};

export const SCOPE_STATUS_LABELS: Record<string, string> = {
  in_scope: 'Dentro do escopo',
  out_of_scope: 'Fora do escopo',
  under_analysis: 'Em análise',
};

export const RECORD_STATUS_LABELS: Record<string, string> = {
  active: 'Ativo',
  in_review: 'Em revisão',
  archived: 'Arquivado',
};

export const REVIEW_STATUS_LABELS: Record<string, string> = {
  up_to_date: 'Em dia',
  due_soon: 'Próxima do vencimento',
  overdue: 'Vencida',
  undefined: 'Não definida',
};

export const RELATIONSHIP_TYPE_LABELS: Record<AssetRelationshipType, string> = {
  depends_on: 'depende de',
  supports: 'suporta',
  uses: 'utiliza',
  stores: 'armazena',
  processes: 'processa',
  responsible_for: 'é responsável por',
  operated_by: 'é operado por',
  regulated_by: 'é regulado por',
  linked_to: 'está vinculado a',
  replaces: 'substitui',
  other: 'outro',
};

// Tipagem auxiliar para garantir cobertura de enums em tempo de compilação.
export type _AssetTypeKeys = AssetType;
export type _CiaKeys = CiaLevel;
export type _ScopeKeys = AssetScopeStatus;
export type _ReviewKeys = AssetReviewStatus;
