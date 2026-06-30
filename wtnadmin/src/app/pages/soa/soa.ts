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
import { EvidencePanel } from '@app/shared/evidence-panel/evidence-panel';
import { TraceabilityTimeline } from '@app/shared/traceability-timeline/traceability-timeline';
import { Soa, SoaItem, SoaImplementationStatus, SoaInclusionReason, GapTheme } from '@app/core/models';
import { DocumentHistory } from '@app/shared/document-history/document-history';
import { DocumentPreview } from '@app/shared/document-preview/document-preview';

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

const ORIGIN_LABELS: Record<string, string> = {
  risk: 'Origem: risco',
  manual: 'Origem: manual',
  'risk+manual': 'Origem: risco + manual',
  none: '',
};

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
    DocumentPreview,
    DocumentHistory,
    EvidencePanel,
    TraceabilityTimeline,
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
      <div class="document-tools">
        <app-document-preview
          [documentType]="'soa_report'"
          [sourceArtifactId]="soa()?.id ?? null"
          title="Relatorio da SoA"
        />
        <app-document-history
          [documentType]="'soa_report'"
          [sourceArtifactId]="soa()?.id ?? null"
          title="Historico da SoA"
        />
      </div>

      @if (soa()!.readiness; as r) {
        <div class="soa-kind-banner" [class.is-normative]="r.kind === 'normative'">
          <i class="pi" [class.pi-verified]="r.kind === 'normative'" [class.pi-info-circle]="r.kind !== 'normative'"></i>
          <div>
            <div class="soa-kind-banner__title">
              {{ r.kind === 'normative' ? 'SoA normativa (6.1.3 d)' : 'Pré-SoA (consolidação do Gap)' }}
            </div>
            @if (r.kind !== 'normative' && r.pending_for_normative.length) {
              <ul class="soa-kind-banner__pending">
                @for (p of r.pending_for_normative; track p) { <li>{{ p }}</li> }
              </ul>
            }
            @if (r.out_of_scope_risk_notices.length) {
              <div class="text-sm mt-1">
                Controles tratados por risco fora do Anexo A da SoA:
                <b>{{ r.out_of_scope_risk_notices.join(', ') }}</b>
              </div>
            }
          </div>
        </div>
      }

      <div class="soa-summary mb-3">
        <span>Total: <b>{{ soa()!.summary.total }}</b></span>
        <span>Aplicáveis: <b>{{ soa()!.summary.applicable }}</b></span>
        <span>Não aplicáveis: <b>{{ soa()!.summary.not_applicable }}</b></span>
        @if (soa()!.summary.divergent > 0) {
          <span class="text-orange-500">Divergentes: <b>{{ soa()!.summary.divergent }}</b></span>
        }
        @if (soa()!.summary.risk_divergent > 0) {
          <span class="text-orange-500">Divergem do risco: <b>{{ soa()!.summary.risk_divergent }}</b></span>
        }
        @if (soa()!.summary.incomplete > 0) {
          <span class="text-red-500">Incompletos: <b>{{ soa()!.summary.incomplete }}</b></span>
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
                    @if (hasRiskDivergence(item)) {
                      <p-tag value="Risco" severity="warn" pTooltip="Diverge do tratamento de risco atual" />
                    } @else if (item.divergence.length) {
                      <p-tag value="Diverge" severity="warn" pTooltip="Difere do Gap Analysis atual" />
                    }
                    @if (item.incomplete) {
                      <p-tag value="Incompleto" severity="danger" pTooltip="Aplicável sem razão de inclusão" />
                    }
                    <p-tag
                      [value]="item.applicable ? 'Aplicável' : 'N/A'"
                      [severity]="item.applicable ? 'success' : 'secondary'"
                    />
                  </div>
                </div>
                <div class="soa-item__name">{{ item.name }}</div>
                <div class="soa-item__meta">
                  @if (item.applicable && item.origin !== 'none') {
                    <span class="origin-badge" [class.origin-risk]="item.origin.includes('risk')">{{ originLabel(item.origin) }}</span>
                  }
                  @if (item.risk_links.length) {
                    <span class="risk-codes" pTooltip="Riscos tratados">{{ riskCodes(item) }}</span>
                  }
                </div>
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
            @if (gapDivergences(it).length) {
              <div class="divergence-box">
                <div class="font-semibold mb-1">Divergências com o Gap Analysis</div>
                @for (d of gapDivergences(it); track d.field) {
                  <div class="text-sm">{{ d.field }}: SoA=<b>{{ d.soa_value }}</b> · Gap=<b>{{ d.source_value }}</b></div>
                }
                @if (canManage()) {
                  <p-button label="Reconciliar com o Gap" size="small" severity="warn" [text]="true"
                    icon="pi pi-sync" (onClick)="reconcile(it, 'gap')" [loading]="saving()" />
                }
              </div>
            }
            @if (riskDivergences(it).length) {
              <div class="divergence-box divergence-box--risk">
                <div class="font-semibold mb-1">Divergências com o Tratamento de Riscos</div>
                @for (d of riskDivergences(it); track d.field) {
                  <div class="text-sm">{{ d.field }}: SoA=<b>{{ d.soa_value }}</b> · Risco=<b>{{ d.source_value }}</b></div>
                }
                @if (canManage()) {
                  <p-button label="Reconciliar com o risco" size="small" severity="warn" [text]="true"
                    icon="pi pi-sync" (onClick)="reconcile(it, 'risk')" [loading]="saving()" />
                }
              </div>
            }
            @if (it.risk_links.length) {
              <div class="text-sm"><b>Riscos tratados:</b> {{ riskCodes(it) }}</div>
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

            <!-- Evidências transversais anexadas (Feature 014) -->
            <app-evidence-panel [targetType]="'soa_item'" [targetId]="it.id" [canManage]="canManageEvidence()" title="Evidências anexadas ao controle" />
            <!-- Rastreabilidade (Feature 014) -->
            <app-traceability-timeline [targetType]="'soa_item'" [targetId]="it.id" title="Linha do tempo do controle" />
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
    .document-tools {
      display: grid;
      gap: 14px;
      grid-template-columns: minmax(0, 1.2fr) minmax(280px, .8fr);
      margin-bottom: 16px;
    }
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
    .divergence-box--risk { border-color: var(--orange-300, #f0a868); background: var(--orange-50, #fff5eb); }
    .soa-kind-banner { display: flex; gap: .6rem; align-items: flex-start; border: 1px solid var(--surface-border); border-left: 4px solid var(--text-color-secondary); border-radius: 6px; padding: .65rem .85rem; margin-bottom: 14px; background: var(--surface-50, #fafafa); }
    .soa-kind-banner.is-normative { border-left-color: var(--green-500, #22a559); background: var(--green-50, #f0fbf4); }
    .soa-kind-banner__title { font-weight: 700; }
    .soa-kind-banner__pending { margin: .25rem 0 0; padding-left: 1.1rem; font-size: .85rem; }
    .soa-item__meta { display: flex; flex-wrap: wrap; gap: .4rem; margin-top: .3rem; }
    .origin-badge { font-size: .72rem; padding: .1rem .4rem; border-radius: 4px; background: var(--surface-200, #e9e9e9); color: var(--text-color-secondary); }
    .origin-badge.origin-risk { background: var(--orange-100, #ffe8d4); color: var(--orange-700, #b3541e); }
    .risk-codes { font-size: .72rem; color: var(--text-color-secondary); }
    @media (max-width: 980px) {
      .document-tools { grid-template-columns: 1fr; }
    }
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
  canManageEvidence = computed(() => hasPermission(this.auth.currentRole(), 'manage_evidence'));

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

  reconcile(item: SoaItem, source: 'gap' | 'risk' | 'all' = 'all') {
    this.saving.set(true);
    const detail = source === 'risk' ? 'Reconciliado com o risco.' : 'Reconciliado com o Gap.';
    this.api.post<SoaItem>(`/soa/items/${item.id}/reconcile`, { fields: [], source }).subscribe({
      next: (updated) => this.applyUpdated(updated, detail),
      error: (e) => {
        this.msg.add({ severity: 'error', summary: 'Erro', detail: e.error?.detail ?? e.message });
        this.saving.set(false);
      },
    });
  }

  gapDivergences(item: SoaItem) {
    return item.divergence.filter((d) => d.source === 'gap');
  }

  riskDivergences(item: SoaItem) {
    return item.divergence.filter((d) => d.source === 'risk');
  }

  hasRiskDivergence(item: SoaItem): boolean {
    return item.divergence.some((d) => d.source === 'risk');
  }

  riskCodes(item: SoaItem): string {
    return item.risk_links.map((r) => r.risk_code).join(', ');
  }

  originLabel(origin: string): string {
    return ORIGIN_LABELS[origin] ?? origin;
  }

  private applyUpdated(updated: SoaItem, detail: string) {
    this.soa.update((s) => {
      if (!s) return s;
      const items = s.items.map((i) => (i.id === updated.id ? updated : i));
      const applicable = items.filter((i) => i.applicable).length;
      const divergent = items.filter((i) => i.divergence.length).length;
      const risk_divergent = items.filter((i) => i.divergence.some((d) => d.source === 'risk')).length;
      const incomplete = items.filter((i) => i.incomplete).length;
      return {
        ...s, items,
        summary: { total: items.length, applicable, not_applicable: items.length - applicable, divergent, risk_divergent, incomplete },
      };
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
