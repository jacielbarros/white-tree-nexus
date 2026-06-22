import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MessageService } from 'primeng/api';

import { ApiService } from '@app/core/api.service';
import { Suggestion } from '@app/core/models';

/** Subconjunto do retorno de GET /context/overview que esta tela consome. */
interface ArtifactState {
  draft_status?: string;
  current_version_id?: string | null;
  review_overdue?: boolean;
}
interface ContextOverview {
  analysis?: ArtifactState & { issues?: unknown[] };
  stakeholders?: ArtifactState & { stakeholders?: unknown[] };
  scope?: ArtifactState & {
    items?: unknown[];
    context_ref_obsolete?: boolean;
    stakeholder_ref_obsolete?: boolean;
  };
}

interface ArtifactCard {
  key: string;
  title: string;
  clause: string;
  status: string;
  statusClass: string;
  count: number;
  countLabel: string;
  overdue: boolean;
  alerts: string[];
  route: string;
}

function statusOf(a: ArtifactState | undefined): { label: string; cls: string } {
  if (a?.current_version_id) {
    return a.review_overdue
      ? { label: 'Revisão vencida', cls: 'wtn-tag--warning' }
      : { label: 'Em vigor', cls: 'wtn-tag--success' };
  }
  if (a?.draft_status === 'in_review') return { label: 'Em revisão', cls: 'wtn-tag--info' };
  return { label: 'Rascunho', cls: 'wtn-tag--neutral' };
}

@Component({
  selector: 'app-context-overview-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <header class="wtn-page-header">
      <div>
        <h1 class="wtn-page-title">Visão Consolidada</h1>
        <p class="wtn-page-desc">
          Estado dos documentos controlados da Cláusula 4 · {{ approvedCount() }} de 3 em vigor.
        </p>
      </div>
    </header>

    @if (loading()) {
      <div class="wtn-loading-row">
        <div class="wtn-spinner"></div>
        <span class="wtn-text-2">Carregando visão consolidada…</span>
      </div>
    } @else {
      <div class="overview-grid">
        @for (card of cards(); track card.key) {
          <a class="artifact-card" [routerLink]="['/app', card.route]">
            <div class="artifact-card-head">
              <div>
                <div class="artifact-clause">{{ card.clause }}</div>
                <div class="artifact-title">{{ card.title }}</div>
              </div>
              <span class="wtn-tag {{ card.statusClass }}">{{ card.status }}</span>
            </div>

            <div class="artifact-count">
              <strong>{{ card.count }}</strong> {{ card.countLabel }}
            </div>

            @if (card.overdue || card.alerts.length) {
              <div class="artifact-alerts">
                @if (card.overdue) {
                  <span class="alert-chip alert-chip--warn">Revisão vencida</span>
                }
                @for (alert of card.alerts; track alert) {
                  <span class="alert-chip alert-chip--info">{{ alert }}</span>
                }
              </div>
            }

            <span class="artifact-link">
              Abrir
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" stroke-width="1.9"
                      stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </span>
          </a>
        }
      </div>

      <section class="suggestions-card">
        <div class="suggestions-head">
          <span>Sugestões</span>
          <span class="suggestions-count">{{ suggestions().length }}</span>
        </div>
        @if (suggestions().length === 0) {
          <div class="suggestions-empty">
            Sem sugestões no momento. Preencha o diagnóstico para gerar recomendações heurísticas.
          </div>
        } @else {
          <ul class="suggestions-list">
            @for (s of suggestions(); track s.id) {
              <li class="suggestion-row">
                <div class="suggestion-text">
                  <span class="suggestion-target">{{ targetLabel(s.target) }}</span>
                  <span>{{ s.reason }}</span>
                </div>
                <button type="button" class="accept-btn" (click)="accept(s)" [disabled]="accepting() === s.id">
                  {{ accepting() === s.id ? 'Aceitando…' : 'Aceitar' }}
                </button>
              </li>
            }
          </ul>
        }
      </section>
    }
  `,
  styles: `
    :host { display: block; }

    .wtn-loading-row {
      align-items: center;
      color: var(--wtn-text-2);
      display: flex;
      gap: 12px;
      padding: 32px 0;
    }

    .overview-grid {
      display: grid;
      gap: 14px;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      margin-bottom: 22px;
    }

    .artifact-card {
      background: var(--wtn-card);
      border: 1px solid var(--wtn-border);
      border-radius: var(--wtn-r-lg);
      box-shadow: var(--wtn-e1);
      color: inherit;
      display: flex;
      flex-direction: column;
      gap: 12px;
      padding: 16px;
      text-decoration: none;
      transition: box-shadow .15s, border-color .15s;
    }

    .artifact-card:hover {
      border-color: var(--wtn-border-strong);
      box-shadow: var(--wtn-e2);
    }

    .artifact-card-head {
      align-items: flex-start;
      display: flex;
      gap: 10px;
      justify-content: space-between;
    }

    .artifact-clause {
      color: var(--wtn-primary);
      font-family: var(--wtn-font-mono);
      font-size: 11px;
      font-weight: 600;
      margin-bottom: 3px;
    }

    .artifact-title {
      color: var(--wtn-text);
      font-size: 14px;
      font-weight: 600;
      line-height: 1.3;
    }

    .artifact-count {
      color: var(--wtn-text-2);
      font-size: 12.5px;
    }

    .artifact-count strong {
      color: var(--wtn-text);
      font-size: 18px;
      font-weight: 700;
      margin-right: 3px;
    }

    .artifact-alerts {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .alert-chip {
      border-radius: var(--wtn-r-pill);
      font-size: 10.5px;
      font-weight: 600;
      padding: 3px 9px;
    }

    .alert-chip--warn {
      background: var(--wtn-warning-soft);
      color: var(--wtn-warning);
    }

    .alert-chip--info {
      background: var(--wtn-info-soft);
      color: var(--wtn-info);
    }

    .artifact-link {
      align-items: center;
      border-top: 1px solid var(--wtn-surface-2);
      color: var(--wtn-primary);
      display: flex;
      font-size: 12.5px;
      font-weight: 600;
      gap: 6px;
      margin-top: auto;
      padding-top: 11px;
    }

    .suggestions-card {
      background: var(--wtn-card);
      border: 1px solid var(--wtn-border);
      border-radius: var(--wtn-r-lg);
      box-shadow: var(--wtn-e1);
      overflow: hidden;
    }

    .suggestions-head {
      align-items: center;
      border-bottom: 1px solid var(--wtn-surface-2);
      display: flex;
      gap: 9px;
      padding: 15px 20px;
    }

    .suggestions-head span:first-child {
      color: var(--wtn-text);
      font-size: 13px;
      font-weight: 600;
    }

    .suggestions-count {
      background: var(--wtn-surface-2);
      border-radius: var(--wtn-r-pill);
      color: var(--wtn-text-2);
      font-size: 11px;
      font-weight: 700;
      min-width: 20px;
      padding: 1px 8px;
      text-align: center;
    }

    .suggestions-empty {
      color: var(--wtn-text-2);
      font-size: 13px;
      padding: 20px;
    }

    .suggestions-list {
      list-style: none;
      margin: 0;
      padding: 0;
    }

    .suggestion-row {
      align-items: center;
      border-bottom: 1px solid var(--wtn-surface-2);
      display: flex;
      gap: 14px;
      justify-content: space-between;
      padding: 14px 20px;
    }

    .suggestion-row:last-child {
      border-bottom: 0;
    }

    .suggestion-text {
      align-items: center;
      color: var(--wtn-text);
      display: flex;
      flex-wrap: wrap;
      font-size: 13px;
      gap: 9px;
    }

    .suggestion-target {
      background: var(--wtn-primary-soft);
      border-radius: var(--wtn-r-pill);
      color: var(--wtn-primary);
      font-size: 10.5px;
      font-weight: 700;
      letter-spacing: .04em;
      padding: 3px 9px;
      text-transform: uppercase;
    }

    .accept-btn {
      background: var(--wtn-primary);
      border: 0;
      border-radius: var(--wtn-r-md);
      color: var(--wtn-primary-contrast);
      cursor: pointer;
      flex: none;
      font: inherit;
      font-size: 12.5px;
      font-weight: 600;
      padding: 7px 16px;
    }

    .accept-btn:hover:not(:disabled) {
      background: var(--wtn-primary-hover);
    }

    .accept-btn:disabled {
      cursor: not-allowed;
      opacity: .6;
    }
  `,
})
export class ContextOverviewPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly messages = inject(MessageService);

  protected readonly loading = signal(true);
  protected readonly overview = signal<ContextOverview | null>(null);
  protected readonly suggestions = signal<Suggestion[]>([]);
  protected readonly accepting = signal<string | null>(null);

  protected readonly cards = computed<ArtifactCard[]>(() => {
    const o = this.overview();
    if (!o) return [];
    const analysis = statusOf(o.analysis);
    const stakeholders = statusOf(o.stakeholders);
    const scope = statusOf(o.scope);
    const scopeAlerts: string[] = [];
    if (o.scope?.context_ref_obsolete) scopeAlerts.push('Referência de contexto obsoleta');
    if (o.scope?.stakeholder_ref_obsolete) scopeAlerts.push('Referência de partes obsoleta');

    return [
      {
        key: 'analysis',
        title: 'Análise de Contexto',
        clause: 'Cláusula 4.1',
        status: analysis.label,
        statusClass: analysis.cls,
        count: o.analysis?.issues?.length ?? 0,
        countLabel: 'questões (PESTEL/SWOT)',
        overdue: !!o.analysis?.review_overdue,
        alerts: [],
        route: 'context-analysis',
      },
      {
        key: 'stakeholders',
        title: 'Partes Interessadas',
        clause: 'Cláusula 4.2',
        status: stakeholders.label,
        statusClass: stakeholders.cls,
        count: o.stakeholders?.stakeholders?.length ?? 0,
        countLabel: 'partes mapeadas',
        overdue: !!o.stakeholders?.review_overdue,
        alerts: [],
        route: 'stakeholders',
      },
      {
        key: 'scope',
        title: 'Declaração de Escopo',
        clause: 'Cláusula 4.3',
        status: scope.label,
        statusClass: scope.cls,
        count: o.scope?.items?.length ?? 0,
        countLabel: 'itens de escopo',
        overdue: !!o.scope?.review_overdue,
        alerts: scopeAlerts,
        route: 'scope',
      },
    ];
  });

  protected readonly approvedCount = computed(
    () => this.cards().filter((c) => c.status === 'Em vigor').length,
  );

  ngOnInit(): void {
    this.load();
  }

  protected targetLabel(target: string): string {
    const map: Record<string, string> = {
      stakeholder: 'Parte interessada',
      analysis: 'Análise',
      scope: 'Escopo',
    };
    return map[target] ?? target;
  }

  protected accept(s: Suggestion): void {
    this.accepting.set(s.id);
    this.api.acceptSuggestion(s.id).subscribe({
      next: () => {
        this.messages.add({ severity: 'success', summary: 'Sugestão aceita', life: 2500 });
        this.accepting.set(null);
        this.load();
      },
      error: (e) => {
        this.messages.add({ severity: 'error', summary: 'Erro', detail: e.error?.detail ?? e.message });
        this.accepting.set(null);
      },
    });
  }

  private load(): void {
    this.api.getContextOverview().subscribe({
      next: (row) => {
        this.overview.set(row as ContextOverview);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
    this.api.listSuggestions().subscribe({ next: (rows) => this.suggestions.set(rows) });
  }
}
