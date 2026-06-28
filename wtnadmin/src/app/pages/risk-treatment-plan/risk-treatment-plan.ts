import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { hasPermission } from '@app/core/permissions';
import { RiskPlan, SoaFeedItem } from '@app/core/models';

interface PlanVersion { id: string; version_number: number; status: string; classification: string | null; }

@Component({
  selector: 'app-risk-treatment-plan',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, ButtonModule],
  template: `
    <header class="wtn-page-header">
      <div>
        <h1 class="wtn-page-title">Plano de Tratamento de Riscos · Fase 3</h1>
        <p class="wtn-page-desc">Documento Controlado consolidado (6.1.3). Aprovar exige riscos avaliados.</p>
      </div>
    </header>

    @if (plan(); as p) {
      <section class="wtn-card pad">
        <div class="rows">
          <div class="row"><span>Status do rascunho</span><strong>{{ statusLabel(p.draft_status) }}</strong></div>
          <div class="row"><span>Versão em vigor</span><strong>{{ p.current_version_id ? 'Sim' : '—' }}</strong></div>
        </div>
        @if (error()) { <p class="err">{{ error() }}</p> }
        @if (canManage()) {
          <div class="actions">
            <p-button label="Enviar para revisão" icon="pi pi-send" severity="secondary" (onClick)="submit()" [disabled]="busy()" />
            @if (canApprove()) {
              <span class="approve-box">
                <input class="wtn-input" placeholder="Natureza da mudança" [(ngModel)]="changeNature" />
                <label class="chk"><input type="checkbox" [(ngModel)]="sign" /> Assinar</label>
                <p-button label="Aprovar" icon="pi pi-verified" (onClick)="approve()" [disabled]="busy()" />
              </span>
            }
          </div>
        }
      </section>

      <section class="wtn-card pad">
        <div class="wtn-card-title">Versões</div>
        @for (v of versions(); track v.id) {
          <div class="ver-row"><strong>v{{ v.version_number }}</strong><span>{{ v.status }}</span><span class="muted">{{ v.classification }}</span></div>
        } @empty { <p class="muted">Nenhuma versão aprovada ainda.</p> }
      </section>

      <section class="wtn-card pad">
        <div class="wtn-card-title">Insumo da SoA (controle ← risco · read-only)</div>
        <p class="hint">Este vínculo alimenta a SoA definitiva; o módulo de Riscos não escreve na SoA.</p>
        @for (f of soaFeed(); track f.gap_catalog_item_id) {
          <div class="feed-row"><strong>{{ f.ref_code }}</strong><span class="muted">{{ f.inclusion_reason }}</span>
            <span>{{ f.risk_codes.join(', ') }}</span></div>
        } @empty { <p class="muted">Nenhum controle de mitigação selecionado.</p> }
      </section>
    } @else {
      <div class="wtn-card pad"><div class="wtn-skeleton skeleton-line"></div></div>
    }
  `,
  styles: [`
    :host { display: block; }
    .wtn-card { background: var(--wtn-card); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-lg); margin-bottom: 16px; }
    .pad { padding: 18px 20px; }
    .wtn-card-title { color: var(--wtn-muted); font-size: 11px; font-weight: 600; letter-spacing: .05em; text-transform: uppercase; margin-bottom: 12px; }
    .rows { display: flex; flex-direction: column; gap: 8px; margin-bottom: 14px; }
    .row { display: flex; justify-content: space-between; font-size: 13px; color: var(--wtn-text-2); } .row strong { color: var(--wtn-text); }
    .actions { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
    .approve-box { display: flex; gap: 8px; align-items: center; }
    .wtn-input { background: var(--wtn-surface); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); padding: 8px 10px; font-size: 13px; color: var(--wtn-text); }
    .chk { font-size: 13px; color: var(--wtn-text-2); display: flex; gap: 5px; align-items: center; }
    .ver-row, .feed-row { display: grid; grid-template-columns: 80px 1fr 1fr; gap: 10px; font-size: 13px; padding: 7px 0; border-bottom: 1px solid var(--wtn-border); }
    .hint { font-size: 12px; color: var(--wtn-muted); margin-bottom: 10px; }
    .err { color: var(--wtn-danger); font-size: 13px; } .muted { color: var(--wtn-muted); } .skeleton-line { height: 18px; }
  `],
})
export class RiskTreatmentPlanPage implements OnInit {
  private api = inject(ApiService);
  private store = inject(AuthStore);

  readonly plan = signal<RiskPlan | null>(null);
  readonly versions = signal<PlanVersion[]>([]);
  readonly soaFeed = signal<SoaFeedItem[]>([]);
  readonly busy = signal(false);
  readonly error = signal<string | null>(null);
  changeNature = '';
  sign = false;

  ngOnInit(): void { this.reload(); }

  reload(): void {
    this.api.get<RiskPlan>('/risk/plan').subscribe((p) => this.plan.set(p));
    this.api.get<PlanVersion[]>('/risk/plan/versions').subscribe((v) => this.versions.set(v));
    this.api.get<SoaFeedItem[]>('/risk/soa-feed').subscribe((f) => this.soaFeed.set(f));
  }

  canManage(): boolean { return hasPermission(this.store.currentRole(), 'manage_risk'); }
  canApprove(): boolean { return hasPermission(this.store.currentRole(), 'approve_risk_plan'); }

  submit(): void {
    this.busy.set(true); this.error.set(null);
    this.api.post<RiskPlan>('/risk/plan/submit-review', {}).subscribe({
      next: () => { this.busy.set(false); this.reload(); },
      error: (e) => { this.busy.set(false); this.error.set(e?.error?.detail ?? 'Falha ao enviar para revisão.'); },
    });
  }

  approve(): void {
    this.busy.set(true); this.error.set(null);
    this.api.post('/risk/plan/approve', { change_nature: this.changeNature || 'Aprovação do plano', sign: this.sign }).subscribe({
      next: () => { this.busy.set(false); this.reload(); },
      error: (e) => { this.busy.set(false); this.error.set(e?.error?.detail ?? 'Falha ao aprovar (avalie os riscos pendentes).'); },
    });
  }

  statusLabel(s: string): string {
    return ({ draft: 'Rascunho', in_review: 'Em revisão', in_force: 'Em vigor' } as Record<string, string>)[s] ?? s;
  }
}
