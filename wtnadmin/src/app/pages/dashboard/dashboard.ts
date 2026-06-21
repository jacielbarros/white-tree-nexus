import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';

interface ModuleCard {
  id: string;
  title: string;
  status: string;
  statusClass: string;
  pct: number | null;
  responsible: string | null;
  deadline: string | null;
  overdue: boolean;
  nextAction: string;
  nextRoute: string;
  notStarted: boolean;
}

interface GapDashboardData {
  overall_adherence: number | null;
  completeness: number;
  status_distribution: Record<string, number>;
  gaps_by_priority?: Record<string, number>;
}

interface SoaData {
  draft_status: string;
  current_version_id: string | null;
  items?: Array<{ implementation_status: string | null }>;
}

interface ContextOverview {
  scope?: { draft_status?: string; current_version_id?: string | null };
  analysis?: { draft_status?: string; current_version_id?: string | null };
}

const STATUS_LABEL: Record<string, string> = {
  draft: 'Rascunho',
  under_review: 'Em revisão',
  approved: 'Aprovado',
};

const STATUS_CLASS: Record<string, string> = {
  draft: 'wtn-tag--neutral',
  under_review: 'wtn-tag--info',
  approved: 'wtn-tag--success',
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
    } @else {
      <!-- KPI row -->
      <div class="wtn-kpi-row">
        <div class="wtn-kpi-card wtn-kpi-card--main">
          <div class="wtn-kpi-label">Conformidade geral</div>
          @if (gapAdherence() !== null) {
            <div class="wtn-kpi-value">{{ (gapAdherence()! * 100).toFixed(0) }}%</div>
          } @else {
            <div class="wtn-kpi-value wtn-muted">—</div>
          }
          <div class="wtn-kpi-sub">Gap Analysis · Anexo A</div>
        </div>
        <div class="wtn-kpi-card">
          <div class="wtn-kpi-label">Controles avaliados</div>
          <div class="wtn-kpi-value">
            {{ evaluatedCount() }}<span class="wtn-kpi-total"> / 93</span>
          </div>
        </div>
        <div class="wtn-kpi-card">
          <div class="wtn-kpi-label">Lacunas críticas</div>
          <div class="wtn-kpi-value" [class.wtn-danger-text]="criticalCount() > 0">
            {{ criticalCount() }}
          </div>
        </div>
        <div class="wtn-kpi-card">
          <div class="wtn-kpi-label">Módulos aprovados</div>
          <div class="wtn-kpi-value">
            {{ approvedCount() }}<span class="wtn-kpi-total"> / {{ cards().length }}</span>
          </div>
        </div>
      </div>

      <!-- Module cards -->
      <div class="wtn-section-label">Módulos da jornada</div>
      <div class="wtn-cards-grid">
        @for (card of cards(); track card.id) {
          <div class="wtn-module-card" (click)="navigate(card.nextRoute)" role="button" tabindex="0"
               (keydown.enter)="navigate(card.nextRoute)">
            <div class="wtn-module-card-header">
              <div class="wtn-module-title">{{ card.title }}</div>
              <span class="wtn-tag {{ card.statusClass }}">{{ card.status }}</span>
            </div>

            @if (!card.notStarted) {
              <div class="wtn-progress-row">
                <span class="wtn-progress-label">Progresso</span>
                <span class="wtn-progress-pct">{{ card.pct !== null ? (card.pct).toFixed(0) + '%' : '—' }}</span>
              </div>
              <div class="wtn-progress-bar">
                <div class="wtn-progress-fill"
                     [style.width]="card.pct !== null ? card.pct + '%' : '0%'"
                     [class.wtn-progress-fill--success]="card.pct !== null && card.pct >= 75"
                     [class.wtn-progress-fill--warning]="card.pct !== null && card.pct >= 40 && card.pct < 75"
                     [class.wtn-progress-fill--danger]="card.pct !== null && card.pct < 40">
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

            <a class="wtn-next-action" (click)="$event.stopPropagation(); navigate(card.nextRoute)"
               (keydown.enter)="$event.stopPropagation(); navigate(card.nextRoute)" role="button" tabindex="0">
              {{ card.nextAction }}
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
                <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </a>
          </div>
        }

        <!-- Placeholder cards (futuros) -->
        <div class="wtn-module-card wtn-module-card--future">
          <div class="wtn-module-card-header">
            <div class="wtn-module-title" style="color: var(--wtn-muted)">Plano de Ação</div>
            <span class="wtn-tag wtn-tag--neutral">Em breve</span>
          </div>
          <div class="wtn-not-started" style="color: var(--wtn-muted)">Módulo 4 — não iniciado</div>
        </div>

        <div class="wtn-module-card wtn-module-card--future">
          <div class="wtn-module-card-header">
            <div class="wtn-module-title" style="color: var(--wtn-muted)">Gestão de Evidências</div>
            <span class="wtn-tag wtn-tag--neutral">Em breve</span>
          </div>
          <div class="wtn-not-started" style="color: var(--wtn-muted)">Módulo 5 — não iniciado</div>
        </div>
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
  protected readonly gapAdherence = signal<number | null>(null);
  protected readonly evaluatedCount = signal(0);
  protected readonly criticalCount = signal(0);
  protected readonly approvedCount = signal(0);
  protected readonly cards = signal<ModuleCard[]>([]);

  protected orgName(): string {
    const me = this.store.me();
    const activeId = this.store.activeOrgId();
    if (!me || !activeId) return '';
    const mem = me.memberships?.find((m) => m.tenant_id === activeId);
    return mem?.org_name ?? '';
  }

  ngOnInit(): void {
    if (!this.store.activeOrgId()) {
      this.loading.set(false);
      this.cards.set(this.buildCards(null, null, null));
      return;
    }
    this.load();
  }

  private load(): void {
    forkJoin({
      gap: this.api.get<GapDashboardData>('/gap-assessment/dashboard').pipe(catchError(() => of(null))),
      soa: this.api.get<SoaData>('/soa').pipe(catchError(() => of(null))),
      ctx: this.api.get<ContextOverview>('/context/overview').pipe(catchError(() => of(null))),
    }).subscribe({
      next: ({ gap, soa, ctx }) => {
        this.gapAdherence.set(gap?.overall_adherence ?? null);

        const dist = gap?.status_distribution ?? {};
        const evaluated = Object.entries(dist)
          .filter(([k]) => k !== 'not_filled')
          .reduce((acc, [, v]) => acc + v, 0);
        this.evaluatedCount.set(evaluated);
        this.criticalCount.set(dist['not_meet'] ?? 0);

        const builtCards = this.buildCards(gap, soa, ctx);
        this.cards.set(builtCards);
        this.approvedCount.set(builtCards.filter((c) => c.statusClass === 'wtn-tag--success').length);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.cards.set(this.buildCards(null, null, null));
      },
    });
  }

  private buildCards(
    gap: GapDashboardData | null,
    soa: SoaData | null,
    ctx: ContextOverview | null,
  ): ModuleCard[] {
    const cards: ModuleCard[] = [];

    /* ── Contexto (Cláusula 4) ── */
    const ctxStatus = ctx?.scope?.draft_status ?? ctx?.analysis?.draft_status ?? 'draft';
    const ctxApproved = !!(ctx?.scope?.current_version_id);
    cards.push({
      id: 'context',
      title: 'Contexto · Cláusula 4',
      status: STATUS_LABEL[ctxStatus] ?? ctxStatus,
      statusClass: STATUS_CLASS[ctxStatus] ?? 'wtn-tag--neutral',
      pct: ctxApproved ? 100 : null,
      responsible: null,
      deadline: null,
      overdue: false,
      nextAction: ctxApproved ? 'Ver visão consolidada' : 'Completar análise de contexto',
      nextRoute: ctxApproved ? 'context-overview' : 'context-analysis',
      notStarted: !ctx?.analysis,
    });

    /* ── Gap Analysis ── */
    const gapPct = gap?.completeness != null ? gap.completeness * 100 : null;
    const gapAdherence = gap?.overall_adherence != null ? gap.overall_adherence * 100 : null;
    const gapStatus = gapAdherence !== null ? 'under_review' : 'draft';
    cards.push({
      id: 'gap',
      title: 'Gap Analysis · Anexo A',
      status: STATUS_LABEL[gapStatus],
      statusClass: STATUS_CLASS[gapStatus],
      pct: gapAdherence,
      responsible: null,
      deadline: null,
      overdue: false,
      nextAction: (gap?.completeness ?? 0) >= 1 ? 'Ver dashboard de aderência' : 'Avaliar controles',
      nextRoute: (gap?.completeness ?? 0) >= 1 ? 'gap-dashboard' : 'gap-analysis',
      notStarted: gap === null,
    });

    /* ── SoA ── */
    const soaStatus = soa?.draft_status ?? 'draft';
    const soaItems = soa?.items ?? [];
    const soaFilled = soaItems.filter((i) => i.implementation_status !== null).length;
    const soaPct = soaItems.length > 0 ? (soaFilled / soaItems.length) * 100 : null;
    cards.push({
      id: 'soa',
      title: 'Declaração de Aplicabilidade',
      status: STATUS_LABEL[soaStatus] ?? soaStatus,
      statusClass: STATUS_CLASS[soaStatus] ?? 'wtn-tag--neutral',
      pct: soaPct,
      responsible: null,
      deadline: null,
      overdue: false,
      nextAction: soaStatus === 'approved' ? 'Ver versões da SoA' : 'Completar declaração',
      nextRoute: soaStatus === 'approved' ? 'soa-versions' : 'soa',
      notStarted: soa === null,
    });

    return cards;
  }

  protected navigate(route: string): void {
    void this.router.navigate(['/app', route]);
  }
}
