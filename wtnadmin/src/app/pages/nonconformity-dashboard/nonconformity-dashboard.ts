import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';

import { ApiService } from '@app/core/api.service';
import { NcDashboard } from '@app/core/models';
import { IMPROVEMENT_STATUS_LABELS, NC_SEVERITY_LABELS, NC_STATUS_LABELS } from '../nonconformities/nonconformity-labels';

/** Dashboard NC/Melhoria (PDCA) — indicadores do módulo (Feature 015, US7). */
@Component({
  selector: 'app-nonconformity-dashboard',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, ButtonModule],
  template: `
    <header class="wtn-page-header">
      <div>
        <h1 class="wtn-page-title">Dashboard · NC & Melhoria</h1>
        <p class="wtn-page-desc">Indicadores do ciclo PDCA (cláusulas 10.2 e 10.1).</p>
      </div>
      <div class="head-actions">
        <a class="link-btn" routerLink="../nonconformities">Não conformidades</a>
        <p-button icon="pi pi-refresh" label="Atualizar" severity="secondary" (onClick)="load()" [loading]="loading()" />
      </div>
    </header>

    @if (data(); as d) {
      <div class="kpis">
        <div class="kpi">
          <span class="kpi-num">{{ total(d.nc_by_status) }}</span>
          <span class="kpi-lbl">Não conformidades</span>
        </div>
        <div class="kpi" [class.alert]="(d.nc_by_status['closed'] || 0) < total(d.nc_by_status)">
          <span class="kpi-num">{{ d.nc_by_status['closed'] || 0 }}</span>
          <span class="kpi-lbl">Encerradas</span>
        </div>
        <div class="kpi" [class.alert]="d.overdue_actions > 0">
          <span class="kpi-num">{{ d.overdue_actions }}</span>
          <span class="kpi-lbl">Ações vencidas</span>
        </div>
        <div class="kpi">
          <span class="kpi-num">{{ total(d.improvements_by_status) }}</span>
          <span class="kpi-lbl">Melhorias</span>
        </div>
      </div>

      <div class="grid">
        <section class="wtn-card pad">
          <div class="wtn-card-title">NC por status</div>
          @for (e of entries(d.nc_by_status); track e[0]) {
            <div class="bar-row"><span>{{ statusLabel(e[0]) }}</span><strong>{{ e[1] }}</strong></div>
          } @empty { <p class="muted">Sem dados.</p> }
        </section>
        <section class="wtn-card pad">
          <div class="wtn-card-title">NC por severidade</div>
          @for (e of entries(d.nc_by_severity); track e[0]) {
            <div class="bar-row"><span>{{ severityLabel(e[0]) }}</span><strong>{{ e[1] }}</strong></div>
          } @empty { <p class="muted">Sem dados.</p> }
        </section>
        <section class="wtn-card pad">
          <div class="wtn-card-title">Melhorias por status</div>
          @for (e of entries(d.improvements_by_status); track e[0]) {
            <div class="bar-row"><span>{{ improvementLabel(e[0]) }}</span><strong>{{ e[1] }}</strong></div>
          } @empty { <p class="muted">Sem dados.</p> }
        </section>
      </div>
    } @else {
      <p class="muted">Carregando…</p>
    }
  `,
  styles: `
    :host { display: block; }
    .head-actions { align-items: center; display: flex; gap: 10px; }
    .link-btn { color: var(--wtn-primary); font-size: 12.5px; text-decoration: none; }
    .kpis { display: grid; gap: 12px; grid-template-columns: repeat(4, 1fr); margin-bottom: 12px; }
    @media (max-width: 880px) { .kpis { grid-template-columns: 1fr 1fr; } }
    .kpi { background: var(--wtn-card); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); display: flex; flex-direction: column; gap: 4px; padding: 14px 16px; }
    .kpi.alert { border-color: #d08a2e; }
    .kpi-num { font-size: 26px; font-weight: 700; }
    .kpi-lbl { color: var(--wtn-text-2); font-size: 12px; }
    .grid { display: grid; gap: 12px; grid-template-columns: repeat(3, 1fr); }
    @media (max-width: 880px) { .grid { grid-template-columns: 1fr; } }
    .bar-row { border-top: 1px solid var(--wtn-border); display: flex; justify-content: space-between; padding: 6px 0; font-size: 12.5px; }
    .muted { color: var(--wtn-text-2); }
  `,
})
export class NonconformityDashboardPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly messages = inject(MessageService);

  protected readonly loading = signal(false);
  protected readonly data = signal<NcDashboard | null>(null);

  ngOnInit(): void {
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    this.api.get<NcDashboard>('/nonconformities/dashboard').subscribe({
      next: (d) => {
        this.data.set(d);
        this.loading.set(false);
      },
      error: (e) => {
        this.messages.add({ severity: 'error', summary: 'Erro ao carregar', detail: this.errorDetail(e) });
        this.loading.set(false);
      },
    });
  }

  protected entries(rec: Record<string, number>): [string, number][] {
    return Object.entries(rec || {});
  }

  protected total(rec: Record<string, number>): number {
    return Object.values(rec || {}).reduce((a, b) => a + b, 0);
  }

  protected statusLabel(s: string): string { return NC_STATUS_LABELS[s as keyof typeof NC_STATUS_LABELS] ?? s; }
  protected severityLabel(s: string): string { return NC_SEVERITY_LABELS[s as keyof typeof NC_SEVERITY_LABELS] ?? s; }
  protected improvementLabel(s: string): string { return IMPROVEMENT_STATUS_LABELS[s as keyof typeof IMPROVEMENT_STATUS_LABELS] ?? s; }

  private errorDetail(error: unknown): string {
    if (typeof error === 'object' && error && 'error' in error) {
      const payload = (error as { error?: { detail?: string } }).error;
      if (payload?.detail) return payload.detail;
    }
    return 'Operação não concluída.';
  }
}
