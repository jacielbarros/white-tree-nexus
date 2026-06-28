import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ButtonModule } from 'primeng/button';

import { ApiService } from '@app/core/api.service';
import { RiskDashboard } from '@app/core/models';
import { LEVEL_LABELS, levelColor } from '@app/pages/risks/risk-labels';

interface Bar { label: string; value: number; percent: number; color: string; }

@Component({
  selector: 'app-risk-dashboard',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, ButtonModule],
  template: `
    <header class="wtn-page-header">
      <div>
        <h1 class="wtn-page-title">Riscos — Dashboard</h1>
        <p class="wtn-page-desc">Heat map, distribuições e comparação inerente × residual.</p>
      </div>
      <div class="wtn-page-actions"><a routerLink="../risks"><p-button label="Ver registro" icon="pi pi-list" severity="secondary" /></a></div>
    </header>

    @if (d(); as dash) {
      <section class="kpi-grid">
        <div class="kpi"><span class="kpi-val">{{ dash.inherent_vs_residual.inherent_above }}</span><span class="kpi-lbl">Inerente acima do critério</span></div>
        <div class="kpi"><span class="kpi-val">{{ dash.inherent_vs_residual.residual_above }}</span><span class="kpi-lbl">Residual acima do critério</span></div>
        <div class="kpi kpi--warn"><span class="kpi-val">{{ dash.without_treatment }}</span><span class="kpi-lbl">Sem tratamento</span></div>
        <div class="kpi"><span class="kpi-val">{{ dash.accepted }}</span><span class="kpi-lbl">Aceitos</span></div>
        <div class="kpi kpi--warn"><span class="kpi-val">{{ dash.residual_pending }}</span><span class="kpi-lbl">Residual pendente</span></div>
      </section>

      <section class="grid">
        <article class="wtn-card pad">
          <div class="wtn-card-title">Heat map · Probabilidade × Impacto</div>
          <div class="heatmap">
            <div class="hm-corner"></div>
            @for (i of axis; track i) { <div class="hm-axis">I{{ i }}</div> }
            @for (p of axisRev; track p) {
              <div class="hm-axis">P{{ p }}</div>
              @for (i of axis; track i) {
                <div class="hm-cell" [style.background]="cellColor(dash, p, i)">{{ cellCount(dash, p, i) || '' }}</div>
              }
            }
          </div>
        </article>

        <article class="wtn-card pad">
          <div class="wtn-card-title">Distribuição por nível</div>
          @for (b of byLevel(); track b.label) {
            <div class="bar-row"><span>{{ b.label }}</span><div class="track"><div class="fill" [style.width.%]="b.percent" [style.background]="b.color"></div></div><strong>{{ b.value }}</strong></div>
          } @empty { <p class="muted">Sem riscos avaliados.</p> }
        </article>
      </section>
    } @else {
      <div class="wtn-card pad"><div class="wtn-skeleton skeleton-line"></div></div>
    }
  `,
  styles: [`
    :host { display: block; }
    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 18px; }
    .kpi { background: var(--wtn-card); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-lg); padding: 14px 16px; display: flex; flex-direction: column; gap: 4px; }
    .kpi-val { font-size: 26px; font-weight: 700; color: var(--wtn-text); }
    .kpi--warn .kpi-val { color: var(--wtn-warning); }
    .kpi-lbl { font-size: 11px; color: var(--wtn-muted); text-transform: uppercase; letter-spacing: .04em; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }
    .wtn-card { background: var(--wtn-card); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-lg); }
    .pad { padding: 18px 20px; }
    .wtn-card-title { color: var(--wtn-muted); font-size: 11px; font-weight: 600; letter-spacing: .05em; text-transform: uppercase; margin-bottom: 14px; }
    .heatmap { display: grid; grid-template-columns: 28px repeat(5, 1fr); gap: 4px; max-width: 420px; }
    .hm-axis { font-size: 11px; color: var(--wtn-muted); display: flex; align-items: center; justify-content: center; }
    .hm-cell { aspect-ratio: 1.8; border-radius: 6px; display: flex; align-items: center; justify-content: center; color: #fff; font-weight: 700; font-size: 13px; }
    .bar-row { display: grid; grid-template-columns: 90px 1fr 30px; align-items: center; gap: 10px; margin-bottom: 9px; font-size: 12.5px; color: var(--wtn-text-2); }
    .bar-row strong { color: var(--wtn-text); text-align: right; }
    .track { background: var(--wtn-surface-2); border-radius: var(--wtn-r-pill); height: 8px; overflow: hidden; }
    .fill { height: 100%; border-radius: var(--wtn-r-pill); }
    .muted { color: var(--wtn-muted); font-size: 13px; } .skeleton-line { height: 18px; }
  `],
})
export class RiskDashboardPage implements OnInit {
  private api = inject(ApiService);

  readonly axis = [1, 2, 3, 4, 5];
  readonly axisRev = [5, 4, 3, 2, 1];
  readonly d = signal<RiskDashboard | null>(null);

  readonly byLevel = computed<Bar[]>(() => {
    const src = this.d()?.by_level;
    if (!src) return [];
    const order = ['low', 'medium', 'high', 'critical'];
    const max = Math.max(1, ...Object.values(src));
    return order.filter((k) => src[k]).map((k) => ({
      label: LEVEL_LABELS[k] ?? k, value: src[k], percent: (src[k] / max) * 100, color: levelColor(k),
    }));
  });

  ngOnInit(): void {
    this.api.get<RiskDashboard>('/risk/dashboard').subscribe((dash) => this.d.set(dash));
  }

  cellCount(dash: RiskDashboard, p: number, i: number): number {
    return dash.heatmap.find((c) => c.probability === p && c.impact === i)?.count ?? 0;
  }
  cellColor(dash: RiskDashboard, p: number, i: number): string {
    return levelColor(dash.heatmap.find((c) => c.probability === p && c.impact === i)?.level_key);
  }
}
