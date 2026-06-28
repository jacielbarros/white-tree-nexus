import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { hasPermission } from '@app/core/permissions';
import { RiskMethodology } from '@app/core/models';
import { LEVEL_LABELS, levelColor } from '@app/pages/risks/risk-labels';

@Component({
  selector: 'app-risk-methodology',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, ButtonModule],
  template: `
    <header class="wtn-page-header">
      <div>
        <h1 class="wtn-page-title">Metodologia de Risco</h1>
        <p class="wtn-page-desc">Escalas, matriz e critério de aceitação (6.1.2 a). Padrão 5×5 quando não configurada.</p>
      </div>
      @if (canManage() && m()) {
        <div class="wtn-page-actions"><p-button label="Salvar" icon="pi pi-check" (onClick)="save()" [disabled]="busy()" /></div>
      }
    </header>

    @if (m(); as meth) {
      @if (!meth.is_configured) {
        <div class="notice">Usando a metodologia padrão 5×5. Ajuste e salve para personalizar.</div>
      }

      <section class="wtn-card pad">
        <div class="wtn-card-title">Matriz Probabilidade × Impacto → Nível</div>
        <div class="matrix">
          <div class="mx-corner"></div>
          @for (i of axis; track i) { <div class="mx-axis">I{{ i }}</div> }
          @for (p of axisRev; track p) {
            <div class="mx-axis">P{{ p }}</div>
            @for (i of axis; track i) {
              <div class="mx-cell" [style.background]="cellColor(meth, p, i)">
                @if (canManage()) {
                  <select [ngModel]="meth.risk_matrix[p + 'x' + i]" (ngModelChange)="setCell(meth, p, i, $event)">
                    @for (lv of meth.risk_levels; track lv.key) { <option [value]="lv.key">{{ lv.label }}</option> }
                  </select>
                } @else { {{ levelName(meth.risk_matrix[p + 'x' + i]) }} }
              </div>
            }
          }
        </div>
      </section>

      <section class="wtn-card pad">
        <div class="wtn-card-title">Critério de aceitação por nível</div>
        @for (lv of meth.risk_levels; track lv.key) {
          <label class="accept-row">
            <span class="lv-chip" [style.background]="levelBg(lv.key)">{{ lv.label }}</span>
            <input type="checkbox" [ngModel]="meth.acceptance[lv.key]" (ngModelChange)="setAcceptance(meth, lv.key, $event)" [disabled]="!canManage()" />
            <span class="muted">{{ meth.acceptance[lv.key] ? 'Aceito automaticamente' : 'Acima do critério' }}</span>
          </label>
        }
      </section>

      <section class="wtn-card pad">
        <div class="wtn-card-title">Mapeamento CIA → Impacto</div>
        <div class="cia-grid">
          @for (k of ciaKeys; track k) {
            <label class="cia-row"><span>{{ ciaLabel(k) }}</span>
              <select [ngModel]="meth.cia_impact_map[k]" (ngModelChange)="setCia(meth, k, $event)" [disabled]="!canManage()">
                @for (n of axis; track n) { <option [ngValue]="n">{{ n }}</option> }</select>
            </label>
          }
        </div>
      </section>
    } @else {
      <div class="wtn-card pad"><div class="wtn-skeleton skeleton-line"></div></div>
    }
  `,
  styles: [`
    :host { display: block; }
    .notice { background: var(--wtn-primary-soft); color: var(--wtn-primary); padding: 10px 14px; border-radius: var(--wtn-r-md); font-size: 13px; margin-bottom: 16px; }
    .wtn-card { background: var(--wtn-card); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-lg); margin-bottom: 16px; }
    .pad { padding: 18px 20px; }
    .wtn-card-title { color: var(--wtn-muted); font-size: 11px; font-weight: 600; letter-spacing: .05em; text-transform: uppercase; margin-bottom: 14px; }
    .matrix { display: grid; grid-template-columns: 32px repeat(5, 1fr); gap: 4px; max-width: 560px; }
    .mx-axis { font-size: 11px; color: var(--wtn-muted); display: flex; align-items: center; justify-content: center; }
    .mx-cell { aspect-ratio: 2.4; border-radius: 6px; display: flex; align-items: center; justify-content: center; }
    .mx-cell select { background: rgba(0,0,0,.15); border: none; color: #fff; font-size: 11px; font-weight: 600; border-radius: 4px; padding: 2px; }
    .accept-row { display: flex; align-items: center; gap: 12px; padding: 7px 0; font-size: 13px; }
    .lv-chip { color: #fff; padding: 2px 10px; border-radius: var(--wtn-r-pill); font-size: 12px; font-weight: 600; min-width: 60px; text-align: center; }
    .cia-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 12px; }
    .cia-row { display: flex; flex-direction: column; gap: 5px; font-size: 12px; color: var(--wtn-muted); }
    .cia-row select { background: var(--wtn-surface); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); padding: 7px; color: var(--wtn-text); }
    .muted { color: var(--wtn-muted); font-size: 12px; } .skeleton-line { height: 18px; }
  `],
})
export class RiskMethodologyPage implements OnInit {
  private api = inject(ApiService);
  private store = inject(AuthStore);

  readonly axis = [1, 2, 3, 4, 5];
  readonly axisRev = [5, 4, 3, 2, 1];
  readonly ciaKeys = ['baixa', 'media', 'alta', 'critica'];
  readonly m = signal<RiskMethodology | null>(null);
  readonly busy = signal(false);

  ngOnInit(): void {
    this.api.get<RiskMethodology>('/risk/methodology').subscribe((meth) => this.m.set(meth));
  }

  canManage(): boolean { return hasPermission(this.store.currentRole(), 'manage_risk'); }

  setCell(meth: RiskMethodology, p: number, i: number, key: string): void {
    meth.risk_matrix = { ...meth.risk_matrix, [`${p}x${i}`]: key };
    this.m.set({ ...meth });
  }
  setAcceptance(meth: RiskMethodology, key: string, val: boolean): void {
    meth.acceptance = { ...meth.acceptance, [key]: val };
    this.m.set({ ...meth });
  }
  setCia(meth: RiskMethodology, key: string, val: number): void {
    meth.cia_impact_map = { ...meth.cia_impact_map, [key]: val };
    this.m.set({ ...meth });
  }

  save(): void {
    const meth = this.m();
    if (!meth) return;
    this.busy.set(true);
    const { probability_scale, impact_scale, risk_levels, risk_matrix, acceptance, cia_impact_map } = meth;
    this.api.put<RiskMethodology>('/risk/methodology', {
      probability_scale, impact_scale, risk_levels, risk_matrix, acceptance, cia_impact_map,
    }).subscribe({
      next: (saved) => { this.busy.set(false); this.m.set(saved); },
      error: () => this.busy.set(false),
    });
  }

  cellColor(meth: RiskMethodology, p: number, i: number): string { return levelColor(meth.risk_matrix[`${p}x${i}`]); }
  levelBg(k: string): string { return levelColor(k); }
  levelName(k: string): string { return LEVEL_LABELS[k] ?? k; }
  ciaLabel(k: string): string { return ({ baixa: 'Baixa', media: 'Média', alta: 'Alta', critica: 'Crítica' } as Record<string, string>)[k] ?? k; }
}
