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
  GapAssessment,
  GapAssessmentItem,
  GapAssignmentItem,
  GapDimension,
  GapPriority,
  GapStatus,
  GapTheme,
} from '@app/core/models';

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
    }
  `,
  styles: [`
    :host {
      display: block;
    }

    .gap-matrix-header {
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

    .assign-form {
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    @media (max-width: 1100px) {
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

  protected readonly canManage = computed(() => hasPermission(this.auth.currentRole(), 'manage_gap'));
  protected readonly canAssign = computed(() => hasPermission(this.auth.currentRole(), 'assign_form'));

  protected readonly statusOptions = STATUS_OPTIONS;
  protected readonly priorityOptions = PRIORITY_OPTIONS;

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
  }

  protected closeDetails() {
    this.editingId.set(null);
    this.selectedItem.set(null);
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
}
