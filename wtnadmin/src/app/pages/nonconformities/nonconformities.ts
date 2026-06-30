import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { hasPermission } from '@app/core/permissions';
import { NCOrigin, NCSeverity, NCStatus, NCSummary } from '@app/core/models';
import { NC_ORIGIN_LABELS, NC_SEVERITY_LABELS, NC_STATUS_LABELS } from './nonconformity-labels';

/** Não Conformidades & Ações Corretivas — lista + filtros + criação (Feature 015, US1/US3). */
@Component({
  selector: 'app-nonconformities',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, RouterLink, ButtonModule],
  template: `
    <header class="wtn-page-header">
      <div>
        <h1 class="wtn-page-title">Não Conformidades</h1>
        <p class="wtn-page-desc">Registro, tratamento e verificação de eficácia (cláusula 10.2).</p>
      </div>
      <div class="head-actions">
        <a class="link-btn" routerLink="../nonconformity-dashboard">Dashboard</a>
        <p-button icon="pi pi-refresh" label="Atualizar" severity="secondary" (onClick)="load()" [loading]="loading()" />
      </div>
    </header>

    @if (canManage()) {
      <section class="wtn-card pad">
        <div class="wtn-card-title">Nova não conformidade</div>
        <form class="stack-form" (submit)="create($event)">
          <div class="row">
            <select [(ngModel)]="newOrigin" name="origin">
              @for (o of origins; track o) { <option [value]="o">{{ originLabel(o) }}</option> }
            </select>
            <select [(ngModel)]="newSeverity" name="severity">
              @for (s of severities; track s) { <option [value]="s">{{ severityLabel(s) }}</option> }
            </select>
          </div>
          <input type="text" [(ngModel)]="newTitle" name="t" placeholder="Título" />
          <textarea [(ngModel)]="newDescription" name="d" rows="2" placeholder="Descrição do desvio"></textarea>
          <button type="submit" class="btn-primary" [disabled]="!canCreate()">Registrar</button>
        </form>
      </section>
    }

    <section class="wtn-card pad">
      <div class="filters">
        <select [(ngModel)]="filterStatus" name="fs" (change)="load()">
          <option value="">Todos os status</option>
          @for (s of statuses; track s) { <option [value]="s">{{ statusLabel(s) }}</option> }
        </select>
        <select [(ngModel)]="filterSeverity" name="fsev" (change)="load()">
          <option value="">Todas as severidades</option>
          @for (s of severities; track s) { <option [value]="s">{{ severityLabel(s) }}</option> }
        </select>
        <label class="chk"><input type="checkbox" [(ngModel)]="filterOverdue" name="fo" (change)="load()" /> Só com ações vencidas</label>
      </div>

      @if (loading()) {
        <p class="muted">Carregando…</p>
      } @else if (!items().length) {
        <div class="wtn-empty"><div class="wtn-empty-title">Nenhuma não conformidade</div></div>
      } @else {
        <div class="nc-list">
          @for (nc of items(); track nc.id) {
            <a class="nc-row" [routerLink]="['../nonconformity-detail', nc.id]">
              <span class="code">{{ nc.code }}</span>
              <span class="title">{{ nc.title }}</span>
              <span class="sev sev--{{ nc.severity }}">{{ severityLabel(nc.severity) }}</span>
              <span class="status status--{{ nc.status }}">{{ statusLabel(nc.status) }}</span>
              @if (nc.source_finding_id) { <span class="badge" title="Promovida de constatação">9.2</span> }
            </a>
          }
        </div>
      }
    </section>
  `,
  styles: `
    :host { display: block; }
    .head-actions { align-items: center; display: flex; gap: 10px; }
    .link-btn { color: var(--wtn-primary); font-size: 12.5px; text-decoration: none; }
    .stack-form { display: grid; gap: 8px; }
    .row { display: flex; gap: 8px; }
    .stack-form input, .stack-form select, .stack-form textarea, .filters select {
      background: var(--wtn-surface); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md);
      color: var(--wtn-text); padding: 7px 10px; font: inherit;
    }
    .btn-primary { background: var(--wtn-primary); border: none; border-radius: var(--wtn-r-md); color: #fff; cursor: pointer; padding: 7px 16px; justify-self: start; }
    .btn-primary:disabled { opacity: .5; cursor: not-allowed; }
    .muted { color: var(--wtn-text-2); }
    .filters { align-items: center; display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 10px; }
    .chk { align-items: center; color: var(--wtn-text-2); display: flex; font-size: 12.5px; gap: 5px; }
    .nc-list { display: grid; gap: 6px; }
    .nc-row { align-items: center; border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); color: var(--wtn-text); display: flex; gap: 10px; padding: 9px 12px; text-decoration: none; }
    .nc-row:hover { border-color: var(--wtn-primary); }
    .nc-row .code { color: var(--wtn-muted); font-weight: 700; font-size: 12px; }
    .nc-row .title { flex: 1; font-size: 13px; }
    .sev, .status { border-radius: 999px; font-size: 10.5px; padding: 2px 9px; border: 1px solid var(--wtn-border); color: var(--wtn-text-2); }
    .sev--maior { border-color: #d14343; color: #d14343; }
    .sev--menor { border-color: #d08a2e; color: #d08a2e; }
    .status--in_progress, .status--in_verification { border-color: var(--wtn-primary); color: var(--wtn-primary); }
    .status--closed { border-color: #2e9e5b; color: #2e9e5b; }
    .status--cancelled { color: var(--wtn-muted); }
    .badge { background: var(--wtn-primary); border-radius: 999px; color: #fff; font-size: 10px; padding: 2px 8px; }
  `,
})
export class NonconformitiesPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly store = inject(AuthStore);
  private readonly messages = inject(MessageService);

  protected readonly loading = signal(false);
  protected readonly items = signal<NCSummary[]>([]);

  protected readonly origins: NCOrigin[] = ['incident', 'audit_finding', 'external_audit', 'management_review', 'other'];
  protected readonly severities: NCSeverity[] = ['maior', 'menor', 'observacao'];
  protected readonly statuses: NCStatus[] = ['open', 'in_progress', 'in_verification', 'closed', 'cancelled'];

  protected newOrigin: NCOrigin = 'incident';
  protected newSeverity: NCSeverity = 'menor';
  protected newTitle = '';
  protected newDescription = '';

  protected filterStatus = '';
  protected filterSeverity = '';
  protected filterOverdue = false;

  protected readonly canManage = computed(() => hasPermission(this.store.currentRole(), 'manage_nonconformity'));

  ngOnInit(): void {
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    const params: Record<string, string> = {};
    if (this.filterStatus) params['status'] = this.filterStatus;
    if (this.filterSeverity) params['severity'] = this.filterSeverity;
    if (this.filterOverdue) params['overdue'] = 'true';
    const qs = new URLSearchParams(params).toString();
    this.api.get<NCSummary[]>(`/nonconformities${qs ? '?' + qs : ''}`).subscribe({
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
    this.api.post<NCSummary>('/nonconformities', {
      origin: this.newOrigin,
      severity: this.newSeverity,
      title: this.newTitle.trim(),
      description: this.newDescription.trim(),
    }).subscribe({
      next: () => {
        this.messages.add({ severity: 'success', summary: 'NC registrada' });
        this.newTitle = '';
        this.newDescription = '';
        this.load();
      },
      error: (e) => this.messages.add({ severity: 'error', summary: 'Erro', detail: this.errorDetail(e) }),
    });
  }

  protected originLabel(o: NCOrigin): string { return NC_ORIGIN_LABELS[o]; }
  protected severityLabel(s: NCSeverity): string { return NC_SEVERITY_LABELS[s]; }
  protected statusLabel(s: NCStatus): string { return NC_STATUS_LABELS[s]; }

  private errorDetail(error: unknown): string {
    if (typeof error === 'object' && error && 'error' in error) {
      const payload = (error as { error?: { detail?: string } }).error;
      if (payload?.detail) return payload.detail;
    }
    return 'Operação não concluída.';
  }
}
