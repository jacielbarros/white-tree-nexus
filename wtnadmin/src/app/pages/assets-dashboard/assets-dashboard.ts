import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ButtonModule } from 'primeng/button';

import { ApiService } from '@app/core/api.service';
import { AssetDashboard } from '@app/core/models';
import {
  ASSET_TYPE_LABELS,
  CIA_LABELS,
  REVIEW_STATUS_LABELS,
  SCOPE_STATUS_LABELS,
} from '@app/pages/assets/asset-labels';

interface Bar { label: string; value: number; percent: number; }

@Component({
  selector: 'app-assets-dashboard',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, ButtonModule],
  template: `
    <header class="wtn-page-header">
      <div>
        <h1 class="wtn-page-title">Ativos e Processos — Dashboard</h1>
        <p class="wtn-page-desc">Distribuições e pendências do inventário do SGSI.</p>
      </div>
      <div class="wtn-page-actions">
        <a routerLink="../assets"><p-button label="Ver inventário" icon="pi pi-list" severity="secondary" /></a>
      </div>
    </header>

    @if (loading()) {
      <div class="wtn-card pad"><div class="wtn-skeleton skeleton-line"></div></div>
    } @else if (dashboard(); as d) {
      <section class="kpi-grid">
        <div class="kpi kpi--warn"><span class="kpi-val">{{ d.with_personal_data }}</span><span class="kpi-lbl">Com dados pessoais</span></div>
        <div class="kpi kpi--warn"><span class="kpi-val">{{ d.critical_without_review }}</span><span class="kpi-lbl">Críticos sem revisão</span></div>
        <div class="kpi kpi--warn"><span class="kpi-val">{{ d.without_responsible }}</span><span class="kpi-lbl">Sem responsável</span></div>
      </section>

      <section class="grid">
        <article class="wtn-card pad">
          <div class="wtn-card-title">Distribuição por tipo</div>
          @for (b of byType(); track b.label) {
            <div class="bar-row"><span>{{ b.label }}</span><div class="track"><div class="fill" [style.width.%]="b.percent"></div></div><strong>{{ b.value }}</strong></div>
          } @empty { <p class="muted">Sem itens.</p> }
        </article>

        <article class="wtn-card pad">
          <div class="wtn-card-title">Distribuição por criticidade</div>
          @for (b of byCriticality(); track b.label) {
            <div class="bar-row"><span>{{ b.label }}</span><div class="track"><div class="fill" [style.width.%]="b.percent"></div></div><strong>{{ b.value }}</strong></div>
          } @empty { <p class="muted">Sem itens.</p> }
        </article>

        <article class="wtn-card pad">
          <div class="wtn-card-title">Situação de escopo</div>
          @for (b of byScope(); track b.label) {
            <div class="bar-row"><span>{{ b.label }}</span><div class="track"><div class="fill" [style.width.%]="b.percent"></div></div><strong>{{ b.value }}</strong></div>
          } @empty { <p class="muted">Sem itens.</p> }
        </article>

        <article class="wtn-card pad">
          <div class="wtn-card-title">Situação de revisão</div>
          @for (b of byReview(); track b.label) {
            <div class="bar-row"><span>{{ b.label }}</span><div class="track"><div class="fill" [style.width.%]="b.percent"></div></div><strong>{{ b.value }}</strong></div>
          } @empty { <p class="muted">Sem itens.</p> }
        </article>
      </section>
    } @else {
      <div class="wtn-empty"><div class="wtn-empty-title">Sem dados</div>
        <div class="wtn-empty-desc">Cadastre itens no inventário para ver as distribuições.</div></div>
    }
  `,
  styles: [`
    :host { display: block; }
    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 18px; }
    .kpi { background: var(--wtn-card); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-lg); padding: 14px 16px; display: flex; flex-direction: column; gap: 4px; }
    .kpi-val { font-size: 26px; font-weight: 700; color: var(--wtn-warning); }
    .kpi-lbl { font-size: 11px; color: var(--wtn-muted); text-transform: uppercase; letter-spacing: .04em; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }
    .wtn-card { background: var(--wtn-card); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-lg); }
    .pad { padding: 20px; }
    .wtn-card-title { color: var(--wtn-muted); font-size: 11px; font-weight: 600; letter-spacing: .05em; text-transform: uppercase; margin-bottom: 14px; }
    .bar-row { display: grid; grid-template-columns: 130px 1fr 36px; align-items: center; gap: 10px; margin-bottom: 9px; font-size: 12.5px; color: var(--wtn-text-2); }
    .bar-row strong { color: var(--wtn-text); text-align: right; }
    .track { background: var(--wtn-surface-2); border-radius: var(--wtn-r-pill); height: 8px; overflow: hidden; }
    .fill { background: var(--wtn-primary); height: 100%; border-radius: var(--wtn-r-pill); }
    .muted { color: var(--wtn-muted); font-size: 13px; }
    .skeleton-line { height: 18px; width: 100%; }
  `],
})
export class AssetsDashboardPage implements OnInit {
  private api = inject(ApiService);

  readonly dashboard = signal<AssetDashboard | null>(null);
  readonly loading = signal(true);

  readonly byType = computed(() => this.bars(this.dashboard()?.by_type, ASSET_TYPE_LABELS));
  readonly byCriticality = computed(() => this.bars(this.dashboard()?.by_criticality, CIA_LABELS));
  readonly byScope = computed(() => this.bars(this.dashboard()?.by_scope, SCOPE_STATUS_LABELS));
  readonly byReview = computed(() => this.bars(this.dashboard()?.by_review_status, REVIEW_STATUS_LABELS));

  ngOnInit(): void {
    this.api.get<AssetDashboard>('/assets/dashboard').subscribe({
      next: (d) => { this.dashboard.set(d); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  private bars(src: Record<string, number> | undefined, labels: Record<string, string>): Bar[] {
    if (!src) return [];
    const entries = Object.entries(src).filter(([, v]) => v > 0);
    const max = Math.max(1, ...entries.map(([, v]) => v));
    return entries.map(([k, v]) => ({ label: labels[k] ?? k, value: v, percent: (v / max) * 100 }));
  }
}
