import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MessageService } from 'primeng/api';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { SelectModule } from 'primeng/select';
import { TagModule } from 'primeng/tag';
import { TextareaModule } from 'primeng/textarea';
import { TooltipModule } from 'primeng/tooltip';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { hasPermission } from '@app/core/permissions';
import { GapAssessment, GapAssessmentItem, GapAssignmentItem, GapStatus, GapDimension } from '@app/core/models';

type StatusSeverity = 'success' | 'warn' | 'danger' | 'secondary' | 'info';

const STATUS_LABELS: Record<GapStatus, string> = {
  not_filled: 'Não avaliado',
  meets: 'Atende',
  partial: 'Parcialmente atende',
  not_meet: 'Não atende',
  not_applicable: 'N/A',
};

const STATUS_SEVERITY: Record<GapStatus, StatusSeverity> = {
  not_filled: 'secondary',
  meets: 'success',
  partial: 'warn',
  not_meet: 'danger',
  not_applicable: 'info',
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

const DIM_LABELS: Record<GapDimension, string> = {
  clause: 'Cláusulas (4–10)',
  annex_a: 'Anexo A — Controles',
};

@Component({
  selector: 'app-gap-analysis',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    DatePipe,
    ReactiveFormsModule,
    FormsModule,
    ButtonModule,
    CardModule,
    DialogModule,
    InputTextModule,
    SelectModule,
    TagModule,
    TextareaModule,
    TooltipModule,
  ],
  template: `
    <div class="page-header">
      <h2>Gap Analysis — ISO/IEC 27001:2022</h2>
      @if (canManage()) {
        <p-button
          label="Adotar catálogo"
          icon="pi pi-download"
          severity="secondary"
          (onClick)="adoptCatalog()"
          [loading]="adopting()"
          pTooltip="Materializa/atualiza o catálogo da organização com o seed 2022.1"
        />
      }
    </div>

    @if (loading()) {
      <div class="p-4 text-center">Carregando avaliação…</div>
    } @else if (!assessment()) {
      <p-card>
        <div class="text-center p-4">
          <p class="mb-4">Nenhuma avaliação encontrada. Adote o catálogo ISO 27001:2022 para iniciar.</p>
          @if (canManage()) {
            <p-button
              label="Adotar catálogo 2022.1"
              icon="pi pi-download"
              (onClick)="adoptCatalog()"
              [loading]="adopting()"
            />
          }
        </div>
      </p-card>
    } @else {
      <!-- Indicador geral -->
      <div class="gap-progress-bar mb-4">
        <span class="text-sm text-color-secondary">
          Preenchimento: {{ (completeness() * 100).toFixed(0) }}%
          dos {{ totalItems() }} itens avaliados
        </span>
        <div class="progress-track mt-1">
          <div class="progress-fill" [style.width]="(completeness() * 100) + '%'"></div>
        </div>
      </div>

      <!-- Matriz por dimensão -->
      @for (dim of dimensions(); track dim) {
        <p-card [header]="dimLabel(dim)" styleClass="mb-3">
          <div class="gap-matrix">
            @for (item of itemsByDimension()[dim]; track item.id) {
              <div
                class="gap-item"
                [class.gap-item--editing]="editingId() === item.id"
                (click)="selectItem(item)"
              >
                <div class="gap-item__header">
                  <span class="gap-item__ref">{{ item.ref_code }}</span>
                  <p-tag
                    [value]="statusLabel(item.status)"
                    [severity]="statusSeverity(item.status)"
                  />
                </div>
                <div class="gap-item__name">{{ item.name }}</div>
              </div>
            }
          </div>
        </p-card>
      }

      <!-- Condução (atribuição da avaliação) -->
      @if (canAssign()) {
        <p-card header="Condução da Avaliação" styleClass="mt-4">
          <div class="flex justify-between items-center mb-3">
            <span class="text-sm text-color-secondary">Atribuições de condução da avaliação gap</span>
            <p-button
              label="Atribuir condução"
              icon="pi pi-user-plus"
              size="small"
              (onClick)="showAssignDialog()"
            />
          </div>
          @if (assignments().length === 0) {
            <p class="text-color-secondary text-sm">Nenhuma atribuição ainda.</p>
          } @else {
            @for (a of assignments(); track a.id) {
              <div class="assign-row">
                <div class="assign-row__meta">
                  <p-tag [value]="a.status" [severity]="assignSeverity(a.status)" />
                  @if (a.scope_theme) {
                    <span class="text-sm text-color-secondary">Tema: {{ a.scope_theme }}</span>
                  }
                </div>
                <div class="text-sm">
                  {{ a.respondent_email ?? 'membro' }}
                  @if (a.deadline_at) { · prazo {{ a.deadline_at | date:'dd/MM/yyyy' }} }
                </div>
                <div class="flex gap-1 mt-1">
                  @if (a.status === 'pending') {
                    <p-button icon="pi pi-times" [text]="true" size="small" severity="secondary"
                      pTooltip="Cancelar" (onClick)="cancelAssignment(a.id)" />
                  }
                </div>
              </div>
            }
          }
        </p-card>
      }

      <!-- Dialog atribuir condução -->
      <p-dialog
        header="Atribuir condução"
        [(visible)]="assignDialogVisible"
        [style]="{ width: '480px' }"
        [modal]="true"
      >
        <div class="flex flex-col gap-3">
          <div>
            <label class="block font-semibold mb-1">E-mail do responsável</label>
            <input pInputText [(ngModel)]="assignEmail" placeholder="email@exemplo.com" class="w-full" />
            <small class="text-color-secondary">Deixe vazio para atribuir a você mesmo.</small>
          </div>
          <div>
            <label class="block font-semibold mb-1">Escopo</label>
            <p-select
              [options]="scopeOptions"
              [(ngModel)]="assignScope"
              optionLabel="label"
              optionValue="value"
              styleClass="w-full"
            />
          </div>
          <div>
            <label class="block font-semibold mb-1">Instruções</label>
            <textarea pTextarea [(ngModel)]="assignInstructions" rows="2" class="w-full"
              placeholder="Instruções para o responsável…"></textarea>
          </div>
        </div>
        <ng-template pTemplate="footer">
          <p-button label="Cancelar" severity="secondary" (onClick)="assignDialogVisible = false" />
          <p-button label="Atribuir" icon="pi pi-check" (onClick)="createAssignment()" [loading]="assigning()" />
        </ng-template>
      </p-dialog>

      <!-- Dialog de edição -->
      <p-dialog
        [header]="selectedItem()?.ref_code + ' — ' + selectedItem()?.name"
        [(visible)]="dialogVisible"
        [style]="{ width: '640px' }"
        [modal]="true"
      >
        @if (selectedItem(); as it) {
          <div class="flex flex-col gap-3">
            <div>
              <label class="block font-semibold mb-1">Status</label>
              <p-select
                [options]="statusOptions"
                [formControl]="editStatus"
                optionLabel="label"
                optionValue="value"
                styleClass="w-full"
              />
            </div>

            @if (editStatus.value === 'not_applicable') {
              <div>
                <label class="block font-semibold mb-1">Justificativa de exclusão *</label>
                <textarea
                  pTextarea
                  [formControl]="editJustification"
                  rows="3"
                  class="w-full"
                  placeholder="Por que este controle não se aplica?"
                ></textarea>
              </div>
            }

            <div>
              <label class="block font-semibold mb-1">Evidências / constatações</label>
              <textarea
                pTextarea
                [formControl]="editFindings"
                rows="3"
                class="w-full"
                placeholder="Descreva o que foi encontrado…"
              ></textarea>
            </div>

            <div>
              <label class="block font-semibold mb-1">Ações necessárias</label>
              <textarea
                pTextarea
                [formControl]="editActions"
                rows="2"
                class="w-full"
                placeholder="O que precisa ser feito?"
              ></textarea>
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block font-semibold mb-1">Prioridade</label>
                <p-select
                  [options]="priorityOptions"
                  [formControl]="editPriority"
                  optionLabel="label"
                  optionValue="value"
                  placeholder="Selecione…"
                  [showClear]="true"
                  styleClass="w-full"
                />
              </div>
              <div>
                <label class="block font-semibold mb-1">Responsável</label>
                <input
                  pInputText
                  [formControl]="editResponsible"
                  placeholder="Nome ou área"
                  class="w-full"
                />
              </div>
            </div>
          </div>

          <ng-template pTemplate="footer">
            <p-button
              label="Cancelar"
              severity="secondary"
              (onClick)="closeDialog()"
            />
            @if (canManage()) {
              <p-button
                label="Salvar"
                icon="pi pi-check"
                (onClick)="saveItem(it)"
                [loading]="saving()"
              />
            }
          </ng-template>
        }
      </p-dialog>
    }
  `,
  styles: [`
    .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
    .gap-progress-bar { background: var(--surface-border); border-radius: 4px; }
    .progress-track { height: 6px; background: var(--surface-border); border-radius: 3px; overflow: hidden; }
    .progress-fill { height: 100%; background: var(--primary-color); transition: width .3s; }
    .gap-matrix { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: .75rem; }
    .gap-item {
      border: 1px solid var(--surface-border); border-radius: 6px; padding: .75rem;
      cursor: pointer; transition: box-shadow .2s;
    }
    .gap-item:hover, .gap-item--editing { box-shadow: 0 0 0 2px var(--primary-color); }
    .gap-item__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: .25rem; }
    .gap-item__ref { font-weight: 700; font-size: .85rem; color: var(--text-color-secondary); }
    .gap-item__name { font-size: .9rem; }
    .assign-row { border: 1px solid var(--surface-border); border-radius: 6px; padding: .6rem .75rem; margin-bottom: .5rem; }
    .assign-row__meta { display: flex; gap: .5rem; align-items: center; margin-bottom: .2rem; }
  `],
})
export class GapAnalysisPage implements OnInit {
  private api = inject(ApiService);
  private auth = inject(AuthStore);
  private msg = inject(MessageService);

  assessment = signal<GapAssessment | null>(null);
  loading = signal(true);
  adopting = signal(false);
  saving = signal(false);
  editingId = signal<string | null>(null);
  selectedItem = signal<GapAssessmentItem | null>(null);
  dialogVisible = false;

  editStatus = new FormControl<GapStatus>('not_filled', { nonNullable: true });
  editFindings = new FormControl('', { nonNullable: true });
  editActions = new FormControl('', { nonNullable: true });
  editPriority = new FormControl<string | null>(null);
  editResponsible = new FormControl('', { nonNullable: true });
  editJustification = new FormControl('', { nonNullable: true });

  canManage = computed(() => hasPermission(this.auth.currentRole(), 'manage_gap'));
  canAssign = computed(() => hasPermission(this.auth.currentRole(), 'assign_form'));

  statusOptions = STATUS_OPTIONS;
  priorityOptions = PRIORITY_OPTIONS;

  assignments = signal<GapAssignmentItem[]>([]);
  assigning = signal(false);
  assignDialogVisible = false;
  assignEmail = '';
  assignScope = 'whole';
  assignInstructions = '';
  scopeOptions = [
    { label: 'Avaliação completa', value: 'whole' },
    { label: 'Organizacional', value: 'organizational' },
    { label: 'Pessoas', value: 'people' },
    { label: 'Físico', value: 'physical' },
    { label: 'Tecnológico', value: 'technological' },
  ];

  totalItems = computed(() => this.assessment()?.items.length ?? 0);
  completeness = computed(() => {
    const items = this.assessment()?.items ?? [];
    const filled = items.filter((i) => i.status !== 'not_filled').length;
    return items.length ? filled / items.length : 0;
  });

  dimensions = computed<GapDimension[]>(() => {
    const dims = new Set(
      (this.assessment()?.items ?? []).map((i) => i.dimension as GapDimension),
    );
    return (['clause', 'annex_a'] as GapDimension[]).filter((d) => dims.has(d));
  });

  itemsByDimension = computed(() => {
    const map: Record<string, GapAssessmentItem[]> = {};
    for (const item of this.assessment()?.items ?? []) {
      (map[item.dimension] ??= []).push(item);
    }
    return map;
  });

  ngOnInit() {
    this.load();
    this.loadAssignments();
  }

  load() {
    this.loading.set(true);
    this.api.get<GapAssessment>('/gap/assessment').subscribe({
      next: (a) => { this.assessment.set(a); this.loading.set(false); },
      error: (e) => {
        if (e.status !== 404) this.msg.add({ severity: 'error', summary: 'Erro ao carregar avaliação', detail: e.message });
        this.loading.set(false);
      },
    });
  }

  adoptCatalog() {
    this.adopting.set(true);
    this.api.post<unknown>('/gap/catalog/adopt', { seed_version: '2022.1' }).subscribe({
      next: () => {
        this.msg.add({ severity: 'success', summary: 'Catálogo adotado', detail: 'Avaliação inicializada com o seed 2022.1.' });
        this.adopting.set(false);
        this.load();
      },
      error: (e) => {
        this.msg.add({ severity: 'error', summary: 'Erro', detail: e.error?.detail ?? e.message });
        this.adopting.set(false);
      },
    });
  }

  selectItem(item: GapAssessmentItem) {
    this.selectedItem.set(item);
    this.editingId.set(item.id);
    this.editStatus.setValue(item.status);
    this.editFindings.setValue(item.findings ?? '');
    this.editActions.setValue(item.actions ?? '');
    this.editPriority.setValue(item.priority);
    this.editResponsible.setValue(item.responsible ?? '');
    this.editJustification.setValue(item.exclusion_justification ?? '');
    this.dialogVisible = true;
  }

  closeDialog() {
    this.dialogVisible = false;
    this.editingId.set(null);
    this.selectedItem.set(null);
  }

  saveItem(item: GapAssessmentItem) {
    if (this.editStatus.value === 'not_applicable' && !this.editJustification.value.trim()) {
      this.msg.add({ severity: 'warn', summary: 'Justificativa obrigatória', detail: 'Informe a justificativa para marcar como N/A.' });
      return;
    }

    this.saving.set(true);
    const body: Record<string, unknown> = {
      status: this.editStatus.value,
      findings: this.editFindings.value || null,
      actions: this.editActions.value || null,
      priority: this.editPriority.value || null,
      responsible: this.editResponsible.value || null,
      exclusion_justification: this.editStatus.value === 'not_applicable' ? this.editJustification.value : null,
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
        this.msg.add({ severity: 'success', summary: 'Salvo', detail: `${item.ref_code} atualizado.` });
        this.saving.set(false);
        this.closeDialog();
      },
      error: (e) => {
        this.msg.add({ severity: 'error', summary: 'Erro ao salvar', detail: e.error?.detail ?? e.message });
        this.saving.set(false);
      },
    });
  }

  private loadAssignments() {
    this.api.get<GapAssignmentItem[]>('/gap/assignments').subscribe({
      next: (list) => this.assignments.set(list),
      error: () => {},
    });
  }

  showAssignDialog() {
    this.assignEmail = '';
    this.assignScope = 'whole';
    this.assignInstructions = '';
    this.assignDialogVisible = true;
  }

  createAssignment() {
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

  cancelAssignment(id: string) {
    this.api.post<GapAssignmentItem>(`/gap/assignments/${id}/cancel`, {}).subscribe({
      next: (a) => {
        this.assignments.update((list) => list.map((x) => (x.id === a.id ? a : x)));
        this.msg.add({ severity: 'info', summary: 'Cancelado' });
      },
      error: (e) => this.msg.add({ severity: 'error', summary: 'Erro', detail: e.error?.detail ?? e.message }),
    });
  }

  assignSeverity(status: string): 'info' | 'warn' | 'success' | 'danger' | 'secondary' {
    const map: Record<string, 'info' | 'warn' | 'success' | 'danger' | 'secondary'> = {
      pending: 'info', in_progress: 'warn', submitted: 'success', cancelled: 'secondary',
    };
    return map[status] ?? 'secondary';
  }

  dimLabel(dim: GapDimension): string {
    return DIM_LABELS[dim] ?? dim;
  }

  statusLabel(s: GapStatus): string {
    return STATUS_LABELS[s] ?? s;
  }

  statusSeverity(s: GapStatus): StatusSeverity {
    return STATUS_SEVERITY[s] ?? 'secondary';
  }
}
