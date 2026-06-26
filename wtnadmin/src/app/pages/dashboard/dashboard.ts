import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { of } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';

interface NextAction {
  label: string;
  route: string;
  fragment: string | null;
}

interface ModuleCard {
  id: string;
  title: string;
  status: string;
  progress_pct: number | null;
  responsible: string | null;
  deadline: string | null;
  overdue: boolean;
  next_action: NextAction;
  not_started: boolean;
  placeholder: boolean;
}

interface DashboardKpis {
  overall_adherence: number | null;
  controls_evaluated: number;
  controls_total: number;
  conformance_clause: number | null;
  conformance_annex: number | null;
  critical_gaps: number;
  modules_approved: number;
  modules_total: number;
}

interface AdherencePoint {
  date: string;
  adherence: number;
  version: number;
}

interface DashboardResponse {
  organization_id: string;
  organization_name: string;
  kpis: DashboardKpis;
  cards: ModuleCard[];
  adherence_trend: AdherencePoint[] | null;
  generated_at: string;
}

const STATUS_LABEL: Record<string, string> = {
  not_started: 'Não iniciado',
  draft: 'Rascunho',
  in_review: 'Em revisão',
  in_force: 'Aprovado',
  needs_review: 'Revisão vencida',
  error: 'Indisponível',
};

const STATUS_CLASS: Record<string, string> = {
  not_started: 'wtn-tag--neutral',
  draft: 'wtn-tag--neutral',
  in_review: 'wtn-tag--info',
  in_force: 'wtn-tag--success',
  needs_review: 'wtn-tag--warning',
  error: 'wtn-tag--danger',
};

@Component({
  selector: 'app-dashboard',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header class="wtn-page-header">
      <div>
        <h1 class="wtn-page-title">Dashboard de Conformidade</h1>
        <p class="wtn-page-desc">
          {{ orgName() }} · jornada de implementação do SGSI conforme ISO/IEC&nbsp;27001:2022.
        </p>
      </div>
    </header>

    @if (loading()) {
      <div class="wtn-loading-row">
        <div class="wtn-spinner"></div>
        <span class="wtn-text-2">Carregando dados…</span>
      </div>
    } @else if (denied()) {
      <div class="wtn-empty">Você não tem permissão para ver o dashboard desta organização.</div>
    } @else {
      <!-- KPI row -->
      <div class="wtn-kpi-row">
        <div class="wtn-kpi-card wtn-kpi-card--main">
          <div class="wtn-kpi-label">Conformidade geral</div>
          <div class="wtn-kpi-main-row">
            @if (kpis().overall_adherence !== null) {
              <div class="wtn-kpi-value">{{ (kpis().overall_adherence! * 100).toFixed(0) }}%</div>
            } @else {
              <div class="wtn-kpi-value wtn-muted">—</div>
            }
            @if (sparkline(); as pts) {
              <svg class="wtn-sparkline" viewBox="0 0 120 36" preserveAspectRatio="none" aria-hidden="true">
                <polyline [attr.points]="pts" fill="none" stroke="var(--wtn-primary)" stroke-width="2"
                          stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            }
          </div>
          <div class="wtn-kpi-sub">
            Cláusulas 4–10 {{ pct(kpis().conformance_clause) }} · Anexo A {{ pct(kpis().conformance_annex) }}
          </div>
        </div>
        <div class="wtn-kpi-card">
          <div class="wtn-kpi-label">Itens avaliados</div>
          <div class="wtn-kpi-value">
            {{ kpis().controls_evaluated }}<span class="wtn-kpi-total"> / {{ kpis().controls_total }}</span>
          </div>
          <div class="wtn-kpi-sub">cláusulas + Anexo A</div>
        </div>
        <div class="wtn-kpi-card">
          <div class="wtn-kpi-label">Lacunas críticas</div>
          <div class="wtn-kpi-value" [class.wtn-danger-text]="kpis().critical_gaps > 0">
            {{ kpis().critical_gaps }}
          </div>
        </div>
        <div class="wtn-kpi-card">
          <div class="wtn-kpi-label">Módulos aprovados</div>
          <div class="wtn-kpi-value">
            {{ kpis().modules_approved }}<span class="wtn-kpi-total"> / {{ kpis().modules_total }}</span>
          </div>
        </div>
      </div>

      <!-- Module cards -->
      <div class="wtn-section-label">Módulos da jornada</div>
      <div class="wtn-cards-grid">
        @for (card of cards(); track card.id) {
          @if (card.placeholder) {
            <div class="wtn-module-card wtn-module-card--future">
              <div class="wtn-module-card-header">
                <div class="wtn-module-title" style="color: var(--wtn-muted)">{{ card.title }}</div>
                <span class="wtn-tag wtn-tag--neutral">Em breve</span>
              </div>
              <div class="wtn-not-started" style="color: var(--wtn-muted)">{{ card.next_action.label }}</div>
            </div>
          } @else {
            <div class="wtn-module-card" (click)="go(card)" role="button" tabindex="0"
                 (keydown.enter)="go(card)">
              <div class="wtn-module-card-header">
                <div class="wtn-module-title">{{ card.title }}</div>
                <span class="wtn-tag {{ statusClass(card.status) }}">{{ statusLabel(card.status) }}</span>
              </div>

              @if (!card.not_started) {
                <div class="wtn-progress-row">
                  <span class="wtn-progress-label">Progresso</span>
                  <span class="wtn-progress-pct">{{ card.progress_pct !== null ? (card.progress_pct).toFixed(0) + '%' : '—' }}</span>
                </div>
                <div class="wtn-progress-bar">
                  <div class="wtn-progress-fill"
                       [style.width]="card.progress_pct !== null ? card.progress_pct + '%' : '0%'"
                       [class.wtn-progress-fill--success]="card.progress_pct !== null && card.progress_pct >= 75"
                       [class.wtn-progress-fill--warning]="card.progress_pct !== null && card.progress_pct >= 40 && card.progress_pct < 75"
                       [class.wtn-progress-fill--danger]="card.progress_pct !== null && card.progress_pct < 40">
                  </div>
                </div>
              } @else {
                <div class="wtn-not-started">Não iniciado</div>
              }

              @if (card.responsible) {
                <div class="wtn-responsible">
                  <div class="wtn-responsible-avatar">{{ card.responsible[0] }}</div>
                  <span>{{ card.responsible }}</span>
                </div>
              }

              @if (card.deadline) {
                <div class="wtn-deadline" [class.wtn-deadline--overdue]="card.overdue">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                    <rect x="3" y="4" width="18" height="18" rx="2" stroke="currentColor" stroke-width="1.7"/>
                    <path d="M3 9h18M8 2v4M16 2v4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
                  </svg>
                  {{ card.overdue ? 'Revisão vencida · ' : '' }}{{ card.deadline }}
                </div>
              }

              <a class="wtn-next-action" (click)="$event.stopPropagation(); go(card)"
                 (keydown.enter)="$event.stopPropagation(); go(card)" role="button" tabindex="0">
                {{ card.next_action.label }}
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
                  <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </a>
            </div>
          }
        }
      </div>
    }
  `,
  styles: `
    :host { display: block; }

    .wtn-loading-row {
      display: flex; align-items: center; gap: 12px;
      padding: 32px 0;
      color: var(--wtn-text-2);
    }

    /* KPI row */
    .wtn-kpi-row {
      display: grid;
      grid-template-columns: 1.5fr 1fr 1fr 1fr;
      gap: 14px;
      margin-bottom: 28px;
    }

    .wtn-kpi-card {
      background: var(--wtn-card);
      border: 1px solid var(--wtn-border);
      border-radius: var(--wtn-r-lg);
      padding: 18px;
      box-shadow: var(--wtn-e1);
    }
    .wtn-kpi-card--main { display: flex; flex-direction: column; gap: 4px; }
    .wtn-kpi-main-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
    .wtn-sparkline { width: 120px; height: 36px; flex: none; }

    .wtn-kpi-label {
      font-size: 11px; font-weight: 600;
      letter-spacing: .05em; text-transform: uppercase;
      color: var(--wtn-muted); margin-bottom: 8px;
    }
    .wtn-kpi-value {
      font-size: 32px; font-weight: 700;
      letter-spacing: -.02em; line-height: 1;
      color: var(--wtn-text);
    }
    .wtn-kpi-total { font-size: 15px; color: var(--wtn-muted); font-weight: 500; }
    .wtn-kpi-sub   { font-size: 11.5px; color: var(--wtn-muted); margin-top: 4px; }
    .wtn-danger-text { color: var(--wtn-danger) !important; }
    .wtn-muted { color: var(--wtn-muted) !important; }

    /* Section label */
    .wtn-section-label {
      font-size: 13px; font-weight: 600;
      color: var(--wtn-text);
      margin-bottom: 12px;
    }

    /* Cards grid */
    .wtn-cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 14px;
    }

    .wtn-module-card {
      background: var(--wtn-card);
      border: 1px solid var(--wtn-border);
      border-radius: var(--wtn-r-lg);
      padding: 16px;
      box-shadow: var(--wtn-e1);
      display: flex; flex-direction: column; gap: 12px;
      cursor: pointer;
      transition: box-shadow .15s, border-color .15s;
      outline: none;
      &:hover { box-shadow: var(--wtn-e2); border-color: var(--wtn-border-strong); }
      &:focus-visible { outline: 3px solid color-mix(in srgb, var(--wtn-focus) 40%, transparent); }
    }
    .wtn-module-card--future {
      opacity: .65; cursor: default;
      &:hover { box-shadow: var(--wtn-e1); border-color: var(--wtn-border); }
    }

    .wtn-module-card-header {
      display: flex; align-items: flex-start; justify-content: space-between; gap: 10px;
    }
    .wtn-module-title { font-size: 14px; font-weight: 600; color: var(--wtn-text); line-height: 1.3; }

    .wtn-progress-row {
      display: flex; justify-content: space-between;
      font-size: 11.5px; color: var(--wtn-text-2); margin-bottom: 5px;
    }
    .wtn-progress-pct { font-weight: 600; color: var(--wtn-text); }
    .wtn-progress-bar {
      height: 6px; border-radius: 999px;
      background: var(--wtn-surface-2); overflow: hidden;
    }
    .wtn-progress-fill {
      height: 100%; border-radius: 999px;
      background: var(--wtn-primary);
      transition: width .4s ease;
    }
    .wtn-progress-fill--success { background: var(--wtn-success); }
    .wtn-progress-fill--warning { background: var(--wtn-warning); }
    .wtn-progress-fill--danger  { background: var(--wtn-danger); }

    .wtn-not-started { font-size: 12.5px; color: var(--wtn-text-2); font-style: italic; }

    .wtn-responsible {
      display: flex; align-items: center; gap: 8px;
      font-size: 12px; color: var(--wtn-text-2);
    }
    .wtn-responsible-avatar {
      width: 22px; height: 22px; border-radius: 50%;
      background: var(--wtn-primary-soft); color: var(--wtn-primary);
      display: flex; align-items: center; justify-content: center;
      font-size: 10px; font-weight: 700; flex: none;
    }

    .wtn-deadline {
      display: flex; align-items: center; gap: 7px;
      font-size: 11.5px; color: var(--wtn-text-2);
    }
    .wtn-deadline--overdue { color: var(--wtn-danger); font-weight: 600; }

    .wtn-next-action {
      display: flex; align-items: center; justify-content: space-between;
      margin-top: 2px; padding-top: 11px;
      border-top: 1px solid var(--wtn-surface-2);
      font-size: 12.5px; font-weight: 600;
      color: var(--wtn-primary); text-decoration: none; cursor: pointer;
      &:hover { color: var(--wtn-primary-hover); }
    }
  `,
})
export class DashboardPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly store = inject(AuthStore);
  private readonly router = inject(Router);

  protected readonly loading = signal(true);
  protected readonly denied = signal(false);
  protected readonly orgNameSig = signal<string>('');
  protected readonly kpis = signal<DashboardKpis>({
    overall_adherence: null,
    controls_evaluated: 0,
    controls_total: 0,
    conformance_clause: null,
    conformance_annex: null,
    critical_gaps: 0,
    modules_approved: 0,
    modules_total: 0,
  });
  protected readonly cards = signal<ModuleCard[]>([]);
  protected readonly trend = signal<AdherencePoint[] | null>(null);

  protected orgName(): string {
    if (this.orgNameSig()) {
      return this.orgNameSig();
    }
    const me = this.store.me();
    const activeId = this.store.activeOrgId();
    if (!me || !activeId) return '';
    return me.memberships?.find((m) => m.tenant_id === activeId)?.org_name ?? '';
  }

  ngOnInit(): void {
    if (!this.store.activeOrgId()) {
      this.loading.set(false);
      return;
    }
    this.api
      .get<DashboardResponse>('/dashboard')
      .pipe(catchError(() => of(null)))
      .subscribe((res) => {
        if (!res) {
          this.denied.set(true);
          this.loading.set(false);
          return;
        }
        this.orgNameSig.set(res.organization_name);
        this.kpis.set(res.kpis);
        this.cards.set(res.cards);
        this.trend.set(res.adherence_trend);
        this.loading.set(false);
      });
  }

  protected pct(v: number | null): string {
    return v === null || v === undefined ? '—' : `${Math.round(v * 100)}%`;
  }

  protected statusLabel(status: string): string {
    return STATUS_LABEL[status] ?? status;
  }

  protected statusClass(status: string): string {
    return STATUS_CLASS[status] ?? 'wtn-tag--neutral';
  }

  /** Polyline points para o sparkline da série de aderência (US2). null se < 2 pontos. */
  protected sparkline(): string | null {
    const pts = this.trend();
    if (!pts || pts.length < 2) return null;
    const w = 120;
    const h = 36;
    const pad = 3;
    const max = Math.max(...pts.map((p) => p.adherence), 1);
    const min = Math.min(...pts.map((p) => p.adherence), 0);
    const span = max - min || 1;
    return pts
      .map((p, i) => {
        const x = pad + (i / (pts.length - 1)) * (w - 2 * pad);
        const y = h - pad - ((p.adherence - min) / span) * (h - 2 * pad);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
  }

  protected go(card: ModuleCard): void {
    if (card.placeholder) return;
    const route = card.next_action.route;
    const extras = card.next_action.fragment ? { fragment: card.next_action.fragment } : {};
    void this.router.navigate(['/app', route], extras);
  }
}
