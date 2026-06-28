import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ReactiveFormsModule, NonNullableFormBuilder, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ButtonModule } from 'primeng/button';

import { ApiService } from '@app/core/api.service';
import { hasPermission } from '@app/core/permissions';
import { AuthStore } from '@app/core/auth.store';
import { HeatmapCell, Risk, Threat, Vulnerability } from '@app/core/models';
import { LEVEL_LABELS, RISK_STATUS_LABELS, levelColor, levelLabel } from '@app/pages/risks/risk-labels';

interface AssetLite { id: string; code: string; name: string; }

@Component({
  selector: 'app-risks',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, FormsModule, ReactiveFormsModule, ButtonModule],
  template: `
    <header class="wtn-page-header">
      <div>
        <h1 class="wtn-page-title">Riscos · Avaliação (6.1.2)</h1>
        <p class="wtn-page-desc">Registro de riscos do SGSI — cenário, probabilidade, impacto e nível.</p>
      </div>
      <div class="wtn-page-actions">
        <a routerLink="../risk-dashboard"><p-button label="Dashboard" icon="pi pi-chart-bar" severity="secondary" /></a>
        @if (canManage()) {
          <p-button label="Novo risco" icon="pi pi-plus" (onClick)="showForm.set(!showForm())" />
        }
      </div>
    </header>

    <!-- Heat map 5x5 -->
    <section class="wtn-card pad heatmap-card">
      <div class="wtn-card-title">Heat map · Probabilidade × Impacto</div>
      <div class="heatmap">
        <div class="hm-corner"></div>
        @for (i of axis; track i) { <div class="hm-axis hm-top">I{{ i }}</div> }
        @for (p of axisRev; track p) {
          <div class="hm-axis hm-left">P{{ p }}</div>
          @for (i of axis; track i) {
            <div class="hm-cell" [style.background]="cellColor(p, i)" [title]="'P'+p+' × I'+i">
              {{ cellCount(p, i) || '' }}
            </div>
          }
        }
      </div>
    </section>

    <!-- Filtros -->
    <section class="filters">
      <input class="wtn-input" placeholder="Buscar título/descrição…" [ngModel]="search()" (ngModelChange)="search.set($event)" />
      <select class="wtn-input" [ngModel]="statusFilter()" (ngModelChange)="statusFilter.set($event)">
        <option value="">Todos os status</option>
        @for (s of statusKeys; track s) { <option [value]="s">{{ statusLabel(s) }}</option> }
      </select>
      <select class="wtn-input" [ngModel]="levelFilter()" (ngModelChange)="levelFilter.set($event)">
        <option value="">Todos os níveis</option>
        @for (l of levelKeys; track l) { <option [value]="l">{{ levelName(l) }}</option> }
      </select>
      <label class="chk"><input type="checkbox" [ngModel]="onlyAbove()" (ngModelChange)="onlyAbove.set($event)" /> Acima do critério</label>
    </section>

    <!-- Form de criação -->
    @if (showForm() && canManage()) {
      <section class="wtn-card pad form-card">
        <div class="wtn-card-title">Novo cenário de risco</div>
        <form [formGroup]="form" (ngSubmit)="create()">
          <div class="grid2">
            <label class="fld"><span>Título *</span><input class="wtn-input" formControlName="title" /></label>
            <label class="fld"><span>Ameaça *</span>
              <select class="wtn-input" formControlName="threat_id">
                <option value="">Selecione…</option>
                @for (t of threats(); track t.id) { <option [value]="t.id">{{ t.code }} · {{ t.name }}</option> }
              </select>
            </label>
            <label class="fld"><span>Vulnerabilidade *</span>
              <select class="wtn-input" formControlName="vulnerability_id">
                <option value="">Selecione…</option>
                @for (v of vulns(); track v.id) { <option [value]="v.id">{{ v.code }} · {{ v.name }}</option> }
              </select>
            </label>
            <label class="fld"><span>Ativos (opcional)</span>
              <select class="wtn-input" multiple [ngModelOptions]="{standalone: true}" [(ngModel)]="selectedAssets">
                @for (a of assets(); track a.id) { <option [value]="a.id">{{ a.code }} · {{ a.name }}</option> }
              </select>
            </label>
          </div>
          <label class="fld"><span>Descrição *</span><textarea class="wtn-input" rows="2" formControlName="description"></textarea></label>
          @if (error()) { <p class="err">{{ error() }}</p> }
          <div class="form-actions">
            <p-button type="submit" label="Criar" icon="pi pi-check" [disabled]="form.invalid || saving()" />
            <p-button type="button" label="Cancelar" severity="secondary" (onClick)="showForm.set(false)" />
          </div>
        </form>
      </section>
    }

    <!-- Lista -->
    @if (loading()) {
      <div class="wtn-card pad"><div class="wtn-skeleton skeleton-line"></div></div>
    } @else if (filtered().length) {
      <table class="wtn-table">
        <thead><tr><th>Código</th><th>Título</th><th>Nível</th><th>Status</th><th>Critério</th><th></th></tr></thead>
        <tbody>
          @for (r of filtered(); track r.id) {
            <tr>
              <td class="mono">{{ r.code }}</td>
              <td>{{ r.title }}</td>
              <td>
                <span class="level-chip" [style.background]="levelBg(r.inherent_level_key)">{{ level(r.inherent_level_key) }}</span>
              </td>
              <td>{{ statusLabel(r.status) }}</td>
              <td>
                @if (r.above_acceptance === true) { <span class="badge badge--danger">Acima</span> }
                @else if (r.above_acceptance === false) { <span class="badge badge--ok">Atende</span> }
                @else { <span class="muted">—</span> }
              </td>
              <td><a [routerLink]="['../risk-detail', r.id]"><p-button label="Abrir" size="small" severity="secondary" text="true" /></a></td>
            </tr>
          }
        </tbody>
      </table>
    } @else {
      <div class="wtn-empty"><div class="wtn-empty-title">Nenhum risco</div>
        <div class="wtn-empty-desc">Crie um cenário de risco (ameaça + vulnerabilidade + ativos) para começar.</div></div>
    }
  `,
  styles: [`
    :host { display: block; }
    .wtn-card { background: var(--wtn-card); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-lg); }
    .pad { padding: 18px 20px; }
    .wtn-card-title { color: var(--wtn-muted); font-size: 11px; font-weight: 600; letter-spacing: .05em; text-transform: uppercase; margin-bottom: 14px; }
    .heatmap-card { margin-bottom: 18px; }
    .heatmap { display: grid; grid-template-columns: 28px repeat(5, 1fr); gap: 4px; max-width: 460px; }
    .hm-corner { }
    .hm-axis { font-size: 11px; color: var(--wtn-muted); display: flex; align-items: center; justify-content: center; }
    .hm-cell { aspect-ratio: 1.8; border-radius: 6px; display: flex; align-items: center; justify-content: center; color: #fff; font-weight: 700; font-size: 13px; }
    .filters { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 16px; align-items: center; }
    .wtn-input { background: var(--wtn-surface); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); padding: 8px 10px; font-size: 13px; color: var(--wtn-text); }
    .chk { font-size: 13px; color: var(--wtn-text-2); display: flex; gap: 6px; align-items: center; }
    .form-card { margin-bottom: 18px; }
    .grid2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; margin-bottom: 12px; }
    .fld { display: flex; flex-direction: column; gap: 5px; font-size: 12px; color: var(--wtn-muted); margin-bottom: 12px; }
    .fld span { font-weight: 600; }
    .fld .wtn-input { width: 100%; box-sizing: border-box; }
    .form-actions { display: flex; gap: 10px; }
    .err { color: var(--wtn-danger); font-size: 13px; }
    .wtn-table { width: 100%; border-collapse: collapse; background: var(--wtn-card); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-lg); overflow: hidden; }
    .wtn-table th { text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: var(--wtn-muted); padding: 11px 14px; border-bottom: 1px solid var(--wtn-border); }
    .wtn-table td { padding: 11px 14px; border-bottom: 1px solid var(--wtn-border); font-size: 13px; color: var(--wtn-text); }
    .mono { font-family: var(--wtn-font-mono, monospace); color: var(--wtn-text-2); }
    .level-chip { color: #fff; padding: 2px 9px; border-radius: var(--wtn-r-pill); font-size: 12px; font-weight: 600; }
    .badge { padding: 2px 8px; border-radius: var(--wtn-r-pill); font-size: 11px; font-weight: 600; }
    .badge--danger { background: #fdecea; color: #c62828; } .badge--ok { background: #e8f5e9; color: #2e7d32; }
    .muted { color: var(--wtn-muted); } .skeleton-line { height: 18px; }
  `],
})
export class RisksPage implements OnInit {
  private api = inject(ApiService);
  private store = inject(AuthStore);
  private fb = inject(NonNullableFormBuilder);

  readonly axis = [1, 2, 3, 4, 5];
  readonly axisRev = [5, 4, 3, 2, 1];
  readonly statusKeys = Object.keys(RISK_STATUS_LABELS);
  readonly levelKeys = Object.keys(LEVEL_LABELS);

  readonly risks = signal<Risk[]>([]);
  readonly threats = signal<Threat[]>([]);
  readonly vulns = signal<Vulnerability[]>([]);
  readonly assets = signal<AssetLite[]>([]);
  readonly heatmap = signal<HeatmapCell[]>([]);
  readonly loading = signal(true);
  readonly showForm = signal(false);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);

  readonly search = signal('');
  readonly statusFilter = signal('');
  readonly levelFilter = signal('');
  readonly onlyAbove = signal(false);
  selectedAssets: string[] = [];

  readonly form = this.fb.group({
    title: ['', Validators.required],
    description: ['', Validators.required],
    threat_id: ['', Validators.required],
    vulnerability_id: ['', Validators.required],
  });

  readonly filtered = computed(() => {
    const q = this.search().toLowerCase();
    return this.risks().filter((r) =>
      (!q || r.title.toLowerCase().includes(q) || r.description.toLowerCase().includes(q)) &&
      (!this.statusFilter() || r.status === this.statusFilter()) &&
      (!this.levelFilter() || r.inherent_level_key === this.levelFilter()) &&
      (!this.onlyAbove() || r.above_acceptance === true),
    );
  });

  ngOnInit(): void {
    this.reload();
    this.api.get<Threat[]>('/risk/threats').subscribe((t) => this.threats.set(t));
    this.api.get<Vulnerability[]>('/risk/vulnerabilities').subscribe((v) => this.vulns.set(v));
    this.api.get<AssetLite[]>('/assets').subscribe({ next: (a) => this.assets.set(a), error: () => {} });
  }

  reload(): void {
    this.loading.set(true);
    this.api.get<Risk[]>('/risk/risks').subscribe({
      next: (r) => { this.risks.set(r); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
    this.api.get<HeatmapCell[]>('/risk/matrix').subscribe((h) => this.heatmap.set(h));
  }

  canManage(): boolean { return hasPermission(this.store.currentRole(), 'manage_risk'); }

  create(): void {
    if (this.form.invalid) return;
    this.saving.set(true);
    this.error.set(null);
    this.api.post<Risk>('/risk/risks', { ...this.form.getRawValue(), asset_item_ids: this.selectedAssets }).subscribe({
      next: () => { this.saving.set(false); this.showForm.set(false); this.form.reset(); this.selectedAssets = []; this.reload(); },
      error: (e) => { this.saving.set(false); this.error.set(e?.error?.detail ?? 'Falha ao criar o risco.'); },
    });
  }

  cellCount(p: number, i: number): number {
    return this.heatmap().find((c) => c.probability === p && c.impact === i)?.count ?? 0;
  }
  cellColor(p: number, i: number): string {
    return levelColor(this.heatmap().find((c) => c.probability === p && c.impact === i)?.level_key);
  }
  level(k: string | null): string { return levelLabel(k); }
  levelBg(k: string | null): string { return levelColor(k); }
  levelName(k: string): string { return LEVEL_LABELS[k] ?? k; }
  statusLabel(s: string): string { return RISK_STATUS_LABELS[s] ?? s; }
}
