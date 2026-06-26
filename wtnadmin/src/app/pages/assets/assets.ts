import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { FormsModule, NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { SelectModule } from 'primeng/select';
import { TableModule } from 'primeng/table';
import { TextareaModule } from 'primeng/textarea';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { hasPermission } from '@app/core/permissions';
import {
  AssetContextSource,
  AssetItem,
  AssetSummary,
  AssetType,
  CiaLevel,
} from '@app/core/models';
import {
  ASSET_TYPE_LABELS,
  CIA_LABELS,
  REVIEW_STATUS_LABELS,
  SCOPE_STATUS_LABELS,
} from '@app/pages/assets/asset-labels';

interface Option<T = string> { label: string; value: T; }
interface MemberRow { user_id: string; full_name: string; email: string; }

@Component({
  selector: 'app-assets',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    RouterLink, FormsModule, ReactiveFormsModule, ButtonModule, DialogModule,
    InputTextModule, SelectModule, TableModule, TextareaModule,
  ],
  template: `
    <header class="wtn-page-header">
      <div>
        <h1 class="wtn-page-title">Ativos e Processos</h1>
        <p class="wtn-page-desc">Inventário do escopo do SGSI — ativos, processos, fornecedores e mais.</p>
      </div>
      <div class="wtn-page-actions">
        <a routerLink="../assets-dashboard"><p-button label="Dashboard" icon="pi pi-chart-bar" severity="secondary" /></a>
        @if (canManage() && contextSources().length) {
          <p-select [options]="contextOptions()" optionLabel="label" optionValue="value"
            placeholder="Criar a partir do contexto" (onChange)="fromContext($event.value)" styleClass="ctx-select" />
        }
        @if (canManage()) {
          <p-button label="Novo item" icon="pi pi-plus" (onClick)="openCreate()" />
        }
      </div>
    </header>

    <!-- Cards de resumo -->
    @if (summary(); as s) {
      <section class="kpi-grid">
        <div class="kpi"><span class="kpi-val">{{ s.total }}</span><span class="kpi-lbl">Total</span></div>
        <div class="kpi"><span class="kpi-val">{{ s.assets }}</span><span class="kpi-lbl">Ativos</span></div>
        <div class="kpi"><span class="kpi-val">{{ s.processes }}</span><span class="kpi-lbl">Processos</span></div>
        <div class="kpi"><span class="kpi-val">{{ s.suppliers }}</span><span class="kpi-lbl">Fornecedores</span></div>
        <div class="kpi"><span class="kpi-val">{{ s.in_scope }}</span><span class="kpi-lbl">No escopo</span></div>
        <div class="kpi kpi--warn"><span class="kpi-val">{{ s.critical }}</span><span class="kpi-lbl">Críticos</span></div>
        <div class="kpi kpi--warn"><span class="kpi-val">{{ s.without_responsible }}</span><span class="kpi-lbl">Sem responsável</span></div>
        <div class="kpi kpi--warn"><span class="kpi-val">{{ s.cia_incomplete }}</span><span class="kpi-lbl">CIA incompleta</span></div>
      </section>
    }

    <!-- Filtros -->
    <section class="filters">
      <input pInputText [(ngModel)]="q" (ngModelChange)="reload()" placeholder="Buscar nome, descrição, área..." class="filter-search" />
      <p-select [options]="typeOptions" optionLabel="label" optionValue="value" [(ngModel)]="fType"
        (onChange)="reload()" placeholder="Tipo" [showClear]="true" />
      <p-select [options]="scopeOptions" optionLabel="label" optionValue="value" [(ngModel)]="fScope"
        (onChange)="reload()" placeholder="Escopo" [showClear]="true" />
      <p-select [options]="ciaOptions" optionLabel="label" optionValue="value" [(ngModel)]="fCriticality"
        (onChange)="reload()" placeholder="Criticidade" [showClear]="true" />
      <p-select [options]="pendingOptions" optionLabel="label" optionValue="value" [(ngModel)]="fPending"
        (onChange)="reload()" placeholder="Pendências" [showClear]="true" />
    </section>

    <!-- Tabela -->
    <div class="wtn-card table-card">
      <p-table [value]="items()" [loading]="loading()" [paginator]="items().length > 20" [rows]="20" dataKey="id">
        <ng-template pTemplate="header">
          <tr>
            <th>Código</th><th>Nome</th><th>Tipo</th><th>Escopo</th>
            <th>Criticidade</th><th>Revisão</th><th></th>
          </tr>
        </ng-template>
        <ng-template pTemplate="body" let-item>
          <tr>
            <td class="mono">{{ item.code }}</td>
            <td>{{ item.name }}</td>
            <td>{{ typeLabel(item.item_type) }}</td>
            <td><span [class]="'wtn-tag ' + scopeClass(item.scope_status)">{{ scopeLabel(item.scope_status) }}</span></td>
            <td>{{ item.criticality ? ciaLabel(item.criticality) : '—' }}</td>
            <td><span [class]="'wtn-tag ' + reviewClass(item.review_status)">{{ reviewLabel(item.review_status) }}</span></td>
            <td class="row-action"><a [routerLink]="['../assets', item.id]"><p-button label="Abrir" icon="pi pi-arrow-right" size="small" [text]="true" /></a></td>
          </tr>
        </ng-template>
        <ng-template pTemplate="emptymessage">
          <tr><td colspan="7" class="empty-row">Nenhum item encontrado. Crie o primeiro item do inventário.</td></tr>
        </ng-template>
      </p-table>
    </div>

    <!-- Dialog de criação -->
    <p-dialog [(visible)]="dialogVisible" header="Novo item de ativo/processo" [modal]="true" [style]="{ width: '640px' }">
      <form [formGroup]="form" class="form-grid" (ngSubmit)="submit()">
        <label class="span2">Nome *
          <input pInputText formControlName="name" />
        </label>
        <label>Tipo *
          <p-select [options]="typeOptions" optionLabel="label" optionValue="value" formControlName="item_type" />
        </label>
        <label>Situação de escopo *
          <p-select [options]="scopeOptions" optionLabel="label" optionValue="value" formControlName="scope_status" />
        </label>
        <label class="span2">Descrição
          <textarea pTextarea formControlName="description" rows="2"></textarea>
        </label>
        <label>Área / unidade
          <input pInputText formControlName="business_unit" />
        </label>
        <label>Responsável
          <p-select [options]="memberOptions()" optionLabel="label" optionValue="value" formControlName="responsible_user_id" [showClear]="true" />
        </label>
        <label>Confidencialidade
          <p-select [options]="ciaOptions" optionLabel="label" optionValue="value" formControlName="confidentiality" [showClear]="true" />
        </label>
        <label>Integridade
          <p-select [options]="ciaOptions" optionLabel="label" optionValue="value" formControlName="integrity" [showClear]="true" />
        </label>
        <label>Disponibilidade
          <p-select [options]="ciaOptions" optionLabel="label" optionValue="value" formControlName="availability" [showClear]="true" />
        </label>
        <label class="checks span2">
          <span><input type="checkbox" formControlName="has_personal_data" /> Dados pessoais</span>
          <span><input type="checkbox" formControlName="has_sensitive_data" /> Dados sensíveis</span>
        </label>
        @if (form.value.scope_status === 'out_of_scope') {
          <label class="span2">Justificativa de exclusão *
            <textarea pTextarea formControlName="scope_justification" rows="2"></textarea>
          </label>
        }
        @if (errorMsg()) { <p class="form-error span2">{{ errorMsg() }}</p> }
      </form>
      <ng-template pTemplate="footer">
        <p-button label="Cancelar" severity="secondary" [text]="true" (onClick)="dialogVisible.set(false)" />
        <p-button label="Salvar" icon="pi pi-check" (onClick)="submit()" [disabled]="form.invalid || saving()" />
      </ng-template>
    </p-dialog>
  `,
  styles: [`
    :host { display: block; }
    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 12px; margin-bottom: 18px; }
    .kpi { background: var(--wtn-card); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-lg);
      padding: 14px 16px; display: flex; flex-direction: column; gap: 4px; }
    .kpi-val { font-size: 24px; font-weight: 700; color: var(--wtn-text); }
    .kpi-lbl { font-size: 11px; color: var(--wtn-muted); text-transform: uppercase; letter-spacing: .04em; }
    .kpi--warn .kpi-val { color: var(--wtn-warning); }
    .filters { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 14px; }
    .filter-search { min-width: 260px; flex: 1; }
    .table-card { background: var(--wtn-card); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-lg); overflow: hidden; }
    .mono { font-family: var(--wtn-font-mono); font-size: 12px; color: var(--wtn-text-2); }
    .row-action { text-align: right; }
    .empty-row { padding: 28px; text-align: center; color: var(--wtn-muted); }
    .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    .form-grid label { display: flex; flex-direction: column; gap: 6px; font-size: 12px; color: var(--wtn-text-2); }
    .form-grid .span2 { grid-column: 1 / -1; }
    .checks { flex-direction: row !important; gap: 20px; }
    .checks span { display: flex; align-items: center; gap: 6px; color: var(--wtn-text); }
    .form-error { color: var(--wtn-danger); font-size: 13px; margin: 0; }
  `],
})
export class AssetsPage implements OnInit {
  private api = inject(ApiService);
  private msg = inject(MessageService);
  private fb = inject(NonNullableFormBuilder);
  private store = inject(AuthStore);

  readonly items = signal<AssetItem[]>([]);
  readonly summary = signal<AssetSummary | null>(null);
  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly dialogVisible = signal(false);
  readonly errorMsg = signal<string | null>(null);
  readonly members = signal<MemberRow[]>([]);
  readonly contextSources = signal<AssetContextSource[]>([]);

  // filtros (ngModel)
  q = '';
  fType: AssetType | null = null;
  fScope: string | null = null;
  fCriticality: CiaLevel | null = null;
  fPending: string | null = null;

  readonly typeOptions: Option<AssetType>[] = (Object.keys(ASSET_TYPE_LABELS) as AssetType[])
    .map((v) => ({ label: ASSET_TYPE_LABELS[v], value: v }));
  readonly scopeOptions: Option[] = Object.entries(SCOPE_STATUS_LABELS).map(([value, label]) => ({ label, value }));
  readonly ciaOptions: Option[] = Object.entries(CIA_LABELS).map(([value, label]) => ({ label, value }));
  readonly pendingOptions: Option[] = [
    { label: 'Sem responsável', value: 'without_responsible' },
    { label: 'CIA incompleta', value: 'cia_incomplete' },
    { label: 'Revisão vencida', value: 'overdue' },
    { label: 'Gaps relacionados', value: 'linked_gap' },
  ];

  readonly memberOptions = computed<Option[]>(() =>
    this.members().map((m) => ({ label: `${m.full_name} (${m.email})`, value: m.user_id })),
  );
  readonly contextOptions = computed<Option[]>(() =>
    this.contextSources().map((s, i) => ({ label: `${s.label} — ${s.origin_type}`, value: String(i) })),
  );

  readonly form = this.fb.group({
    name: ['', Validators.required],
    item_type: ['information_asset' as AssetType, Validators.required],
    scope_status: ['under_analysis' as string, Validators.required],
    description: [''],
    business_unit: [''],
    responsible_user_id: [null as string | null],
    confidentiality: [null as CiaLevel | null],
    integrity: [null as CiaLevel | null],
    availability: [null as CiaLevel | null],
    has_personal_data: [false],
    has_sensitive_data: [false],
    scope_justification: [''],
  });

  ngOnInit(): void {
    this.reload();
    this.loadSummary();
    this.api.listUsers().subscribe({ next: (rows) => this.members.set(rows as unknown as MemberRow[]), error: () => {} });
    this.api.get<AssetContextSource[]>('/assets/context-sources').subscribe({
      next: (s) => this.contextSources.set(s), error: () => {},
    });
  }

  reload(): void {
    this.loading.set(true);
    const params: Record<string, string> = {};
    if (this.q.trim()) params['q'] = this.q.trim();
    if (this.fType) params['item_type'] = this.fType;
    if (this.fScope) params['scope_status'] = this.fScope;
    if (this.fCriticality) params['criticality'] = this.fCriticality;
    if (this.fPending === 'overdue') params['review_status'] = 'overdue';
    else if (this.fPending) params[this.fPending] = 'true';
    this.api.get<AssetItem[]>('/assets', params).subscribe({
      next: (rows) => { this.items.set(rows); this.loading.set(false); },
      error: (e) => { this.loading.set(false); if (e.status !== 404) this.toastErr(e); },
    });
  }

  private loadSummary(): void {
    this.api.get<AssetSummary>('/assets/summary').subscribe({
      next: (s) => this.summary.set(s), error: () => {},
    });
  }

  openCreate(): void {
    this.form.reset({ item_type: 'information_asset', scope_status: 'under_analysis', has_personal_data: false, has_sensitive_data: false });
    this.errorMsg.set(null);
    this.dialogVisible.set(true);
  }

  fromContext(index: string): void {
    const src = this.contextSources()[Number(index)];
    if (!src) return;
    this.openCreate();
    this.form.patchValue({
      name: src.label,
      item_type: (src.suggested_item_type ?? 'other'),
      description: src.description ?? '',
    });
  }

  submit(): void {
    if (this.form.invalid) return;
    this.saving.set(true);
    this.errorMsg.set(null);
    const v = this.form.getRawValue();
    this.api.post<AssetItem>('/assets', v).subscribe({
      next: () => {
        this.saving.set(false);
        this.dialogVisible.set(false);
        this.msg.add({ severity: 'success', summary: 'Item criado' });
        this.reload();
        this.loadSummary();
      },
      error: (e) => {
        this.saving.set(false);
        this.errorMsg.set(e.error?.detail ?? 'Não foi possível salvar o item.');
      },
    });
  }

  private toastErr(e: { message?: string }): void {
    this.msg.add({ severity: 'error', summary: 'Erro', detail: e.message ?? 'Falha ao carregar.' });
  }

  canManage(): boolean { return hasPermission(this.store.currentRole(), 'manage_asset'); }

  typeLabel(t: AssetType): string { return ASSET_TYPE_LABELS[t]; }
  scopeLabel(s: string): string { return SCOPE_STATUS_LABELS[s] ?? s; }
  ciaLabel(c: string): string { return CIA_LABELS[c] ?? c; }
  reviewLabel(r: string): string { return REVIEW_STATUS_LABELS[r] ?? r; }
  scopeClass(s: string): string {
    return s === 'in_scope' ? 'wtn-tag--success' : s === 'out_of_scope' ? 'wtn-tag--neutral' : 'wtn-tag--warning';
  }
  reviewClass(r: string): string {
    return r === 'overdue' ? 'wtn-tag--danger' : r === 'due_soon' ? 'wtn-tag--warning' : r === 'up_to_date' ? 'wtn-tag--success' : 'wtn-tag--neutral';
  }
}
