import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ButtonModule } from 'primeng/button';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { hasPermission } from '@app/core/permissions';
import { MembershipRow, Risk, RiskControl, RiskEvent } from '@app/core/models';
import { RISK_STATUS_LABELS, TREATMENT_LABELS, levelColor, levelLabel } from '@app/pages/risks/risk-labels';

interface GapItem { id: string; ref_code: string; name: string; dimension: string; }

@Component({
  selector: 'app-risk-detail',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, FormsModule, ButtonModule, DatePipe],
  template: `
    <a routerLink="../../risks" class="back">← Voltar ao registro</a>

    @if (risk(); as r) {
      <header class="wtn-page-header">
        <div>
          <h1 class="wtn-page-title"><span class="mono">{{ r.code }}</span> · {{ r.title }}</h1>
          <p class="wtn-page-desc">{{ r.description }}</p>
        </div>
        <div class="wtn-page-actions">
          <span class="level-chip" [style.background]="levelBg(r.inherent_level_key)">Inerente: {{ level(r.inherent_level_key) }}</span>
          <span class="badge">{{ statusLabel(r.status) }}</span>
        </div>
      </header>

      <div class="cols">
        <!-- Avaliação (6.1.2) -->
        <section class="wtn-card pad">
          <div class="wtn-card-title">Avaliação (6.1.2)</div>
          <div class="rows">
            <div class="row"><span>Probabilidade</span><strong>{{ r.probability_level ?? '—' }}</strong></div>
            <div class="row"><span>Impacto</span><strong>{{ r.impact_level ?? '—' }}
              @if (r.impact_is_override) { <em class="ovr">(override)</em> }
              @else if (r.impact_derived_level) { <em class="der">(da CIA)</em> }</strong></div>
            <div class="row"><span>Nível inerente</span><strong [style.color]="levelBg(r.inherent_level_key)">{{ level(r.inherent_level_key) }}</strong></div>
            <div class="row"><span>Critério</span><strong>{{ r.above_acceptance === true ? 'Acima do critério' : r.above_acceptance === false ? 'Atende' : '—' }}</strong></div>
          </div>

          @if (canManage()) {
            <div class="eval-form">
              <label class="fld"><span>Probabilidade (1–5)</span>
                <select class="wtn-input" [(ngModel)]="evalProb"><option [ngValue]="null">—</option>
                  @for (n of [1,2,3,4,5]; track n) { <option [ngValue]="n">{{ n }}</option> }</select></label>
              <label class="fld"><span>Impacto (1–5, vazio = derivar da CIA)</span>
                <select class="wtn-input" [(ngModel)]="evalImpact"><option [ngValue]="null">Derivar da CIA</option>
                  @for (n of [1,2,3,4,5]; track n) { <option [ngValue]="n">{{ n }}</option> }</select></label>
              <label class="fld"><span>Justificativa do override (se aplicável)</span>
                <input class="wtn-input" [(ngModel)]="overrideReason" /></label>
              <label class="fld"><span>Dono do risco</span>
                <select class="wtn-input" [(ngModel)]="evalOwner"><option [ngValue]="null">—</option>
                  @for (m of members(); track m.user_id) { <option [ngValue]="m.user_id">{{ m.full_name || m.email }}</option> }</select></label>
              @if (evalError()) { <p class="err">{{ evalError() }}</p> }
              <p-button label="Salvar avaliação" icon="pi pi-check" (onClick)="saveEval()" [disabled]="saving()" />
            </div>
          }
        </section>

        <!-- Tratamento (6.1.3) -->
        <section class="wtn-card pad">
          <div class="wtn-card-title">Tratamento (6.1.3)</div>
          <div class="rows">
            <div class="row"><span>Opção</span><strong>{{ r.treatment_option ? treatmentLabel(r.treatment_option) : '—' }}</strong></div>
            <div class="row"><span>Residual</span><strong [style.color]="levelBg(r.residual_level_key)">{{ level(r.residual_level_key) }}
              @if (r.residual_above_acceptance === false) { <em class="der">(atende)</em> }
              @else if (r.residual_above_acceptance === true) { <em class="ovr">(pendente)</em> }</strong></div>
          </div>

          @if (canManage()) {
            <div class="eval-form">
              <label class="fld"><span>Opção de tratamento</span>
                <select class="wtn-input" [(ngModel)]="treatOption">
                  <option [ngValue]="null">—</option>
                  @for (o of treatmentKeys; track o) { <option [ngValue]="o">{{ treatmentLabel(o) }}</option> }</select></label>
              <div class="grid2">
                <label class="fld"><span>Residual prob.</span>
                  <select class="wtn-input" [(ngModel)]="resProb"><option [ngValue]="null">—</option>
                    @for (n of [1,2,3,4,5]; track n) { <option [ngValue]="n">{{ n }}</option> }</select></label>
                <label class="fld"><span>Residual impacto</span>
                  <select class="wtn-input" [(ngModel)]="resImpact"><option [ngValue]="null">—</option>
                    @for (n of [1,2,3,4,5]; track n) { <option [ngValue]="n">{{ n }}</option> }</select></label>
              </div>
              <label class="fld"><span>Justificativa</span><input class="wtn-input" [(ngModel)]="treatReason" /></label>
              <p-button label="Salvar tratamento" icon="pi pi-shield" severity="secondary" (onClick)="saveTreatment()" [disabled]="!treatOption || saving()" />
            </div>

            <!-- Controles -->
            <div class="sub-title">Controles selecionados</div>
            @for (c of controls(); track c.id) {
              <div class="control-row">
                <span>{{ c.custom_control_label || gapName(c.gap_catalog_item_id) }}</span>
                <p-button icon="pi pi-trash" size="small" text="true" severity="danger" (onClick)="removeControl(c.id)" />
              </div>
            } @empty { <p class="muted">Nenhum controle.</p> }

            <div class="add-control">
              <select class="wtn-input" [(ngModel)]="newGapId">
                <option [ngValue]="null">Controle do Anexo A…</option>
                @for (g of gapControls(); track g.id) { <option [ngValue]="g.id">{{ g.ref_code }} · {{ g.name }}</option> }
              </select>
              <input class="wtn-input" placeholder="ou controle custom" [(ngModel)]="newCustom" />
              <select class="wtn-input" [(ngModel)]="newResp"><option [ngValue]="null">Responsável…</option>
                @for (m of members(); track m.user_id) { <option [ngValue]="m.user_id">{{ m.full_name || m.email }}</option> }</select>
              <input class="wtn-input" type="date" [(ngModel)]="newDue" />
              <p-button label="Add controle" icon="pi pi-plus" size="small" (onClick)="addControl()" [disabled]="saving()" />
            </div>
            @if (controlError()) { <p class="err">{{ controlError() }}</p> }

            <!-- Aceitação -->
            <div class="sub-title">Aceitar risco</div>
            <div class="add-control">
              <input class="wtn-input grow" placeholder="Justificativa de aceitação" [(ngModel)]="acceptReason" />
              <select class="wtn-input" [(ngModel)]="acceptOwner"><option [ngValue]="null">Dono…</option>
                @for (m of members(); track m.user_id) { <option [ngValue]="m.user_id">{{ m.full_name || m.email }}</option> }</select>
              <p-button label="Aceitar" icon="pi pi-check-circle" severity="warn" (onClick)="accept()" [disabled]="!acceptReason || !acceptOwner || saving()" />
            </div>
            @if (acceptError()) { <p class="err">{{ acceptError() }}</p> }
          }
        </section>
      </div>

      <!-- Histórico -->
      <section class="wtn-card pad">
        <div class="wtn-card-title">Histórico</div>
        @for (e of history(); track e.id) {
          <div class="hist-row">
            <span class="hist-type">{{ e.event_type }}</span>
            <span class="hist-detail">{{ e.field_name }} {{ e.old_value }} → {{ e.new_value }} {{ e.reason ? '· ' + e.reason : '' }}</span>
            <span class="hist-date">{{ e.occurred_at | date:'short' }}</span>
          </div>
        } @empty { <p class="muted">Sem eventos.</p> }
      </section>
    } @else if (loading()) {
      <div class="wtn-card pad"><div class="wtn-skeleton skeleton-line"></div></div>
    } @else {
      <div class="wtn-empty"><div class="wtn-empty-title">Risco não encontrado</div></div>
    }
  `,
  styles: [`
    :host { display: block; }
    .back { color: var(--wtn-muted); font-size: 13px; text-decoration: none; }
    .wtn-card { background: var(--wtn-card); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-lg); margin-bottom: 16px; }
    .pad { padding: 18px 20px; }
    .wtn-card-title { color: var(--wtn-muted); font-size: 11px; font-weight: 600; letter-spacing: .05em; text-transform: uppercase; margin-bottom: 14px; }
    .cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 16px; }
    .rows { display: flex; flex-direction: column; gap: 8px; margin-bottom: 14px; }
    .row { display: flex; justify-content: space-between; font-size: 13px; color: var(--wtn-text-2); }
    .row strong { color: var(--wtn-text); }
    .ovr { color: var(--wtn-warning); font-style: normal; font-size: 11px; } .der { color: var(--wtn-muted); font-style: normal; font-size: 11px; }
    .eval-form { display: flex; flex-direction: column; gap: 10px; border-top: 1px solid var(--wtn-border); padding-top: 14px; }
    .fld { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--wtn-muted); }
    .fld span { font-weight: 600; }
    .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .wtn-input { background: var(--wtn-surface); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); padding: 8px 10px; font-size: 13px; color: var(--wtn-text); width: 100%; box-sizing: border-box; }
    .sub-title { font-size: 12px; font-weight: 700; color: var(--wtn-text-2); margin: 16px 0 8px; }
    .control-row { display: flex; justify-content: space-between; align-items: center; font-size: 13px; padding: 6px 0; border-bottom: 1px solid var(--wtn-border); }
    .add-control { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 8px; }
    .add-control .wtn-input { width: auto; flex: 1; min-width: 140px; } .grow { flex: 2 !important; }
    .level-chip { color: #fff; padding: 3px 10px; border-radius: var(--wtn-r-pill); font-size: 12px; font-weight: 600; }
    .badge { background: var(--wtn-surface-2); color: var(--wtn-text-2); padding: 3px 10px; border-radius: var(--wtn-r-pill); font-size: 12px; }
    .mono { font-family: var(--wtn-font-mono, monospace); }
    .hist-row { display: grid; grid-template-columns: 150px 1fr auto; gap: 10px; font-size: 12.5px; padding: 6px 0; border-bottom: 1px solid var(--wtn-border); }
    .hist-type { font-weight: 700; color: var(--wtn-primary); } .hist-detail { color: var(--wtn-text-2); } .hist-date { color: var(--wtn-muted); }
    .err { color: var(--wtn-danger); font-size: 13px; } .muted { color: var(--wtn-muted); font-size: 13px; } .skeleton-line { height: 18px; }
  `],
})
export class RiskDetailPage implements OnInit {
  private api = inject(ApiService);
  private store = inject(AuthStore);
  private route = inject(ActivatedRoute);

  readonly treatmentKeys = Object.keys(TREATMENT_LABELS);
  readonly risk = signal<Risk | null>(null);
  readonly controls = signal<RiskControl[]>([]);
  readonly history = signal<RiskEvent[]>([]);
  readonly members = signal<MembershipRow[]>([]);
  readonly gapControls = signal<GapItem[]>([]);
  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly evalError = signal<string | null>(null);
  readonly controlError = signal<string | null>(null);
  readonly acceptError = signal<string | null>(null);

  private id = '';
  evalProb: number | null = null;
  evalImpact: number | null = null;
  overrideReason = '';
  evalOwner: string | null = null;
  treatOption: string | null = null;
  resProb: number | null = null;
  resImpact: number | null = null;
  treatReason = '';
  newGapId: string | null = null;
  newCustom = '';
  newResp: string | null = null;
  newDue = '';
  acceptReason = '';
  acceptOwner: string | null = null;

  ngOnInit(): void {
    this.id = this.route.snapshot.paramMap.get('id') ?? '';
    this.load();
    this.api.listUsers().subscribe({ next: (m) => this.members.set(m), error: () => {} });
    this.api.get<GapItem[]>('/gap/catalog').subscribe({
      next: (g) => this.gapControls.set(g.filter((x) => x.dimension === 'annex_a')),
      error: () => {},
    });
  }

  load(): void {
    this.api.get<Risk>(`/risk/risks/${this.id}`).subscribe({
      next: (r) => {
        this.risk.set(r); this.loading.set(false);
        this.evalProb = r.probability_level; this.evalOwner = r.owner_user_id;
        this.treatOption = r.treatment_option; this.resProb = r.residual_probability_level; this.resImpact = r.residual_impact_level;
      },
      error: () => this.loading.set(false),
    });
    this.api.get<RiskControl[]>(`/risk/risks/${this.id}/controls`).subscribe({ next: (c) => this.controls.set(c), error: () => {} });
    this.api.get<RiskEvent[]>(`/risk/risks/${this.id}/history`).subscribe({ next: (h) => this.history.set(h), error: () => {} });
  }

  canManage(): boolean { return hasPermission(this.store.currentRole(), 'manage_risk'); }

  saveEval(): void {
    this.saving.set(true); this.evalError.set(null);
    const body: Record<string, unknown> = { probability_level: this.evalProb, owner_user_id: this.evalOwner };
    if (this.evalImpact !== null) body['impact_level'] = this.evalImpact;
    if (this.overrideReason) body['impact_override_reason'] = this.overrideReason;
    this.api.put<Risk>(`/risk/risks/${this.id}`, body).subscribe({
      next: () => { this.saving.set(false); this.load(); },
      error: (e) => { this.saving.set(false); this.evalError.set(e?.error?.detail ?? 'Falha ao salvar.'); },
    });
  }

  saveTreatment(): void {
    if (!this.treatOption) return;
    this.saving.set(true);
    this.api.put<Risk>(`/risk/risks/${this.id}/treatment`, {
      treatment_option: this.treatOption, residual_probability_level: this.resProb,
      residual_impact_level: this.resImpact, reason: this.treatReason || null,
    }).subscribe({ next: () => { this.saving.set(false); this.load(); }, error: () => this.saving.set(false) });
  }

  addControl(): void {
    this.saving.set(true); this.controlError.set(null);
    this.api.post<RiskControl>(`/risk/risks/${this.id}/controls`, {
      gap_catalog_item_id: this.newGapId, custom_control_label: this.newCustom || null,
      responsible_user_id: this.newResp, due_date: this.newDue || null,
    }).subscribe({
      next: () => { this.saving.set(false); this.newGapId = null; this.newCustom = ''; this.newResp = null; this.newDue = ''; this.load(); },
      error: (e) => { this.saving.set(false); this.controlError.set(e?.error?.detail ?? 'Falha ao adicionar controle.'); },
    });
  }

  removeControl(controlId: string): void {
    this.api.delete<void>(`/risk/risks/${this.id}/controls/${controlId}`).subscribe({ next: () => this.load() });
  }

  accept(): void {
    this.saving.set(true); this.acceptError.set(null);
    this.api.post<Risk>(`/risk/risks/${this.id}/accept`, {
      acceptance_reason: this.acceptReason, accepted_owner_user_id: this.acceptOwner,
    }).subscribe({
      next: () => { this.saving.set(false); this.acceptReason = ''; this.acceptOwner = null; this.load(); },
      error: (e) => { this.saving.set(false); this.acceptError.set(e?.error?.detail ?? 'Falha ao aceitar.'); },
    });
  }

  gapName(id: string | null): string {
    const g = this.gapControls().find((x) => x.id === id);
    return g ? `${g.ref_code} · ${g.name}` : (id ?? '—');
  }
  level(k: string | null): string { return levelLabel(k); }
  levelBg(k: string | null): string { return levelColor(k); }
  statusLabel(s: string): string { return RISK_STATUS_LABELS[s] ?? s; }
  treatmentLabel(o: string): string { return TREATMENT_LABELS[o] ?? o; }
}
