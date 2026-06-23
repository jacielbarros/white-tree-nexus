import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { SelectModule } from 'primeng/select';
import { TextareaModule } from 'primeng/textarea';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { hasPermission } from '@app/core/permissions';
import {
  Classification,
  GapAssessment,
  GapAssessmentItem,
  GapAssignmentItem,
  GapDimension,
  GapEvidenceHistory,
  GapEvidenceSummary,
  GapPriority,
  GapStatus,
  GapTheme,
} from '@app/core/models';
import { DocumentHistory } from '@app/shared/document-history/document-history';
import { DocumentPreview } from '@app/shared/document-preview/document-preview';

const STATUS_LABELS: Record<GapStatus, string> = {
  not_filled: 'Não avaliado',
  meets: 'Atende',
  partial: 'Parcialmente atende',
  not_meet: 'Não atende',
  not_applicable: 'N/A',
};

const STATUS_CLASSES: Record<GapStatus, string> = {
  not_filled: 'wtn-tag--neutral',
  meets: 'wtn-tag--success',
  partial: 'wtn-tag--warning',
  not_meet: 'wtn-tag--danger',
  not_applicable: 'wtn-tag--info',
};

const STATUS_OPTIONS = [
  { label: 'Não avaliado', value: 'not_filled' },
  { label: 'Atende', value: 'meets' },
  { label: 'Parcialmente atende', value: 'partial' },
  { label: 'Não atende', value: 'not_meet' },
  { label: 'N/A', value: 'not_applicable' },
];

const PRIORITY_OPTIONS = [
  { label: 'Crítico', value: 'critical' },
  { label: 'Alto', value: 'high' },
  { label: 'Médio', value: 'medium' },
  { label: 'Baixo', value: 'low' },
];

const PRIORITY_LABELS: Record<GapPriority, string> = {
  critical: 'Crítico',
  high: 'Alto',
  medium: 'Médio',
  low: 'Baixo',
};

const PRIORITY_COLORS: Record<GapPriority, string> = {
  critical: 'var(--wtn-prio-crit)',
  high: 'var(--wtn-prio-high)',
  medium: 'var(--wtn-prio-med)',
  low: 'var(--wtn-prio-low)',
};

const CLASSIFICATION_OPTIONS: { label: string; value: Classification }[] = [
  { label: 'Uso interno', value: 'uso_interno' },
  { label: 'Público', value: 'publico' },
  { label: 'Confidencial', value: 'confidencial' },
  { label: 'Restrito', value: 'restrito' },
];

const CLASSIFICATION_LABELS: Record<Classification, string> = {
  publico: 'Público',
  uso_interno: 'Uso interno',
  confidencial: 'Confidencial',
  restrito: 'Restrito',
};

const GROUP_LABELS: Record<GapDimension | GapTheme, string> = {
  clause: 'Cláusulas (4-10)',
  annex_a: 'Anexo A - Controles',
  organizational: 'Organizacional',
  people: 'Pessoas',
  physical: 'Físico',
  technological: 'Tecnológico',
};

const GROUP_ORDER: Record<string, number> = {
  clause: 0,
  organizational: 1,
  people: 2,
  physical: 3,
  technological: 4,
  annex_a: 5,
};

const ASSIGNMENT_STATUS_LABELS: Record<string, string> = {
  pending: 'Pendente',
  in_progress: 'Em avaliação',
  submitted: 'Enviado',
  signed: 'Assinado',
  completed: 'Concluído',
  cancelled: 'Cancelado',
};

interface GapGroup {
  key: string;
  label: string;
  count: number;
  items: GapAssessmentItem[];
}

interface ItemGuidance {
  seed_item_id: string;
  ref_code: string;
  referencia: string;
  objetivo: string;
  como_avaliar: string[];
  evidencias_esperadas: string[];
  nota: string | null;
}

interface GuidanceLegendEntry {
  code: string;
  label: string;
  definition: string;
  order: number;
}

interface GuidanceResponse {
  items: ItemGuidance[];
  legend: { status: GuidanceLegendEntry[]; priority: GuidanceLegendEntry[] };
}

@Component({
  selector: 'app-gap-analysis',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    FormsModule,
    ButtonModule,
    DialogModule,
    InputTextModule,
    SelectModule,
    TextareaModule,
    DocumentPreview,
    DocumentHistory,
  ],
  template: `
    <header class="wtn-page-header gap-matrix-header">
      <div>
        <h1 class="wtn-page-title">Gap Analysis — Matriz</h1>
        <p class="wtn-page-desc">
          {{ totalItems() }} controles do Anexo A · {{ evaluatedItems() }} avaliados · aderência geral {{ adherenceLabel() }}
        </p>
      </div>
      <div class="wtn-page-actions">
        @if (assessment()) {
          <p-button
            [label]="showOnlyGaps() ? 'Todos' : 'Filtros'"
            icon="pi pi-filter"
            severity="secondary"
            (onClick)="toggleGapFilter()"
          />
          @if (canAssign()) {
            <p-button label="Atribuir condução" icon="pi pi-user-plus" (onClick)="showAssignDialog()" />
          }
        }
      </div>
    </header>

    @if (legendStatus().length || legendPriority().length) {
      <details class="wtn-legend">
        <summary>Legenda — escalas de Status e Prioridade</summary>
        <div class="legend-grid">
          <div>
            <div class="legend-h">Status</div>
            @for (s of legendStatus(); track s.code) {
              <div class="legend-row"><strong>{{ s.label }}</strong><span>{{ s.definition }}</span></div>
            }
          </div>
          <div>
            <div class="legend-h">Prioridade</div>
            @for (p of legendPriority(); track p.code) {
              <div class="legend-row"><strong>{{ p.label }}</strong><span>{{ p.definition }}</span></div>
            }
          </div>
        </div>
      </details>
    }

    @if (loading()) {
      <div class="matrix-loading">
        <div class="wtn-spinner"></div>
        <span>Carregando matriz...</span>
      </div>
    } @else if (!assessment()) {
      <div class="wtn-empty">
        <div class="wtn-empty-icon">
          <span class="pi pi-table"></span>
        </div>
        <div class="wtn-empty-title">Nenhuma avaliação encontrada</div>
        <div class="wtn-empty-desc">Adote o catálogo ISO/IEC 27001:2022 para iniciar a matriz.</div>
        @if (canManage()) {
          <p-button
            label="Adotar catálogo 2022.1"
            icon="pi pi-download"
            (onClick)="adoptCatalog()"
            [loading]="adopting()"
          />
        }
      </div>
    } @else {
      <div class="document-tools">
        <app-document-preview
          [documentType]="'gap_report'"
          [sourceArtifactId]="assessment()?.id ?? null"
          title="Relatorio de Gap Analysis"
        />
        <app-document-history
          [documentType]="'gap_report'"
          [sourceArtifactId]="assessment()?.id ?? null"
          title="Historico de Gap Analysis"
        />
      </div>

      <section class="gap-matrix-shell">
        <div class="gap-table-panel">
          <table class="gap-table">
            <thead>
              <tr>
                <th class="col-ref">Ref.</th>
                <th>Controle</th>
                <th class="col-status">Status</th>
                <th class="col-priority">Prioridade</th>
                <th class="col-resp">Resp.</th>
              </tr>
            </thead>
            <tbody>
              @for (group of groupedItems(); track group.key) {
                <tr class="group-row">
                  <td colspan="5">
                    <div class="group-label">
                      <span class="chevron">⌄</span>
                      <strong>{{ group.label }}</strong>
                      <span>{{ group.count }} controles</span>
                    </div>
                  </td>
                </tr>
                @for (item of group.items; track item.id) {
                  <tr
                    class="matrix-row"
                    [class.matrix-row--selected]="selectedItem()?.id === item.id"
                    (click)="selectItem(item)"
                  >
                    <td class="ref-cell">{{ item.ref_code }}</td>
                    <td class="name-cell">{{ item.name }}</td>
                    <td>
                      <span [class]="'wtn-tag ' + statusClass(item.status)">
                        {{ statusLabel(item.status) }}
                      </span>
                    </td>
                    <td>
                      @if (item.priority) {
                        <span class="priority-text" [style.color]="priorityColor(item.priority)">
                          {{ priorityLabel(item.priority) }}
                        </span>
                      } @else {
                        <span class="muted-dash">—</span>
                      }
                    </td>
                    <td>
                      <span class="assignee-avatar">
                        {{ responsibleInitials(item.responsible) }}
                      </span>
                    </td>
                  </tr>
                }
              } @empty {
                <tr>
                  <td colspan="5" class="table-empty">Nenhum controle encontrado para o filtro atual.</td>
                </tr>
              }
            </tbody>
          </table>
        </div>

        <aside class="gap-edit-panel">
          @if (selectedItem(); as it) {
            <div class="panel-title-row">
              <div>
                <div class="panel-ref">{{ it.ref_code }}</div>
                <h2>{{ it.name }}</h2>
              </div>
              <button type="button" class="panel-close" (click)="closeDetails()" title="Fechar painel">×</button>
            </div>

            @if (selectedGuidance(); as g) {
              <div class="guidance-block">
                <div class="guidance-head">Orientação de avaliação</div>
                @if (g.objetivo) { <p class="guidance-obj">{{ g.objetivo }}</p> }
                @if (g.como_avaliar.length) {
                  <div class="guidance-sub">Como avaliar</div>
                  <ul class="guidance-list">
                    @for (q of g.como_avaliar; track q) { <li>{{ q }}</li> }
                  </ul>
                }
                @if (g.evidencias_esperadas.length) {
                  <div class="guidance-sub">Evidências esperadas</div>
                  <ul class="guidance-list">
                    @for (e of g.evidencias_esperadas; track e) { <li>{{ e }}</li> }
                  </ul>
                }
                @if (g.nota) { <div class="guidance-note">{{ g.nota }}</div> }
              </div>
            } @else {
              <div class="guidance-empty">Sem orientação disponível para este item.</div>
            }

            <div class="evidence-block">
              <div class="evidence-head">
                <span>Evidências anexadas</span>
                @if (evidenceLoading()) { <span class="mini-loading">Carregando...</span> }
              </div>

              @if (!evidenceLoading() && evidences().length) {
                <div class="evidence-list">
                  @for (ev of evidences(); track ev.id) {
                    <div class="evidence-row">
                      <div class="evidence-meta">
                        <strong>{{ ev.title }}</strong>
                        <span>{{ ev.file_name }} · {{ formatBytes(ev.size_bytes) }} · {{ classificationLabel(ev.classification) }}</span>
                        @if (ev.description) { <p>{{ ev.description }}</p> }
                        <span class="evidence-foot">
                          {{ formatDate(ev.uploaded_at) }} · hash {{ shortHash(ev.content_hash) }}
                        </span>
                      </div>
                      <div class="evidence-actions">
                        @if (ev.can_download) {
                          <button
                            type="button"
                            class="icon-action icon-action--download"
                            (click)="downloadEvidence(ev)"
                            [disabled]="evidenceDownloadingId() === ev.id"
                            aria-label="Baixar evidencia"
                            title="Baixar evidência"
                          >
                            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                              <path d="M12 3v10"></path>
                              <path d="m8 9 4 4 4-4"></path>
                              <path d="M5 18h14"></path>
                            </svg>
                          </button>
                        }
                        @if (canManage()) {
                          <button
                            type="button"
                            class="icon-action icon-action--history"
                            (click)="openEvidenceHistory(ev)"
                            aria-label="Historico da evidencia"
                            title="Histórico"
                          >
                            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                              <path d="M3 12a9 9 0 1 0 3-6.7"></path>
                              <path d="M3 4v5h5"></path>
                              <path d="M12 7v5l3 2"></path>
                            </svg>
                          </button>
                          <button
                            type="button"
                            class="icon-action icon-action--replace"
                            (click)="openReplaceEvidence(ev)"
                            aria-label="Substituir evidencia"
                            title="Substituir"
                          >
                            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                              <path d="M20 7v5h-5"></path>
                              <path d="M4 17v-5h5"></path>
                              <path d="M18.2 12A6.5 6.5 0 0 0 7 7.4L4 12"></path>
                              <path d="M5.8 12A6.5 6.5 0 0 0 17 16.6L20 12"></path>
                            </svg>
                          </button>
                          <button
                            type="button"
                            class="icon-action icon-action--danger icon-action--delete"
                            (click)="inactivateEvidence(ev)"
                            [disabled]="evidenceInactivatingId() === ev.id"
                            aria-label="Inativar evidencia"
                            title="Inativar"
                          >
                            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                              <path d="M4 7h16"></path>
                              <path d="M10 11v6"></path>
                              <path d="M14 11v6"></path>
                              <path d="M6 7l1 13h10l1-13"></path>
                              <path d="M9 7V4h6v3"></path>
                            </svg>
                          </button>
                        }
                      </div>
                    </div>
                  }
                </div>
              } @else if (!evidenceLoading()) {
                <div class="evidence-empty">Nenhuma evidência anexada ainda.</div>
              }

              @if (canManage()) {
                <div class="evidence-upload">
                  <input type="file" class="file-input" (change)="onEvidenceFileSelected($event)" />
                  <p-select
                    [options]="classificationOptions"
                    [formControl]="evidenceClassification"
                    optionLabel="label"
                    optionValue="value"
                    styleClass="wtn-panel-select"
                  />
                  <textarea
                    pTextarea
                    [formControl]="evidenceDescription"
                    rows="2"
                    placeholder="Descrição curta"
                  ></textarea>
                  <p-button
                    label="Adicionar evidência"
                    icon="pi pi-paperclip"
                    (onClick)="uploadEvidence()"
                    [loading]="evidenceUploading()"
                  />
                </div>
              }
            </div>

            <div class="panel-field">
              <label>Status da avaliação</label>
              <p-select
                [options]="statusOptions"
                [formControl]="editStatus"
                optionLabel="label"
                optionValue="value"
                styleClass="wtn-panel-select"
              />
            </div>

            <div class="panel-grid">
              <div class="panel-field">
                <label>Prioridade</label>
                <p-select
                  [options]="priorityOptions"
                  [formControl]="editPriority"
                  optionLabel="label"
                  optionValue="value"
                  placeholder="Selecione"
                  [showClear]="true"
                  styleClass="wtn-panel-select"
                />
              </div>
              <div class="panel-field">
                <label>Responsável</label>
                <input pInputText [formControl]="editResponsible" placeholder="Nome ou área" />
              </div>
            </div>

            @if (editStatus.value === 'not_applicable') {
              <div class="panel-field">
                <label>Justificativa de exclusão *</label>
                <textarea
                  pTextarea
                  [formControl]="editJustification"
                  rows="3"
                  placeholder="Por que este controle não se aplica?"
                ></textarea>
              </div>
            }

            <div class="panel-field">
              <label>Constatações & ações</label>
              <textarea
                pTextarea
                [formControl]="editFindings"
                rows="4"
                placeholder="Registre constatações, evidências e observações."
              ></textarea>
            </div>

            <div class="panel-field">
              <label>Ações necessárias</label>
              <textarea
                pTextarea
                [formControl]="editActions"
                rows="3"
                placeholder="O que precisa ser feito?"
              ></textarea>
            </div>

            <div class="assignment-timeline">
              <div class="timeline-title">Condução atribuível</div>
              @if (assignments().length) {
                @for (a of assignments().slice(0, 2); track a.id) {
                  <div class="timeline-item">
                    <span class="timeline-dot"></span>
                    <div>
                      <strong>{{ assignmentStatusLabel(a.status) }}</strong>
                      <span>{{ assignmentActor(a) }}</span>
                    </div>
                  </div>
                }
              } @else {
                <div class="timeline-item">
                  <span class="timeline-dot timeline-dot--muted"></span>
                  <div>
                    <strong>Sem condução atribuída</strong>
                    <span>Use o botão acima para definir responsável.</span>
                  </div>
                </div>
              }
            </div>

            <div class="panel-actions">
              @if (canManage()) {
                <p-button label="Salvar" (onClick)="saveItem(it)" [loading]="saving()" />
              }
              <p-button label="Cancelar" severity="secondary" (onClick)="resetSelectedItem()" />
            </div>
          } @else {
            <div class="panel-empty">
              <strong>Selecione um controle</strong>
              <span>A edição aparece aqui, mantendo a matriz sempre visível.</span>
            </div>
          }
        </aside>
      </section>

      <p-dialog
        header="Atribuir condução"
        [(visible)]="assignDialogVisible"
        [style]="{ width: '480px' }"
        [modal]="true"
      >
        <div class="assign-form">
          <div class="panel-field">
            <label>E-mail do responsável</label>
            <input pInputText [(ngModel)]="assignEmail" placeholder="email@exemplo.com" />
            <small>Deixe vazio para atribuir a você mesmo.</small>
          </div>
          <div class="panel-field">
            <label>Escopo</label>
            <p-select
              [options]="scopeOptions"
              [(ngModel)]="assignScope"
              optionLabel="label"
              optionValue="value"
              styleClass="wtn-panel-select"
            />
          </div>
          <div class="panel-field">
            <label>Instruções</label>
            <textarea
              pTextarea
              [(ngModel)]="assignInstructions"
              rows="2"
              placeholder="Instruções para o responsável..."
            ></textarea>
          </div>
        </div>
        <ng-template pTemplate="footer">
          <p-button label="Cancelar" severity="secondary" (onClick)="assignDialogVisible = false" />
          <p-button label="Atribuir" icon="pi pi-check" (onClick)="createAssignment()" [loading]="assigning()" />
        </ng-template>
      </p-dialog>

      <p-dialog
        header="Substituir evidência"
        [(visible)]="evidenceReplaceDialogVisible"
        [style]="{ width: '460px' }"
        [modal]="true"
      >
        <div class="assign-form">
          <div class="panel-field">
            <label>Arquivo</label>
            <input type="file" class="file-input" (change)="onReplaceFileSelected($event)" />
          </div>
          <div class="panel-field">
            <label>Classificação</label>
            <p-select
              [options]="classificationOptions"
              [formControl]="replaceClassification"
              optionLabel="label"
              optionValue="value"
              styleClass="wtn-panel-select"
            />
          </div>
          <div class="panel-field">
            <label>Descrição</label>
            <textarea pTextarea [formControl]="replaceDescription" rows="2"></textarea>
          </div>
        </div>
        <ng-template pTemplate="footer">
          <p-button label="Cancelar" severity="secondary" (onClick)="evidenceReplaceDialogVisible = false" />
          <p-button
            label="Substituir"
            icon="pi pi-refresh"
            (onClick)="replaceEvidence()"
            [disabled]="!replaceEvidenceFile()"
            [loading]="evidenceUploading()"
          />
        </ng-template>
      </p-dialog>

      <p-dialog
        header="Histórico da evidência"
        [(visible)]="evidenceHistoryDialogVisible"
        [style]="{ width: '560px' }"
        [modal]="true"
      >
        @if (evidenceHistoryLoading()) {
          <div class="history-loading">Carregando...</div>
        } @else if (evidenceHistory(); as h) {
          <div class="history-section">
            <div class="history-title">Versões</div>
            @for (version of h.versions; track version.id) {
              <div class="history-row">
                <strong>v{{ version.version_number }} {{ version.is_current ? '· atual' : '' }}</strong>
                <span>{{ version.file_name }} · {{ classificationLabel(version.classification) }} · {{ formatBytes(version.size_bytes) }}</span>
                <span>hash {{ shortHash(version.content_hash) }} · {{ formatDate(version.uploaded_at) }}</span>
              </div>
            }
          </div>
          <div class="history-section">
            <div class="history-title">Eventos</div>
            @for (event of h.events; track event.id) {
              <div class="history-row">
                <strong>{{ event.event_type }}</strong>
                <span>{{ event.outcome }} · {{ formatDate(event.occurred_at) }}</span>
              </div>
            }
          </div>
        }
      </p-dialog>
    }
  `,
  styles: [`
    :host {
      display: block;
    }

    .gap-matrix-header {
      margin-bottom: 16px;
    }

    .document-tools {
      display: grid;
      gap: 14px;
      grid-template-columns: minmax(0, 1.2fr) minmax(280px, .8fr);
      margin-bottom: 16px;
    }

    .matrix-loading {
      align-items: center;
      background: var(--wtn-card);
      border: 1px solid var(--wtn-border);
      border-radius: var(--wtn-r-lg);
      color: var(--wtn-text-2);
      display: flex;
      gap: 12px;
      padding: 24px;
    }

    .gap-matrix-shell {
      background: var(--wtn-card);
      border: 1px solid var(--wtn-border);
      border-radius: var(--wtn-r-lg);
      display: grid;
      grid-template-columns: minmax(0, 1fr) 348px;
      min-height: 560px;
      overflow: hidden;
    }

    .gap-table-panel {
      min-width: 0;
      overflow: auto;
    }

    .gap-table {
      border-collapse: collapse;
      font-size: 12.5px;
      min-width: 760px;
      width: 100%;
    }

    .gap-table th {
      background: var(--wtn-surface-2);
      border-bottom: 1px solid var(--wtn-border);
      color: var(--wtn-muted);
      font-size: 10px;
      font-weight: 600;
      letter-spacing: .06em;
      padding: 8px 12px;
      text-align: left;
      text-transform: uppercase;
    }

    .gap-table td {
      border-bottom: 1px solid var(--wtn-surface-2);
      padding: 10px 12px;
      vertical-align: middle;
    }

    .col-ref {
      padding-left: 16px !important;
      width: 84px;
    }

    .col-status {
      width: 170px;
    }

    .col-priority {
      width: 106px;
    }

    .col-resp {
      padding-right: 16px !important;
      width: 64px;
    }

    .group-row td {
      background: var(--wtn-bg);
      border-bottom: 1px solid var(--wtn-border);
      padding: 9px 16px;
    }

    .group-label {
      align-items: center;
      display: flex;
      gap: 9px;
    }

    .group-label strong {
      color: var(--wtn-text);
      font-size: 12px;
    }

    .group-label span:last-child {
      color: var(--wtn-muted);
      font-size: 11px;
    }

    .chevron {
      color: var(--wtn-text-2);
      font-size: 16px;
      line-height: 1;
    }

    .matrix-row {
      background: var(--wtn-surface);
      cursor: pointer;
      transition: background .12s;
    }

    .matrix-row:hover {
      background: var(--wtn-surface-2);
    }

    .matrix-row--selected,
    .matrix-row--selected:hover {
      background: var(--wtn-primary-soft);
    }

    .ref-cell {
      color: var(--wtn-text-2);
      font-family: var(--wtn-font-mono);
      font-size: 11.5px;
      padding-left: 16px !important;
    }

    .name-cell {
      color: var(--wtn-text);
      font-weight: 500;
    }

    .priority-text {
      font-weight: 700;
    }

    .muted-dash {
      color: var(--wtn-muted);
      font-weight: 700;
    }

    .assignee-avatar {
      align-items: center;
      background: var(--wtn-primary-soft);
      border-radius: 50%;
      color: var(--wtn-primary);
      display: inline-flex;
      font-size: 9.5px;
      font-weight: 700;
      height: 24px;
      justify-content: center;
      width: 24px;
    }

    .gap-edit-panel {
      background: var(--wtn-surface);
      border-left: 1px solid var(--wtn-border);
      display: flex;
      flex-direction: column;
      gap: 16px;
      padding: 20px;
    }

    .panel-title-row {
      align-items: flex-start;
      display: flex;
      gap: 10px;
      justify-content: space-between;
    }

    .panel-ref {
      color: var(--wtn-primary);
      font-family: var(--wtn-font-mono);
      font-size: 12px;
      font-weight: 600;
      margin-bottom: 3px;
    }

    .panel-title-row h2 {
      color: var(--wtn-text);
      font-size: 15px;
      font-weight: 600;
      line-height: 1.3;
      margin: 0;
    }

    .panel-close {
      align-items: center;
      background: var(--wtn-surface-2);
      border: 0;
      border-radius: var(--wtn-r-md);
      color: var(--wtn-text-2);
      cursor: pointer;
      display: flex;
      flex: none;
      font-size: 18px;
      height: 28px;
      justify-content: center;
      line-height: 1;
      width: 28px;
    }

    .panel-grid {
      display: grid;
      gap: 12px;
      grid-template-columns: 1fr 1fr;
    }

    .panel-field {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .panel-field label,
    .timeline-title {
      color: var(--wtn-text-2);
      font-size: 11.5px;
      font-weight: 500;
    }

    .timeline-title {
      color: var(--wtn-muted);
      font-weight: 600;
      letter-spacing: .05em;
      margin-bottom: 12px;
      text-transform: uppercase;
    }

    .panel-field input,
    .panel-field textarea {
      background: var(--wtn-surface);
      border: 1px solid var(--wtn-border-strong);
      border-radius: var(--wtn-r-md);
      color: var(--wtn-text);
      font: inherit;
      font-size: 13px;
      padding: 8px 11px;
      width: 100%;
    }

    .panel-field textarea {
      resize: vertical;
    }

    .panel-field input:focus,
    .panel-field textarea:focus {
      border-color: var(--wtn-focus);
      box-shadow: 0 0 0 3px color-mix(in srgb, var(--wtn-focus) 26%, transparent);
      outline: 0;
    }

    .panel-field small {
      color: var(--wtn-muted);
      font-size: 11px;
    }

    ::ng-deep .wtn-panel-select {
      width: 100%;
    }

    ::ng-deep .wtn-panel-select .p-select {
      background: var(--wtn-surface);
      border-color: var(--wtn-border-strong);
      border-radius: var(--wtn-r-md);
      color: var(--wtn-text);
      min-height: 36px;
      width: 100%;
    }

    .assignment-timeline {
      margin-top: 2px;
    }

    .timeline-item {
      display: flex;
      gap: 11px;
      padding-bottom: 14px;
      position: relative;
    }

    .timeline-item::before {
      background: var(--wtn-border);
      bottom: 0;
      content: "";
      left: 5px;
      position: absolute;
      top: 15px;
      width: 2px;
    }

    .timeline-item:last-child::before {
      display: none;
    }

    .timeline-dot {
      background: var(--wtn-primary);
      border-radius: 50%;
      box-shadow: 0 0 0 3px var(--wtn-primary-soft);
      flex: none;
      height: 11px;
      margin-top: 3px;
      width: 11px;
    }

    .timeline-dot--muted {
      background: var(--wtn-neutral);
      box-shadow: none;
    }

    .timeline-item strong {
      color: var(--wtn-text);
      display: block;
      font-size: 12.5px;
      font-weight: 600;
    }

    .timeline-item span:last-child {
      color: var(--wtn-muted);
      display: block;
      font-size: 11px;
      margin-top: 2px;
    }

    .panel-actions {
      display: flex;
      gap: 9px;
      margin-top: auto;
      padding-top: 6px;
    }

    .panel-actions p-button:first-child {
      flex: 1;
    }

    .panel-empty {
      align-items: center;
      color: var(--wtn-text-2);
      display: flex;
      flex: 1;
      flex-direction: column;
      justify-content: center;
      line-height: 1.5;
      text-align: center;
    }

    .panel-empty strong {
      color: var(--wtn-text);
      font-size: 14px;
    }

    .table-empty {
      color: var(--wtn-text-2);
      padding: 24px !important;
      text-align: center;
    }

    /* Orientação de avaliação (read-only) no painel */
    /* Legenda global (status/prioridade) */
    .wtn-legend {
      background: var(--wtn-card);
      border: 1px solid var(--wtn-border);
      border-radius: var(--wtn-r-lg);
      box-shadow: var(--wtn-e1);
      margin-bottom: 14px;
      padding: 10px 16px;
    }
    .wtn-legend summary {
      color: var(--wtn-text);
      cursor: pointer;
      font-size: 12.5px;
      font-weight: 600;
    }
    .legend-grid {
      display: grid;
      gap: 18px;
      grid-template-columns: 1fr 1fr;
      margin-top: 12px;
    }
    .legend-h {
      color: var(--wtn-muted);
      font-size: 10.5px;
      font-weight: 600;
      letter-spacing: .05em;
      margin-bottom: 6px;
      text-transform: uppercase;
    }
    .legend-row {
      font-size: 12px;
      margin-bottom: 6px;
    }
    .legend-row strong { color: var(--wtn-text); margin-right: 6px; }
    .legend-row span { color: var(--wtn-text-2); }

    @media (max-width: 760px) {
      .legend-grid { grid-template-columns: 1fr; }
    }

    .assign-form {
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    @media (max-width: 1100px) {
      .document-tools {
        grid-template-columns: 1fr;
      }

      .gap-matrix-shell {
        grid-template-columns: 1fr;
      }

      .gap-edit-panel {
        border-left: 0;
        border-top: 1px solid var(--wtn-border);
      }
    }
  `],
})
export class GapAnalysisPage implements OnInit {
  private api = inject(ApiService);
  private auth = inject(AuthStore);
  private msg = inject(MessageService);

  readonly assessment = signal<GapAssessment | null>(null);
  readonly loading = signal(true);
  protected readonly adopting = signal(false);
  protected readonly saving = signal(false);
  protected readonly editingId = signal<string | null>(null);
  protected readonly selectedItem = signal<GapAssessmentItem | null>(null);
  protected readonly showOnlyGaps = signal(false);

  protected readonly editStatus = new FormControl<GapStatus>('not_filled', { nonNullable: true });
  protected readonly editFindings = new FormControl('', { nonNullable: true });
  protected readonly editActions = new FormControl('', { nonNullable: true });
  protected readonly editPriority = new FormControl<GapPriority | null>(null);
  protected readonly editResponsible = new FormControl('', { nonNullable: true });
  protected readonly editJustification = new FormControl('', { nonNullable: true });

  protected readonly evidences = signal<GapEvidenceSummary[]>([]);
  protected readonly evidenceLoading = signal(false);
  protected readonly evidenceUploading = signal(false);
  protected readonly evidenceDownloadingId = signal<string | null>(null);
  protected readonly evidenceInactivatingId = signal<string | null>(null);
  protected readonly selectedEvidenceFile = signal<File | null>(null);
  protected readonly evidenceDescription = new FormControl('', { nonNullable: true });
  protected readonly evidenceClassification = new FormControl<Classification>('uso_interno', { nonNullable: true });
  protected readonly replacingEvidence = signal<GapEvidenceSummary | null>(null);
  protected readonly replaceEvidenceFile = signal<File | null>(null);
  protected readonly replaceDescription = new FormControl('', { nonNullable: true });
  protected readonly replaceClassification = new FormControl<Classification>('uso_interno', { nonNullable: true });
  protected readonly evidenceHistory = signal<GapEvidenceHistory | null>(null);
  protected readonly evidenceHistoryLoading = signal(false);
  protected evidenceReplaceDialogVisible = false;
  protected evidenceHistoryDialogVisible = false;

  protected readonly canManage = computed(() => hasPermission(this.auth.currentRole(), 'manage_gap'));
  protected readonly canAssign = computed(() => hasPermission(this.auth.currentRole(), 'assign_form'));

  protected readonly statusOptions = STATUS_OPTIONS;
  protected readonly priorityOptions = PRIORITY_OPTIONS;
  protected readonly classificationOptions = CLASSIFICATION_OPTIONS;

  protected readonly guidanceByRef = signal<Record<string, ItemGuidance>>({});
  protected readonly legendStatus = signal<GuidanceLegendEntry[]>([]);
  protected readonly legendPriority = signal<GuidanceLegendEntry[]>([]);
  protected readonly selectedGuidance = computed<ItemGuidance | null>(() => {
    const it = this.selectedItem();
    return it ? this.guidanceByRef()[it.ref_code] ?? null : null;
  });

  protected readonly assignments = signal<GapAssignmentItem[]>([]);
  protected readonly assigning = signal(false);
  protected assignDialogVisible = false;
  protected assignEmail = '';
  protected assignScope = 'whole';
  protected assignInstructions = '';
  protected readonly scopeOptions = [
    { label: 'Avaliação completa', value: 'whole' },
    { label: 'Organizacional', value: 'organizational' },
    { label: 'Pessoas', value: 'people' },
    { label: 'Físico', value: 'physical' },
    { label: 'Tecnológico', value: 'technological' },
  ];

  readonly totalItems = computed(() => this.assessment()?.items.length ?? 0);

  protected readonly evaluatedItems = computed(() =>
    (this.assessment()?.items ?? []).filter((item) => item.status !== 'not_filled').length,
  );

  readonly completeness = computed(() => {
    const total = this.totalItems();
    return total ? this.evaluatedItems() / total : 0;
  });

  protected readonly adherence = computed(() => {
    const relevant = (this.assessment()?.items ?? []).filter((item) =>
      ['meets', 'partial', 'not_meet'].includes(item.status),
    );
    if (!relevant.length) return null;
    return relevant.filter((item) => item.status === 'meets').length / relevant.length;
  });

  protected readonly visibleItems = computed(() => {
    const items = this.assessment()?.items ?? [];
    if (!this.showOnlyGaps()) return items;
    return items.filter((item) => ['partial', 'not_meet'].includes(item.status));
  });

  protected readonly groupedItems = computed<GapGroup[]>(() => {
    const groups = new Map<string, GapAssessmentItem[]>();
    for (const item of this.visibleItems()) {
      const key = this.groupKey(item);
      groups.set(key, [...(groups.get(key) ?? []), item]);
    }
    return [...groups.entries()]
      .sort(([a], [b]) => (GROUP_ORDER[a] ?? 99) - (GROUP_ORDER[b] ?? 99))
      .map(([key, items]) => ({
        key,
        label: GROUP_LABELS[key as GapDimension | GapTheme] ?? key,
        count: items.length,
        items,
      }));
  });

  ngOnInit() {
    this.load();
    this.loadAssignments();
    this.loadGuidance();
  }

  private loadGuidance() {
    this.api.get<GuidanceResponse>('/gap/guidance').subscribe({
      next: (g) => {
        const byRef: Record<string, ItemGuidance> = {};
        for (const it of g.items) byRef[it.ref_code] = it;
        this.guidanceByRef.set(byRef);
        this.legendStatus.set(g.legend.status);
        this.legendPriority.set(g.legend.priority);
      },
      error: () => {},
    });
  }

  protected load() {
    this.loading.set(true);
    this.api.get<GapAssessment>('/gap/assessment').subscribe({
      next: (a) => {
        this.assessment.set(a);
        this.loading.set(false);
        const selected = this.selectedItem();
        const nextSelected = selected
          ? a.items.find((item) => item.id === selected.id) ?? this.defaultSelected(a.items)
          : this.defaultSelected(a.items);
        if (nextSelected) this.selectItem(nextSelected);
      },
      error: (e) => {
        if (e.status !== 404) {
          this.msg.add({ severity: 'error', summary: 'Erro ao carregar avaliação', detail: e.message });
        }
        this.loading.set(false);
      },
    });
  }

  protected adoptCatalog() {
    this.adopting.set(true);
    this.api.post<unknown>('/gap/catalog/adopt', { seed_version: '2022.1' }).subscribe({
      next: () => {
        this.msg.add({
          severity: 'success',
          summary: 'Catálogo adotado',
          detail: 'Avaliação inicializada com o seed 2022.1.',
        });
        this.adopting.set(false);
        this.load();
      },
      error: (e) => {
        this.msg.add({ severity: 'error', summary: 'Erro', detail: e.error?.detail ?? e.message });
        this.adopting.set(false);
      },
    });
  }

  protected selectItem(item: GapAssessmentItem) {
    this.selectedItem.set(item);
    this.editingId.set(item.id);
    this.resetForm(item);
    this.loadEvidences(item.id);
  }

  protected closeDetails() {
    this.editingId.set(null);
    this.selectedItem.set(null);
    this.evidences.set([]);
  }

  protected resetSelectedItem() {
    const item = this.selectedItem();
    if (item) this.resetForm(item);
  }

  protected saveItem(item: GapAssessmentItem) {
    if (this.editStatus.value === 'not_applicable' && !this.editJustification.value.trim()) {
      this.msg.add({
        severity: 'warn',
        summary: 'Justificativa obrigatória',
        detail: 'Informe a justificativa para marcar como N/A.',
      });
      return;
    }

    this.saving.set(true);
    const body: Record<string, unknown> = {
      status: this.editStatus.value,
      findings: this.editFindings.value || null,
      actions: this.editActions.value || null,
      priority: this.editPriority.value || null,
      responsible: this.editResponsible.value || null,
      exclusion_justification:
        this.editStatus.value === 'not_applicable' ? this.editJustification.value : null,
    };

    this.api.put<GapAssessmentItem>(`/gap/assessment/items/${item.id}`, body).subscribe({
      next: (updated) => {
        this.assessment.update((a) => {
          if (!a) return a;
          return {
            ...a,
            items: a.items.map((i) => (i.id === updated.id ? updated : i)),
          };
        });
        this.selectedItem.set(updated);
        this.resetForm(updated);
        this.msg.add({ severity: 'success', summary: 'Salvo', detail: `${item.ref_code} atualizado.` });
        this.saving.set(false);
      },
      error: (e) => {
        this.msg.add({ severity: 'error', summary: 'Erro ao salvar', detail: e.error?.detail ?? e.message });
        this.saving.set(false);
      },
    });
  }

  protected loadEvidences(itemId: string) {
    this.evidenceLoading.set(true);
    this.api.get<GapEvidenceSummary[]>(`/gap/assessment/items/${itemId}/evidences`).subscribe({
      next: (list) => {
        if (this.selectedItem()?.id === itemId) {
          this.evidences.set(list);
        }
        this.evidenceLoading.set(false);
      },
      error: (e) => {
        if (this.selectedItem()?.id === itemId) {
          this.evidences.set([]);
        }
        this.msg.add({ severity: 'error', summary: 'Erro ao carregar evidências', detail: this.errorDetail(e) });
        this.evidenceLoading.set(false);
      },
    });
  }

  protected onEvidenceFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    this.selectedEvidenceFile.set(input.files?.[0] ?? null);
  }

  protected uploadEvidence() {
    const item = this.selectedItem();
    const file = this.selectedEvidenceFile();
    if (!item || !file) {
      this.msg.add({ severity: 'warn', summary: 'Arquivo obrigatório', detail: 'Selecione um arquivo.' });
      return;
    }
    const body = new FormData();
    body.append('file', file);
    body.append('classification', this.evidenceClassification.value);
    if (this.evidenceDescription.value.trim()) {
      body.append('description', this.evidenceDescription.value.trim());
    }

    this.evidenceUploading.set(true);
    this.api.postForm<GapEvidenceSummary>(`/gap/assessment/items/${item.id}/evidences`, body).subscribe({
      next: (created) => {
        this.evidences.update((list) => [created, ...list]);
        this.selectedEvidenceFile.set(null);
        this.evidenceDescription.setValue('');
        this.evidenceClassification.setValue('uso_interno');
        this.msg.add({ severity: 'success', summary: 'Evidência anexada', detail: created.file_name });
        this.evidenceUploading.set(false);
      },
      error: (e) => {
        this.msg.add({ severity: 'error', summary: 'Erro ao anexar evidência', detail: this.errorDetail(e) });
        this.evidenceUploading.set(false);
      },
    });
  }

  protected downloadEvidence(evidence: GapEvidenceSummary) {
    const item = this.selectedItem();
    if (!item) return;
    this.evidenceDownloadingId.set(evidence.id);
    this.api.getBlob(`/gap/assessment/items/${item.id}/evidences/${evidence.id}/download`).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = evidence.file_name;
        link.click();
        URL.revokeObjectURL(url);
        this.evidenceDownloadingId.set(null);
      },
      error: (e) => {
        this.msg.add({ severity: 'error', summary: 'Erro ao baixar evidência', detail: this.errorDetail(e) });
        this.evidenceDownloadingId.set(null);
      },
    });
  }

  protected openReplaceEvidence(evidence: GapEvidenceSummary) {
    this.replacingEvidence.set(evidence);
    this.replaceEvidenceFile.set(null);
    this.replaceClassification.setValue(evidence.classification);
    this.replaceDescription.setValue(evidence.description ?? '');
    this.evidenceReplaceDialogVisible = true;
  }

  protected onReplaceFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    this.replaceEvidenceFile.set(input.files?.[0] ?? null);
  }

  protected replaceEvidence() {
    const item = this.selectedItem();
    const evidence = this.replacingEvidence();
    const file = this.replaceEvidenceFile();
    if (!item || !evidence || !file) return;
    const body = new FormData();
    body.append('file', file);
    body.append('classification', this.replaceClassification.value);
    if (this.replaceDescription.value.trim()) {
      body.append('description', this.replaceDescription.value.trim());
    }
    this.evidenceUploading.set(true);
    this.api.postForm<GapEvidenceSummary>(
      `/gap/assessment/items/${item.id}/evidences/${evidence.id}/versions`,
      body,
    ).subscribe({
      next: (updated) => {
        this.evidences.update((list) => list.map((ev) => (ev.id === updated.id ? updated : ev)));
        this.evidenceReplaceDialogVisible = false;
        this.replacingEvidence.set(null);
        this.replaceEvidenceFile.set(null);
        this.msg.add({ severity: 'success', summary: 'Evidência substituída', detail: updated.file_name });
        this.evidenceUploading.set(false);
      },
      error: (e) => {
        this.msg.add({ severity: 'error', summary: 'Erro ao substituir evidência', detail: this.errorDetail(e) });
        this.evidenceUploading.set(false);
      },
    });
  }

  protected inactivateEvidence(evidence: GapEvidenceSummary) {
    const item = this.selectedItem();
    if (!item) return;
    const reason = window.prompt('Motivo da inativação');
    if (reason === null) return;
    this.evidenceInactivatingId.set(evidence.id);
    this.api.delete<void>(`/gap/assessment/items/${item.id}/evidences/${evidence.id}`, {
      reason: reason.trim() || null,
    }).subscribe({
      next: () => {
        this.evidences.update((list) => list.filter((ev) => ev.id !== evidence.id));
        this.msg.add({ severity: 'success', summary: 'Evidência inativada', detail: evidence.file_name });
        this.evidenceInactivatingId.set(null);
      },
      error: (e) => {
        this.msg.add({ severity: 'error', summary: 'Erro ao inativar evidência', detail: this.errorDetail(e) });
        this.evidenceInactivatingId.set(null);
      },
    });
  }

  protected openEvidenceHistory(evidence: GapEvidenceSummary) {
    const item = this.selectedItem();
    if (!item) return;
    this.evidenceHistoryDialogVisible = true;
    this.evidenceHistoryLoading.set(true);
    this.evidenceHistory.set(null);
    this.api.get<GapEvidenceHistory>(`/gap/assessment/items/${item.id}/evidences/${evidence.id}/history`).subscribe({
      next: (history) => {
        this.evidenceHistory.set(history);
        this.evidenceHistoryLoading.set(false);
      },
      error: (e) => {
        this.msg.add({ severity: 'error', summary: 'Erro ao carregar histórico', detail: this.errorDetail(e) });
        this.evidenceHistoryLoading.set(false);
      },
    });
  }

  protected showAssignDialog() {
    this.assignEmail = '';
    this.assignScope = 'whole';
    this.assignInstructions = '';
    this.assignDialogVisible = true;
  }

  protected createAssignment() {
    this.assigning.set(true);
    const body: Record<string, unknown> = {
      scope: this.assignScope,
      scope_theme: this.assignScope !== 'whole' ? this.assignScope : null,
    };
    if (this.assignEmail.trim()) {
      body['respondent_email'] = this.assignEmail.trim();
    } else {
      body['respondent_user_id'] = this.auth.me()?.user_id;
    }
    if (this.assignInstructions.trim()) {
      body['instructions'] = this.assignInstructions.trim();
    }
    this.api.post<GapAssignmentItem>('/gap/assignments', body).subscribe({
      next: (a) => {
        this.assignments.update((list) => [a, ...list]);
        this.msg.add({ severity: 'success', summary: 'Atribuído', detail: 'Condução atribuída com sucesso.' });
        this.assigning.set(false);
        this.assignDialogVisible = false;
      },
      error: (e) => {
        this.msg.add({ severity: 'error', summary: 'Erro', detail: e.error?.detail ?? e.message });
        this.assigning.set(false);
      },
    });
  }

  protected toggleGapFilter() {
    this.showOnlyGaps.update((value) => !value);
  }

  protected adherenceLabel(): string {
    const value = this.adherence();
    return value === null ? '—' : `${Math.round(value * 100)}%`;
  }

  statusLabel(status: GapStatus): string {
    return STATUS_LABELS[status];
  }

  protected classificationLabel(classification: Classification): string {
    return CLASSIFICATION_LABELS[classification] ?? classification;
  }

  protected formatBytes(value: number): string {
    if (value < 1024) return `${value} B`;
    if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
    return `${(value / 1024 / 1024).toFixed(1)} MB`;
  }

  protected shortHash(value: string): string {
    return value ? value.slice(0, 10) : '-';
  }

  protected formatDate(value: string): string {
    return new Intl.DateTimeFormat('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(value));
  }

  protected statusClass(status: GapStatus): string {
    return STATUS_CLASSES[status];
  }

  protected priorityLabel(priority: GapPriority): string {
    return PRIORITY_LABELS[priority];
  }

  protected priorityColor(priority: GapPriority): string {
    return PRIORITY_COLORS[priority];
  }

  protected responsibleInitials(value: string | null): string {
    if (!value?.trim()) return '-';
    return value
      .split(/[\s@.]/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0].toUpperCase())
      .join('');
  }

  protected assignmentStatusLabel(status: string): string {
    return ASSIGNMENT_STATUS_LABELS[status] ?? status;
  }

  protected assignmentActor(a: GapAssignmentItem): string {
    if (a.respondent_email) return a.respondent_email;
    if (a.respondent_user_id) return 'Membro da organização';
    return 'Sem responsável definido';
  }

  private loadAssignments() {
    this.api.get<GapAssignmentItem[]>('/gap/assignments').subscribe({
      next: (list) => this.assignments.set(list),
      error: () => {},
    });
  }

  private resetForm(item: GapAssessmentItem) {
    this.editStatus.setValue(item.status);
    this.editFindings.setValue(item.findings ?? '');
    this.editActions.setValue(item.actions ?? '');
    this.editPriority.setValue(item.priority);
    this.editResponsible.setValue(item.responsible ?? '');
    this.editJustification.setValue(item.exclusion_justification ?? '');
  }

  private defaultSelected(items: GapAssessmentItem[]): GapAssessmentItem | null {
    return (
      items.find((item) => item.status === 'not_meet' && item.priority === 'critical') ??
      items.find((item) => ['not_meet', 'partial'].includes(item.status)) ??
      items[0] ??
      null
    );
  }

  private groupKey(item: GapAssessmentItem): string {
    if (item.dimension === 'annex_a') return item.theme ?? 'annex_a';
    return item.dimension;
  }

  private errorDetail(error: unknown): string {
    if (typeof error === 'object' && error && 'error' in error) {
      const payload = (error as { error?: { detail?: string } }).error;
      if (payload?.detail) return payload.detail;
    }
    if (typeof error === 'object' && error && 'message' in error) {
      return String((error as { message?: unknown }).message);
    }
    return 'Operação não concluída.';
  }
}
