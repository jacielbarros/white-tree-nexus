import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';

import { ApiService } from '@app/core/api.service';
import { GapAssessmentItem, GapDashboard, GapPriority, GapStatus } from '@app/core/models';

const STATUS_ORDER: GapStatus[] = ['meets', 'partial', 'not_meet', 'not_applicable', 'not_filled'];

const STATUS_LABELS: Record<GapStatus, string> = {
  not_filled: 'Não avaliado',
  meets: 'Atende',
  partial: 'Parcialmente',
  not_meet: 'Não atende',
  not_applicable: 'N/A',
};

const STATUS_TAG_LABELS: Record<GapStatus, string> = {
  not_filled: 'Não avaliado',
  meets: 'Atende',
  partial: 'Parcialmente atende',
  not_meet: 'Não atende',
  not_applicable: 'N/A',
};

const STATUS_COLORS: Record<GapStatus, string> = {
  meets: 'var(--wtn-success)',
  partial: 'var(--wtn-warning)',
  not_meet: 'var(--wtn-danger)',
  not_applicable: 'var(--wtn-info)',
  not_filled: 'var(--wtn-neutral)',
};

const STATUS_CLASSES: Record<GapStatus, string> = {
  meets: 'wtn-tag--success',
  partial: 'wtn-tag--warning',
  not_meet: 'wtn-tag--danger',
  not_applicable: 'wtn-tag--info',
  not_filled: 'wtn-tag--neutral',
};

const DIMENSION_LABELS: Record<string, string> = {
  organizational: 'Organizacional',
  people: 'Pessoas',
  physical: 'Físico',
  technological: 'Tecnológico',
  clause: 'Cláusulas (4-10)',
  annex_a: 'Anexo A - Controles',
};

const PRIORITY_LABELS: Record<GapPriority, string> = {
  critical: 'Crítico',
  high: 'Alto',
  medium: 'Médio',
  low: 'Baixo',
};

const PRIORITY_CLASSES: Record<GapPriority, string> = {
  critical: 'wtn-prio--crit',
  high: 'wtn-prio--high',
  medium: 'wtn-prio--med',
  low: 'wtn-prio--low',
};

const PRIORITY_RANK: Record<GapPriority, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

interface StatusView {
  key: GapStatus;
  label: string;
  tagLabel: string;
  count: number;
  percent: number;
  color: string;
  className: string;
}

interface DimensionView {
  key: string;
  label: string;
  value: number | null;
}

@Component({
  selector: 'app-gap-dashboard',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, ButtonModule],
  template: `
    <header class="wtn-page-header gap-dashboard-header">
      <div>
        <h1 class="wtn-page-title">Gap Analysis — Dashboard</h1>
        <p class="wtn-page-desc">
          Aderência aos {{ totalControls() || 93 }} controles do Anexo A
        </p>
      </div>
      <div class="wtn-page-actions">
        <a routerLink="../gap-analysis">
          <p-button label="Ver matriz" icon="pi pi-table" severity="secondary" />
        </a>
      </div>
    </header>

    @if (loading()) {
      <div class="gap-dashboard-grid">
        <div class="wtn-card dashboard-card adherence-card">
          <div class="wtn-card-title">Aderência geral</div>
          <div class="loading-orb"></div>
        </div>
        <div class="wtn-card dashboard-card distribution-card">
          <div class="wtn-card-title">Distribuição por status</div>
          <div class="wtn-skeleton skeleton-line"></div>
          <div class="wtn-skeleton skeleton-line short"></div>
          <div class="wtn-skeleton skeleton-line mid"></div>
        </div>
      </div>
    } @else if (!dashboard()) {
      <div class="wtn-empty">
        <div class="wtn-empty-icon">
          <span class="pi pi-chart-line"></span>
        </div>
        <div class="wtn-empty-title">Sem dados de aderência</div>
        <div class="wtn-empty-desc">Adote o catálogo e avalie os controles para preencher o dashboard.</div>
        <a routerLink="../gap-analysis">
          <p-button label="Abrir matriz" icon="pi pi-table" />
        </a>
      </div>
    } @else {
      <section class="gap-dashboard-grid">
        <article class="wtn-card dashboard-card adherence-card">
          <div class="wtn-card-title">Aderência geral</div>
          <div class="donut-wrap" aria-label="Aderência geral">
            <svg class="donut" viewBox="0 0 150 150" aria-hidden="true">
              <circle cx="75" cy="75" r="60" class="donut-track" />
              <circle
                cx="75"
                cy="75"
                r="60"
                class="donut-value"
                [attr.stroke-dasharray]="donutDash()"
              />
            </svg>
            <div class="donut-center">
              <strong>{{ overallPercentLabel() }}</strong>
              <span>{{ evaluatedControls() }} / {{ totalControls() }}</span>
            </div>
          </div>
        </article>

        <article class="wtn-card dashboard-card distribution-card">
          <div class="wtn-card-title">Distribuição por status</div>
          <div class="status-stack" aria-hidden="true">
            @for (entry of statusViews(); track entry.key) {
              @if (entry.count > 0) {
                <div
                  class="status-segment"
                  [style.width.%]="entry.percent"
                  [style.background]="entry.color"
                ></div>
              }
            }
          </div>
          <div class="status-legend">
            @for (entry of statusViews(); track entry.key) {
              <div class="status-legend-item">
                <span class="legend-swatch" [style.background]="entry.color"></span>
                <span>{{ entry.label }}</span>
                <strong>{{ entry.count }}</strong>
              </div>
            }
          </div>
        </article>

        <article class="wtn-card dashboard-card dimensions-card">
          <div class="wtn-card-title">Aderência por dimensão</div>
          <div class="dimension-list">
            @for (dim of dimensionViews(); track dim.key) {
              <div class="dimension-row">
                <div class="dimension-row-head">
                  <span>{{ dim.label }}</span>
                  <strong>{{ percentLabel(dim.value) }}</strong>
                </div>
                <div class="dimension-track">
                  <div class="dimension-fill" [style.width.%]="barPercent(dim.value)"></div>
                </div>
              </div>
            } @empty {
              <p class="muted-copy">Sem aderência por dimensão.</p>
            }
          </div>
        </article>

        <article class="wtn-card dashboard-card gaps-card">
          <div class="gaps-card-header">
            <span>Lacunas priorizadas</span>
            <a routerLink="../gap-analysis">Ver todas ({{ gaps().length }})</a>
          </div>
          @if (prioritizedGaps().length === 0) {
            <div class="compact-empty">Sem lacunas identificadas.</div>
          } @else {
            <table class="gaps-table">
              <tbody>
                @for (item of prioritizedGaps(); track item.id) {
                  <tr>
                    <td class="gap-ref">{{ item.ref_code }}</td>
                    <td class="gap-name">{{ item.name }}</td>
                    <td class="gap-status">
                      <span [class]="'wtn-tag ' + statusTagClass(item.status)">
                        {{ statusTagLabel(item.status) }}
                      </span>
                    </td>
                    <td class="gap-priority">
                      @if (item.priority) {
                        <span [class]="'wtn-prio ' + priorityClass(item.priority)">
                          {{ priorityLabel(item.priority) }}
                        </span>
                      } @else {
                        <span class="muted-dash">—</span>
                      }
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          }
        </article>
      </section>
    }
  `,
  styles: [`
    :host {
      display: block;
    }

    .gap-dashboard-grid {
      display: grid;
      grid-template-columns: minmax(260px, 300px) minmax(0, 1fr);
      gap: 16px;
    }

    .wtn-card {
      background: var(--wtn-card);
      border: 1px solid var(--wtn-border);
      border-radius: var(--wtn-r-lg);
      box-shadow: var(--wtn-e1);
    }

    .dashboard-card {
      padding: 22px;
      min-width: 0;
    }

    .wtn-card-title {
      color: var(--wtn-muted);
      font-size: 11px;
      font-weight: 600;
      letter-spacing: .05em;
      margin-bottom: 16px;
      text-transform: uppercase;
    }

    .adherence-card {
      align-items: center;
      display: flex;
      flex-direction: column;
      justify-content: center;
      min-height: 230px;
    }

    .adherence-card .wtn-card-title {
      align-self: stretch;
      margin-bottom: 10px;
    }

    .donut-wrap {
      height: 150px;
      position: relative;
      width: 150px;
    }

    .donut {
      height: 150px;
      transform: rotate(-90deg);
      width: 150px;
    }

    .donut circle {
      fill: none;
      stroke-width: 14;
    }

    .donut-track {
      stroke: var(--wtn-surface-2);
    }

    .donut-value {
      stroke: var(--wtn-primary);
      stroke-linecap: round;
    }

    .donut-center {
      align-items: center;
      color: var(--wtn-text-2);
      display: flex;
      flex-direction: column;
      font-size: 11px;
      inset: 0;
      justify-content: center;
      position: absolute;
    }

    .donut-center strong {
      color: var(--wtn-text);
      font-size: 34px;
      font-weight: 700;
      letter-spacing: 0;
      line-height: 1;
    }

    .distribution-card {
      min-height: 230px;
    }

    .status-stack {
      border-radius: 6px;
      display: flex;
      height: 18px;
      margin-bottom: 18px;
      overflow: hidden;
      background: var(--wtn-surface-2);
    }

    .status-segment {
      min-width: 2px;
    }

    .status-legend {
      display: grid;
      gap: 10px 18px;
      grid-template-columns: repeat(3, minmax(130px, 1fr));
    }

    .status-legend-item {
      align-items: center;
      color: var(--wtn-text-2);
      display: flex;
      font-size: 12px;
      gap: 8px;
      min-width: 0;
    }

    .status-legend-item span:nth-child(2) {
      flex: 1;
      min-width: 0;
    }

    .status-legend-item strong {
      color: var(--wtn-text);
      font-size: 13px;
      font-weight: 700;
    }

    .legend-swatch {
      border-radius: 3px;
      flex: none;
      height: 10px;
      width: 10px;
    }

    .dimensions-card {
      min-height: 300px;
    }

    .dimension-list {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .dimension-row-head {
      display: flex;
      font-size: 12.5px;
      justify-content: space-between;
      margin-bottom: 6px;
    }

    .dimension-row-head span,
    .dimension-row-head strong {
      color: var(--wtn-text);
    }

    .dimension-row-head strong {
      font-weight: 700;
    }

    .dimension-track {
      background: var(--wtn-surface-2);
      border-radius: var(--wtn-r-pill);
      height: 8px;
      overflow: hidden;
    }

    .dimension-fill {
      background: var(--wtn-primary);
      border-radius: var(--wtn-r-pill);
      height: 100%;
    }

    .gaps-card {
      overflow: hidden;
      padding: 0;
    }

    .gaps-card-header {
      align-items: center;
      display: flex;
      justify-content: space-between;
      padding: 16px 20px 12px;
    }

    .gaps-card-header span {
      color: var(--wtn-text);
      font-size: 13px;
      font-weight: 600;
    }

    .gaps-card-header a {
      color: var(--wtn-primary);
      font-size: 12px;
      font-weight: 600;
      text-decoration: none;
    }

    .gaps-table {
      border-collapse: collapse;
      font-size: 12.5px;
      width: 100%;
    }

    .gaps-table td {
      border-top: 1px solid var(--wtn-surface-2);
      padding: 10px 8px;
      vertical-align: middle;
    }

    .gaps-table tr:hover {
      background: var(--wtn-surface-2);
    }

    .gap-ref {
      color: var(--wtn-text-2);
      font-family: var(--wtn-font-mono);
      font-size: 11.5px;
      padding-left: 20px !important;
      width: 76px;
    }

    .gap-name {
      color: var(--wtn-text);
      min-width: 220px;
    }

    .gap-status {
      width: 170px;
    }

    .gap-priority {
      padding-right: 20px !important;
      width: 96px;
    }

    .compact-empty,
    .muted-copy {
      color: var(--wtn-text-2);
      font-size: 13px;
      margin: 0;
    }

    .compact-empty {
      padding: 18px 20px 22px;
    }

    .muted-dash {
      color: var(--wtn-muted);
      font-weight: 700;
    }

    .loading-orb {
      border: 12px solid var(--wtn-surface-2);
      border-radius: 50%;
      border-top-color: var(--wtn-primary);
      height: 116px;
      width: 116px;
      animation: wtn-spin .9s linear infinite;
    }

    .skeleton-line {
      height: 18px;
      margin-bottom: 12px;
      width: 100%;
    }

    .skeleton-line.short {
      width: 72%;
    }

    .skeleton-line.mid {
      width: 86%;
    }

    @media (max-width: 960px) {
      .gap-dashboard-grid {
        grid-template-columns: 1fr;
      }

      .status-legend {
        grid-template-columns: repeat(2, minmax(120px, 1fr));
      }

      .gaps-table,
      .gaps-table tbody,
      .gaps-table tr,
      .gaps-table td {
        display: block;
      }

      .gaps-table tr {
        border-top: 1px solid var(--wtn-surface-2);
        padding: 12px 20px;
      }

      .gaps-table td {
        border: 0;
        padding: 3px 0 !important;
        width: auto;
      }
    }
  `],
})
export class GapDashboardPage implements OnInit {
  private api = inject(ApiService);
  private msg = inject(MessageService);

  readonly dashboard = signal<GapDashboard | null>(null);
  protected readonly gaps = signal<GapAssessmentItem[]>([]);
  readonly loading = signal(true);

  protected readonly totalControls = computed(() => {
    const distribution = this.dashboard()?.status_distribution ?? {};
    return Object.values(distribution).reduce((sum, count) => sum + count, 0);
  });

  protected readonly evaluatedControls = computed(() => {
    const total = this.totalControls();
    const notFilled = this.dashboard()?.status_distribution['not_filled'] ?? 0;
    return Math.max(total - notFilled, 0);
  });

  protected readonly adherenceRatio = computed(() => {
    const value = this.dashboard()?.overall_adherence;
    return value === null || value === undefined ? 0 : value;
  });

  protected readonly statusViews = computed<StatusView[]>(() => {
    const distribution = this.dashboard()?.status_distribution ?? {};
    const total = this.totalControls();
    return STATUS_ORDER.map((key) => {
      const count = distribution[key] ?? 0;
      return {
        key,
        label: STATUS_LABELS[key],
        tagLabel: STATUS_TAG_LABELS[key],
        count,
        percent: total ? (count / total) * 100 : 0,
        color: STATUS_COLORS[key],
        className: STATUS_CLASSES[key],
      };
    });
  });

  protected readonly dimensionViews = computed<DimensionView[]>(() => {
    const d = this.dashboard();
    if (!d) return [];
    const source = Object.keys(d.by_theme ?? {}).length ? d.by_theme : d.by_dimension;
    return Object.entries(source).map(([key, value]) => ({
      key,
      label: DIMENSION_LABELS[key] ?? key,
      value,
    }));
  });

  protected readonly prioritizedGaps = computed(() =>
    [...this.gaps()]
      .sort((a, b) => this.priorityRank(a.priority) - this.priorityRank(b.priority))
      .slice(0, 5),
  );

  ngOnInit() {
    this.api.get<GapDashboard>('/gap/assessment/dashboard').subscribe({
      next: (d) => {
        this.dashboard.set(d);
        this.loadGaps();
      },
      error: (e) => {
        if (e.status !== 404) {
          this.msg.add({ severity: 'error', summary: 'Erro', detail: e.message });
        }
        this.loading.set(false);
      },
    });
  }

  private loadGaps() {
    this.api.get<GapAssessmentItem[]>('/gap/assessment/gaps').subscribe({
      next: (g) => {
        this.gaps.set(g);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  protected donutDash(): string {
    const circumference = 377;
    return `${(this.adherenceRatio() * circumference).toFixed(1)} ${circumference}`;
  }

  protected overallPercentLabel(): string {
    const value = this.dashboard()?.overall_adherence;
    return value === null || value === undefined ? '—' : `${Math.round(value * 100)}%`;
  }

  protected percentLabel(value: number | null): string {
    return value === null ? '—' : `${Math.round(value * 100)}%`;
  }

  protected barPercent(value: number | null): number {
    return value === null ? 0 : Math.max(0, Math.min(value * 100, 100));
  }

  protected statusTagLabel(status: GapStatus): string {
    return STATUS_TAG_LABELS[status];
  }

  protected statusTagClass(status: GapStatus): string {
    return STATUS_CLASSES[status];
  }

  protected priorityLabel(priority: GapPriority): string {
    return PRIORITY_LABELS[priority];
  }

  protected priorityClass(priority: GapPriority): string {
    return PRIORITY_CLASSES[priority];
  }

  private priorityRank(priority: GapPriority | null): number {
    return priority ? PRIORITY_RANK[priority] : 9;
  }
}
