import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MessageService } from 'primeng/api';
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
import { Soa, SoaItem, SoaImplementationStatus, SoaInclusionReason, GapTheme } from '@app/core/models';

const STATUS_LABELS: Record<string, string> = {
  implemented: 'Implementado',
  in_progress: 'Em andamento',
  planned: 'Planejado',
  not_started: 'Não iniciado',
  not_applicable: 'Não aplicável',
};

const REASONS: { label: string; value: SoaInclusionReason }[] = [
  { label: 'Tratamento de risco', value: 'risk_treatment' },
  { label: 'Legal/Regulatório', value: 'legal' },
  { label: 'Contratual', value: 'contractual' },
  { label: 'Boa prática/Negócio', value: 'best_practice' },
];

const THEME_LABELS: Record<string, string> = {
  organizational: 'A.5 — Organizacional',
  people: 'A.6 — Pessoas',
  physical: 'A.7 — Físico',
  technological: 'A.8 — Tecnológico',
};

const THEME_ORDER: GapTheme[] = ['organizational', 'people', 'physical', 'technological'];

@Component({
  selector: 'app-soa',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    ReactiveFormsModule,
    RouterLink,
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
      <h2>Declaração de Aplicabilidade (SoA)</h2>
      <div class="flex gap-2">
        <a routerLink="../soa-versions">
          <p-button label="Versões" icon="pi pi-file" severity="secondary" />
        </a>
        @if (canManage()) {
          <p-button
            label="Consolidar do Gap"
            icon="pi pi-sync"
            (onClick)="consolidate()"
            [loading]="consolidating()"
            pTooltip="Gera/atualiza a SoA a partir da avaliação corrente do Gap Analysis"
          />
        }
      </div>
    </div>

    @if (loading()) {
      <div class="p-4 text-center">Carregando SoA…</div>
    } @else if (!soa()) {
      <p-card>
        <div class="text-center p-4">
          <p class="mb-4">Nenhuma SoA encontrada. Consolide a partir do Gap Analysis para iniciar.</p>
          @if (canManage()) {
            <p-button label="Consolidar do Gap" icon="pi pi-sync" (onClick)="consolidate()" [loading]="consolidating()" />
          }
        </div>
      </p-card>
    } @else {
      <div class="soa-summary mb-3">
        <span>Total: <b>{{ soa()!.summary.total }}</b></span>
        <span>Aplicáveis: <b>{{ soa()!.summary.applicable }}</b></span>
        <span>Não aplicáveis: <b>{{ soa()!.summary.not_applicable }}</b></span>
        @if (soa()!.summary.divergent > 0) {
          <span class="text-orange-500">Divergentes: <b>{{ soa()!.summary.divergent }}</b></span>
        }
      </div>

      @for (theme of themes(); track theme) {
        <p-card [header]="themeLabel(theme)" styleClass="mb-3">
          <div class="soa-grid">
            @for (item of itemsByTheme()[theme]; track item.id) {
              <div class="soa-item" (click)="selectItem(item)">
                <div class="soa-item__header">
                  <span class="soa-item__ref">{{ item.ref_code }}</span>
                  <div class="flex gap-1">
                    @if (item.divergence.length) {
                      <p-tag value="Diverge" severity="warn" pTooltip="Difere do Gap Analysis atual" />
                    }
                    <p-tag
                      [value]="item.applicable ? 'Aplicável' : 'N/A'"
                      [severity]="item.applicable ? 'success' : 'secondary'"
                    />
                  </div>
                </div>
                <div class="soa-item__name">{{ item.name }}</div>
                @if (item.implementation_status) {
                  <div class="soa-item__status">{{ statusLabel(item.implementation_status) }}</div>
                }
              </div>
            }
          </div>
        </p-card>
      }

      <!-- Dialog de edição -->
      <p-dialog
        [header]="selectedItem()?.ref_code + ' — ' + selectedItem()?.name"
        [(visible)]="dialogVisible"
        [style]="{ width: '680px' }"
        [modal]="true"
      >
        @if (selectedItem(); as it) {
          <div class="flex flex-col gap-3">
            @if (it.divergence.length) {
              <div class="divergence-box">
                <div class="font-semibold mb-1">Divergências com o Gap Analysis</div>
                @for (d of it.divergence; track d.field) {
                  <div class="text-sm">{{ d.field }}: SoA=<b>{{ d.soa_value }}</b> · Gap=<b>{{ d.gap_value }}</b></div>
                }
                @if (canManage()) {
                  <p-button label="Reconciliar com o Gap" size="small" severity="warn" [text]="true"
                    icon="pi pi-sync" (onClick)="reconcile(it)" [loading]="saving()" />
                }
              </div>
            }

            <div class="flex items-center gap-2">
              <label class="font-semibold">Aplicável</label>
              <input type="checkbox" [(ngModel)]="editApplicable" />
            </div>

            @if (editApplicable) {
              <div>
                <label class="block font-semibold mb-1">Razões de inclusão *</label>
                <div class="reasons">
                  @for (r of reasons; track r.value) {
                    <label class="reason">
                      <input type="checkbox" [checked]="editReasons().includes(r.value)" (change)="toggleReason(r.value)" />
                      {{ r.label }}
                    </label>
                  }
                </div>
              </div>
              <div>
                <label class="block font-semibold mb-1">Observação da inclusão</label>
                <textarea pTextarea [formControl]="editInclusionNote" rows="2" class="w-full"></textarea>
              </div>
            } @else {
              <div>
                <label class="block font-semibold mb-1">Justificativa de exclusão *</label>
                <textarea pTextarea [formControl]="editExclusion" rows="3" class="w-full"
                  placeholder="Por que este controle não se aplica?"></textarea>
              </div>
            }

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block font-semibold mb-1">Status de implementação</label>
                <p-select [options]="statusOptions" [formControl]="editStatus" optionLabel="label"
                  optionValue="value" placeholder="—" [showClear]="true" styleClass="w-full" />
              </div>
              <div>
                <label class="block font-semibold mb-1">Responsável</label>
                <input pInputText [formControl]="editResponsible" class="w-full" />
              </div>
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block font-semibold mb-1">Riscos tratados</label>
                <input pInputText [formControl]="editRisks" placeholder="R01, R02" class="w-full" />
              </div>
              <div>
                <label class="block font-semibold mb-1">Referências de evidência</label>
                <input pInputText [formControl]="editEvidenceRefs" placeholder="POL-SI-001" class="w-full" />
              </div>
            </div>

            <div>
              <label class="block font-semibold mb-1">Evidências esperadas</label>
              <textarea pTextarea [formControl]="editExpectedEvidence" rows="2" class="w-full"></textarea>
            </div>
            <div>
              <label class="block font-semibold mb-1">Observações</label>
              <textarea pTextarea [formControl]="editObservations" rows="2" class="w-full"></textarea>
            </div>
          </div>

          <ng-template pTemplate="footer">
            <p-button label="Cancelar" severity="secondary" (onClick)="closeDialog()" />
            @if (canManage()) {
              <p-button label="Salvar" icon="pi pi-check" (onClick)="saveItem(it)" [loading]="saving()" />
            }
          </ng-template>
        }
      </p-dialog>
    }
  `,
  styles: [`
    .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
    .soa-summary { display: flex; gap: 1.5rem; font-size: .9rem; }
    .soa-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: .75rem; }
    .soa-item { border: 1px solid var(--surface-border); border-radius: 6px; padding: .75rem; cursor: pointer; transition: box-shadow .2s; }
    .soa-item:hover { box-shadow: 0 0 0 2px var(--primary-color); }
    .soa-item__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: .25rem; }
    .soa-item__ref { font-weight: 700; font-size: .85rem; color: var(--text-color-secondary); }
    .soa-item__name { font-size: .9rem; }
    .soa-item__status { font-size: .8rem; color: var(--text-color-secondary); margin-top: .25rem; }
    .reasons { display: flex; flex-wrap: wrap; gap: .75rem; }
    .reason { display: flex; align-items: center; gap: .35rem; font-size: .9rem; }
    .divergence-box { border: 1px solid var(--yellow-300, #f5d76e); background: var(--yellow-50, #fffbe6); border-radius: 6px; padding: .6rem .75rem; }
  `],
})
export class SoaPage implements OnInit {
  private api = inject(ApiService);
  private auth = inject(AuthStore);
  private msg = inject(MessageService);

  soa = signal<Soa | null>(null);
  loading = signal(true);
  consolidating = signal(false);
  saving = signal(false);
  selectedItem = signal<SoaItem | null>(null);
  dialogVisible = false;

  editApplicable = true;
  editReasons = signal<SoaInclusionReason[]>([]);
  editInclusionNote = new FormControl('', { nonNullable: true });
  editExclusion = new FormControl('', { nonNullable: true });
  editStatus = new FormControl<SoaImplementationStatus | null>(null);
  editResponsible = new FormControl('', { nonNullable: true });
  editRisks = new FormControl('', { nonNullable: true });
  editEvidenceRefs = new FormControl('', { nonNullable: true });
  editExpectedEvidence = new FormControl('', { nonNullable: true });
  editObservations = new FormControl('', { nonNullable: true });

  canManage = computed(() => hasPermission(this.auth.currentRole(), 'manage_soa'));

  reasons = REASONS;
  statusOptions = Object.entries(STATUS_LABELS).map(([value, label]) => ({ label, value }));

  themes = computed<GapTheme[]>(() => {
    const present = new Set((this.soa()?.items ?? []).map((i) => i.theme).filter(Boolean) as GapTheme[]);
    return THEME_ORDER.filter((t) => present.has(t));
  });

  itemsByTheme = computed(() => {
    const map: Record<string, SoaItem[]> = {};
    for (const item of this.soa()?.items ?? []) {
      const key = item.theme ?? 'organizational';
      (map[key] ??= []).push(item);
    }
    return map;
  });

  ngOnInit() {
    this.load();
  }

  load() {
    this.loading.set(true);
    this.api.get<Soa>('/soa').subscribe({
      next: (s) => { this.soa.set(s); this.loading.set(false); },
      error: (e) => {
        if (e.status !== 404) this.msg.add({ severity: 'error', summary: 'Erro', detail: e.message });
        this.soa.set(null);
        this.loading.set(false);
      },
    });
  }

  consolidate() {
    this.consolidating.set(true);
    this.api.post<Soa>('/soa/consolidate', {}).subscribe({
      next: (s) => {
        this.soa.set(s);
        this.msg.add({ severity: 'success', summary: 'SoA consolidada', detail: 'Gerada a partir do Gap Analysis.' });
        this.consolidating.set(false);
      },
      error: (e) => {
        this.msg.add({ severity: 'error', summary: 'Erro', detail: e.error?.detail ?? e.message });
        this.consolidating.set(false);
      },
    });
  }

  selectItem(item: SoaItem) {
    this.selectedItem.set(item);
    this.editApplicable = item.applicable;
    this.editReasons.set([...item.inclusion_reasons]);
    this.editInclusionNote.setValue(item.inclusion_note ?? '');
    this.editExclusion.setValue(item.exclusion_justification ?? '');
    this.editStatus.setValue(item.implementation_status);
    this.editResponsible.setValue(item.responsible ?? '');
    this.editRisks.setValue(item.risks_treated ?? '');
    this.editEvidenceRefs.setValue(item.evidence_refs ?? '');
    this.editExpectedEvidence.setValue(item.expected_evidence ?? '');
    this.editObservations.setValue(item.observations ?? '');
    this.dialogVisible = true;
  }

  closeDialog() {
    this.dialogVisible = false;
    this.selectedItem.set(null);
  }

  toggleReason(reason: SoaInclusionReason) {
    const current = this.editReasons();
    this.editReasons.set(
      current.includes(reason) ? current.filter((r) => r !== reason) : [...current, reason],
    );
  }

  saveItem(item: SoaItem) {
    if (this.editApplicable && this.editReasons().length === 0) {
      this.msg.add({ severity: 'warn', summary: 'Razão obrigatória', detail: 'Selecione ao menos uma razão de inclusão.' });
      return;
    }
    if (!this.editApplicable && !this.editExclusion.value.trim()) {
      this.msg.add({ severity: 'warn', summary: 'Justificativa obrigatória', detail: 'Informe a justificativa de exclusão.' });
      return;
    }

    this.saving.set(true);
    const body: Record<string, unknown> = {
      applicable: this.editApplicable,
      inclusion_reasons: this.editApplicable ? this.editReasons() : [],
      inclusion_note: this.editInclusionNote.value || null,
      exclusion_justification: this.editApplicable ? null : this.editExclusion.value,
      implementation_status: this.editStatus.value || null,
      responsible: this.editResponsible.value || null,
      risks_treated: this.editRisks.value || null,
      evidence_refs: this.editEvidenceRefs.value || null,
      expected_evidence: this.editExpectedEvidence.value || null,
      observations: this.editObservations.value || null,
    };

    this.api.put<SoaItem>(`/soa/items/${item.id}`, body).subscribe({
      next: (updated) => this.applyUpdated(updated, 'Controle atualizado.'),
      error: (e) => {
        this.msg.add({ severity: 'error', summary: 'Erro ao salvar', detail: e.error?.detail ?? e.message });
        this.saving.set(false);
      },
    });
  }

  reconcile(item: SoaItem) {
    this.saving.set(true);
    this.api.post<SoaItem>(`/soa/items/${item.id}/reconcile`, { fields: [] }).subscribe({
      next: (updated) => this.applyUpdated(updated, 'Reconciliado com o Gap.'),
      error: (e) => {
        this.msg.add({ severity: 'error', summary: 'Erro', detail: e.error?.detail ?? e.message });
        this.saving.set(false);
      },
    });
  }

  private applyUpdated(updated: SoaItem, detail: string) {
    this.soa.update((s) => {
      if (!s) return s;
      const items = s.items.map((i) => (i.id === updated.id ? updated : i));
      const applicable = items.filter((i) => i.applicable).length;
      const divergent = items.filter((i) => i.divergence.length).length;
      return { ...s, items, summary: { total: items.length, applicable, not_applicable: items.length - applicable, divergent } };
    });
    this.selectedItem.set(updated);
    this.msg.add({ severity: 'success', summary: 'Salvo', detail });
    this.saving.set(false);
    this.closeDialog();
  }

  themeLabel(theme: string): string {
    return THEME_LABELS[theme] ?? theme;
  }

  statusLabel(s: string): string {
    return STATUS_LABELS[s] ?? s;
  }
}
