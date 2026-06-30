import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { hasPermission } from '@app/core/permissions';
import { Improvement, ImprovementOrigin, ImprovementStatus, PdcaEntry, SgsiArtifactType } from '@app/core/models';
import { IMPROVEMENT_ORIGIN_LABELS, IMPROVEMENT_STATUS_LABELS } from '../nonconformities/nonconformity-labels';

/** Melhorias (10.1) + visão de ciclo PDCA read-only fechando o loop (Feature 015, US6). */
@Component({
  selector: 'app-improvements',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, ButtonModule],
  template: `
    <header class="wtn-page-header">
      <div>
        <h1 class="wtn-page-title">Melhoria Contínua</h1>
        <p class="wtn-page-desc">Oportunidades de melhoria e ciclo PDCA do SGSI (cláusula 10.1).</p>
      </div>
      <p-button icon="pi pi-refresh" label="Atualizar" severity="secondary" (onClick)="load()" [loading]="loading()" />
    </header>

    @if (canManage()) {
      <section class="wtn-card pad">
        <div class="wtn-card-title">Nova melhoria</div>
        <form class="stack-form" (submit)="create($event)">
          <div class="row">
            <input type="text" [(ngModel)]="newTitle" name="t" placeholder="Título" />
            <select [(ngModel)]="newOrigin" name="o">
              @for (o of origins; track o) { <option [value]="o">{{ originLabel(o) }}</option> }
            </select>
          </div>
          <textarea [(ngModel)]="newDescription" name="d" rows="2" placeholder="Descrição"></textarea>
          <button type="submit" class="btn-primary" [disabled]="!canCreate()">Registrar</button>
        </form>
      </section>
    }

    <section class="wtn-card pad">
      <div class="filters">
        <select [(ngModel)]="filterOrigin" name="fo" (change)="load()">
          <option value="">Todas as origens</option>
          @for (o of origins; track o) { <option [value]="o">{{ originLabel(o) }}</option> }
        </select>
        <select [(ngModel)]="filterStatus" name="fs" (change)="load()">
          <option value="">Todos os status</option>
          @for (s of statuses; track s) { <option [value]="s">{{ statusLabel(s) }}</option> }
        </select>
      </div>
      @if (loading()) {
        <p class="muted">Carregando…</p>
      } @else if (!items().length) {
        <div class="wtn-empty"><div class="wtn-empty-title">Nenhuma melhoria</div></div>
      } @else {
        <div class="imp-list">
          @for (i of items(); track i.id) {
            <div class="imp-row">
              <span class="code">{{ i.code }}</span>
              <div class="imp-meta">
                <strong>{{ i.title }}</strong>
                <span>{{ originLabel(i.origin) }}</span>
              </div>
              @if (canManage()) {
                <select [ngModel]="i.status" (ngModelChange)="updateStatus(i, $event)" name="st-{{ i.id }}">
                  @for (s of statuses; track s) { <option [value]="s">{{ statusLabel(s) }}</option> }
                </select>
              } @else {
                <span class="status">{{ statusLabel(i.status) }}</span>
              }
            </div>
          }
        </div>
      }
    </section>

    <section class="wtn-card pad">
      <div class="wtn-card-title">Ciclo PDCA (visão por artefato)</div>
      <form class="filters" (submit)="loadPdca($event)">
        <select [(ngModel)]="pdcaType" name="pt">
          <option value="gap_item">Item de Gap</option>
          <option value="soa_item">Controle SoA</option>
          <option value="risk">Risco</option>
          <option value="asset">Ativo</option>
          <option value="nonconformity">Não conformidade</option>
        </select>
        <input type="text" [(ngModel)]="pdcaId" name="pi" placeholder="ID do artefato" />
        <button type="submit" class="btn-sec" [disabled]="!pdcaId.trim()">Ver ciclo</button>
      </form>
      @if (pdca().length) {
        <div class="pdca">
          @for (phase of phases; track phase.key) {
            <div class="pdca-col">
              <div class="pdca-head pdca-head--{{ phase.key }}">{{ phase.label }}</div>
              @for (e of entriesFor(phase.key); track e.ref_id) {
                <div class="pdca-card">
                  <span class="kind">{{ e.kind }}</span>
                  <strong>{{ e.label }}</strong>
                  <small>{{ e.detail }}</small>
                  <time>{{ formatDate(e.occurred_at) }}</time>
                </div>
              } @empty { <p class="muted small">—</p> }
            </div>
          }
        </div>
      } @else if (pdcaLoaded()) {
        <p class="muted">Nenhum evento de ciclo para este artefato.</p>
      }
    </section>
  `,
  styles: `
    :host { display: block; }
    .stack-form { display: grid; gap: 8px; }
    .row { display: flex; gap: 8px; }
    .row input { flex: 1; }
    input, select, textarea { background: var(--wtn-surface); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); color: var(--wtn-text); padding: 7px 10px; font: inherit; }
    .btn-primary { background: var(--wtn-primary); border: none; border-radius: var(--wtn-r-md); color: #fff; cursor: pointer; padding: 7px 16px; justify-self: start; }
    .btn-primary:disabled { opacity: .5; cursor: not-allowed; }
    .btn-sec { background: var(--wtn-surface); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); color: var(--wtn-text); cursor: pointer; padding: 6px 14px; }
    .muted { color: var(--wtn-text-2); }
    .small { font-size: 11.5px; }
    .filters { align-items: center; display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 10px; }
    .imp-list { display: grid; gap: 6px; }
    .imp-row { align-items: center; border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); display: flex; gap: 10px; padding: 9px 12px; }
    .imp-row .code { color: var(--wtn-muted); font-weight: 700; font-size: 12px; }
    .imp-meta { display: flex; flex: 1; flex-direction: column; }
    .imp-meta span { color: var(--wtn-text-2); font-size: 11.5px; }
    .status { border-radius: 999px; font-size: 10.5px; padding: 2px 9px; border: 1px solid var(--wtn-border); color: var(--wtn-text-2); }
    .pdca { display: grid; gap: 10px; grid-template-columns: repeat(3, 1fr); }
    @media (max-width: 880px) { .pdca { grid-template-columns: 1fr; } }
    .pdca-col { display: flex; flex-direction: column; gap: 6px; }
    .pdca-head { border-radius: var(--wtn-r-md); color: #fff; font-size: 12px; font-weight: 700; padding: 5px 10px; text-align: center; }
    .pdca-head--plan { background: #6c63ff; }
    .pdca-head--check { background: #d08a2e; }
    .pdca-head--act { background: #2e9e5b; }
    .pdca-card { border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); display: flex; flex-direction: column; gap: 2px; padding: 7px 9px; }
    .pdca-card .kind { color: var(--wtn-muted); font-size: 10px; text-transform: uppercase; }
    .pdca-card strong { font-size: 12.5px; }
    .pdca-card small { color: var(--wtn-text-2); font-size: 11px; }
    .pdca-card time { color: var(--wtn-muted); font-size: 10.5px; }
  `,
})
export class ImprovementsPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly store = inject(AuthStore);
  private readonly messages = inject(MessageService);

  protected readonly loading = signal(false);
  protected readonly items = signal<Improvement[]>([]);
  protected readonly pdca = signal<PdcaEntry[]>([]);
  protected readonly pdcaLoaded = signal(false);

  protected readonly origins: ImprovementOrigin[] = ['suggestion', 'audit', 'nonconformity', 'management_review'];
  protected readonly statuses: ImprovementStatus[] = ['proposed', 'in_progress', 'implemented', 'rejected'];
  protected readonly phases: { key: 'plan' | 'check' | 'act'; label: string }[] = [
    { key: 'check', label: 'Check · verificar' },
    { key: 'act', label: 'Act · agir' },
    { key: 'plan', label: 'Plan · planejar' },
  ];

  protected newTitle = '';
  protected newDescription = '';
  protected newOrigin: ImprovementOrigin = 'suggestion';
  protected filterOrigin = '';
  protected filterStatus = '';
  protected pdcaType: SgsiArtifactType = 'gap_item';
  protected pdcaId = '';

  protected readonly canManage = computed(() => hasPermission(this.store.currentRole(), 'manage_nonconformity'));

  ngOnInit(): void {
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    const params: Record<string, string> = {};
    if (this.filterOrigin) params['origin'] = this.filterOrigin;
    if (this.filterStatus) params['status'] = this.filterStatus;
    const qs = new URLSearchParams(params).toString();
    this.api.get<Improvement[]>(`/improvements${qs ? '?' + qs : ''}`).subscribe({
      next: (rows) => {
        this.items.set(rows);
        this.loading.set(false);
      },
      error: (e) => {
        this.messages.add({ severity: 'error', summary: 'Erro ao carregar', detail: this.errorDetail(e) });
        this.loading.set(false);
      },
    });
  }

  protected canCreate(): boolean {
    return !!(this.newTitle.trim() && this.newDescription.trim());
  }

  protected create(event: Event): void {
    event.preventDefault();
    if (!this.canCreate()) return;
    this.api.post<Improvement>('/improvements', {
      title: this.newTitle.trim(),
      description: this.newDescription.trim(),
      origin: this.newOrigin,
    }).subscribe({
      next: () => {
        this.messages.add({ severity: 'success', summary: 'Melhoria registrada' });
        this.newTitle = '';
        this.newDescription = '';
        this.load();
      },
      error: (e) => this.messages.add({ severity: 'error', summary: 'Erro', detail: this.errorDetail(e) }),
    });
  }

  protected updateStatus(i: Improvement, status: ImprovementStatus): void {
    this.api.put(`/improvements/${i.id}`, {
      title: i.title,
      description: i.description,
      origin: i.origin,
      source_ref: i.source_ref,
      status,
      target_type: i.target_type,
      target_id: i.target_id,
    }).subscribe({
      next: () => this.load(),
      error: (e) => this.messages.add({ severity: 'error', summary: 'Erro', detail: this.errorDetail(e) }),
    });
  }

  protected loadPdca(event: Event): void {
    event.preventDefault();
    if (!this.pdcaId.trim()) return;
    const qs = new URLSearchParams({ target_type: this.pdcaType, target_id: this.pdcaId.trim() }).toString();
    this.api.get<PdcaEntry[]>(`/improvements/pdca?${qs}`).subscribe({
      next: (rows) => {
        this.pdca.set(rows);
        this.pdcaLoaded.set(true);
      },
      error: (e) => this.messages.add({ severity: 'error', summary: 'Erro', detail: this.errorDetail(e) }),
    });
  }

  protected entriesFor(phase: 'plan' | 'check' | 'act'): PdcaEntry[] {
    return this.pdca().filter((e) => e.phase === phase);
  }

  protected originLabel(o: ImprovementOrigin): string { return IMPROVEMENT_ORIGIN_LABELS[o]; }
  protected statusLabel(s: ImprovementStatus): string { return IMPROVEMENT_STATUS_LABELS[s]; }

  protected formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString('pt-BR');
  }

  private errorDetail(error: unknown): string {
    if (typeof error === 'object' && error && 'error' in error) {
      const payload = (error as { error?: { detail?: string } }).error;
      if (payload?.detail) return payload.detail;
    }
    return 'Operação não concluída.';
  }
}
