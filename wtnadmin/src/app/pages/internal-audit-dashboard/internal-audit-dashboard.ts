import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';

import { ApiService } from '@app/core/api.service';
import { AuditDashboardData } from '@app/core/models';
import { AUDIT_STATUS_LABELS, FINDING_TYPE_LABELS } from '@app/pages/internal-audit/internal-audit-labels';

const CLASSIFICATION_LABELS: Record<string, string> = {
  publico: 'Público', uso_interno: 'Uso interno', confidencial: 'Confidencial', restrito: 'Restrito',
};
const EVIDENCE_STATUS_LABELS: Record<string, string> = { active: 'Ativas', inactive: 'Inativas' };

interface Cell { label: string; count: number; }

/** Dashboard do módulo Evidências & Auditoria Interna (Feature 014, US8). Contagens simples. */
@Component({
  selector: 'app-internal-audit-dashboard',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ButtonModule],
  template: `
    <header class="wtn-page-header">
      <div>
        <h1 class="wtn-page-title">Dashboard · Evidências & Auditoria</h1>
        <p class="wtn-page-desc">Visão consolidada de evidências e auditorias internas da organização.</p>
      </div>
      <p-button icon="pi pi-refresh" label="Atualizar" severity="secondary" (onClick)="load()" [loading]="loading()" />
    </header>

    @if (loading()) {
      <div class="wtn-card pad muted">Carregando indicadores…</div>
    } @else if (data(); as d) {
      <div class="cards">
        <section class="wtn-card pad">
          <div class="wtn-card-title">Evidências por estado</div>
          @for (c of evidenceByStatus(); track c.label) { <div class="cell"><span>{{ c.label }}</span><b>{{ c.count }}</b></div> }
          @if (!evidenceByStatus().length) { <p class="muted">Nenhuma evidência.</p> }
        </section>
        <section class="wtn-card pad">
          <div class="wtn-card-title">Evidências por classificação</div>
          @for (c of evidenceByClassification(); track c.label) { <div class="cell"><span>{{ c.label }}</span><b>{{ c.count }}</b></div> }
          @if (!evidenceByClassification().length) { <p class="muted">Nenhuma evidência ativa.</p> }
        </section>
        <section class="wtn-card pad">
          <div class="wtn-card-title">Auditorias por status</div>
          @for (c of auditsByStatus(); track c.label) { <div class="cell"><span>{{ c.label }}</span><b>{{ c.count }}</b></div> }
          @if (!auditsByStatus().length) { <p class="muted">Nenhuma auditoria.</p> }
        </section>
        <section class="wtn-card pad">
          <div class="wtn-card-title">Constatações por tipo</div>
          @for (c of findingsByType(); track c.label) { <div class="cell"><span>{{ c.label }}</span><b>{{ c.count }}</b></div> }
          @if (!findingsByType().length) { <p class="muted">Nenhuma constatação.</p> }
        </section>
      </div>
    } @else {
      <div class="wtn-empty"><div class="wtn-empty-title">Sem dados</div></div>
    }
  `,
  styles: `
    :host { display: block; }
    .muted { color: var(--wtn-text-2); }
    .cards { display: grid; gap: 12px; grid-template-columns: repeat(2, 1fr); }
    @media (max-width: 880px) { .cards { grid-template-columns: 1fr; } }
    .cell { align-items: center; border-top: 1px solid var(--wtn-border); display: flex; justify-content: space-between; padding: 7px 0; }
    .cell span { color: var(--wtn-text-2); font-size: 12.5px; }
    .cell b { color: var(--wtn-text); font-size: 14px; }
  `,
})
export class InternalAuditDashboardPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly messages = inject(MessageService);

  protected readonly loading = signal(false);
  protected readonly data = signal<AuditDashboardData | null>(null);

  protected readonly evidenceByStatus = computed(() => this.cells(this.data()?.evidence_by_status, EVIDENCE_STATUS_LABELS));
  protected readonly evidenceByClassification = computed(() => this.cells(this.data()?.evidence_by_classification, CLASSIFICATION_LABELS));
  protected readonly auditsByStatus = computed(() => this.cells(this.data()?.audits_by_status, AUDIT_STATUS_LABELS));
  protected readonly findingsByType = computed(() => this.cells(this.data()?.findings_by_type, FINDING_TYPE_LABELS));

  ngOnInit(): void {
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    this.api.get<AuditDashboardData>('/internal-audit/dashboard').subscribe({
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

  private cells(dict: Record<string, number> | undefined, labels: Record<string, string>): Cell[] {
    if (!dict) return [];
    return Object.entries(dict).map(([key, count]) => ({ label: labels[key] ?? key, count }));
  }

  private errorDetail(error: unknown): string {
    if (typeof error === 'object' && error && 'error' in error) {
      const payload = (error as { error?: { detail?: string } }).error;
      if (payload?.detail) return payload.detail;
    }
    return 'Operação não concluída.';
  }
}
