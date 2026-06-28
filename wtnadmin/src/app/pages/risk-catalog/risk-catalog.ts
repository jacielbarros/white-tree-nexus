import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { hasPermission } from '@app/core/permissions';
import { Threat, Vulnerability } from '@app/core/models';
import { THREAT_CATEGORY_LABELS, VULN_CATEGORY_LABELS } from '@app/pages/risks/risk-labels';

@Component({
  selector: 'app-risk-catalog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, ButtonModule],
  template: `
    <header class="wtn-page-header">
      <div>
        <h1 class="wtn-page-title">Ameaças e Vulnerabilidades · Fase 1</h1>
        <p class="wtn-page-desc">Catálogo da organização (base ISO 27005) — adote, personalize e arquive.</p>
      </div>
      @if (canManage()) {
        <div class="wtn-page-actions">
          <p-button label="Adotar catálogo" icon="pi pi-download" severity="secondary" (onClick)="adopt()" [disabled]="busy()" />
        </div>
      }
    </header>

    <div class="tabs">
      <button class="tab" [class.active]="tab() === 'threats'" (click)="tab.set('threats')">Ameaças ({{ threats().length }})</button>
      <button class="tab" [class.active]="tab() === 'vulns'" (click)="tab.set('vulns')">Vulnerabilidades ({{ vulns().length }})</button>
    </div>

    @if (canManage()) {
      <section class="wtn-card pad form-card">
        @if (tab() === 'threats') {
          <div class="add-row">
            <input class="wtn-input grow" placeholder="Nova ameaça…" [(ngModel)]="tName" />
            <select class="wtn-input" [(ngModel)]="tCat">
              @for (c of threatCats; track c) { <option [value]="c">{{ threatCatLabel(c) }}</option> }</select>
            <p-button label="Adicionar" icon="pi pi-plus" size="small" (onClick)="createThreat()" [disabled]="!tName || busy()" />
          </div>
        } @else {
          <div class="add-row">
            <input class="wtn-input grow" placeholder="Nova vulnerabilidade…" [(ngModel)]="vName" />
            <select class="wtn-input" [(ngModel)]="vCat">
              @for (c of vulnCats; track c) { <option [value]="c">{{ vulnCatLabel(c) }}</option> }</select>
            <p-button label="Adicionar" icon="pi pi-plus" size="small" (onClick)="createVuln()" [disabled]="!vName || busy()" />
          </div>
        }
      </section>
    }

    @if (tab() === 'threats') {
      <table class="wtn-table">
        <thead><tr><th>Código</th><th>Nome</th><th>Categoria</th><th>Origem</th><th></th></tr></thead>
        <tbody>
          @for (t of threats(); track t.id) {
            <tr><td class="mono">{{ t.code }}</td><td>{{ t.name }}</td><td>{{ threatCatLabel(t.category) }}</td>
              <td>{{ t.origin ?? '—' }}</td>
              <td>@if (canManage()) { <p-button icon="pi pi-archive" size="small" text="true" severity="secondary" (onClick)="archiveThreat(t)" /> }</td></tr>
          } @empty { <tr><td colspan="5" class="muted">Adote o catálogo para começar.</td></tr> }
        </tbody>
      </table>
    } @else {
      <table class="wtn-table">
        <thead><tr><th>Código</th><th>Nome</th><th>Categoria</th><th></th></tr></thead>
        <tbody>
          @for (v of vulns(); track v.id) {
            <tr><td class="mono">{{ v.code }}</td><td>{{ v.name }}</td><td>{{ vulnCatLabel(v.category) }}</td>
              <td>@if (canManage()) { <p-button icon="pi pi-archive" size="small" text="true" severity="secondary" (onClick)="archiveVuln(v)" /> }</td></tr>
          } @empty { <tr><td colspan="4" class="muted">Adote o catálogo para começar.</td></tr> }
        </tbody>
      </table>
    }
  `,
  styles: [`
    :host { display: block; }
    .tabs { display: flex; gap: 6px; margin-bottom: 16px; }
    .tab { background: var(--wtn-surface); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); padding: 8px 14px; font-size: 13px; cursor: pointer; color: var(--wtn-text-2); }
    .tab.active { background: var(--wtn-primary-soft); color: var(--wtn-primary); font-weight: 600; }
    .wtn-card { background: var(--wtn-card); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-lg); }
    .pad { padding: 16px 18px; } .form-card { margin-bottom: 16px; }
    .add-row { display: flex; gap: 10px; align-items: center; }
    .wtn-input { background: var(--wtn-surface); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); padding: 8px 10px; font-size: 13px; color: var(--wtn-text); }
    .grow { flex: 1; }
    .wtn-table { width: 100%; border-collapse: collapse; background: var(--wtn-card); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-lg); overflow: hidden; }
    .wtn-table th { text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: var(--wtn-muted); padding: 11px 14px; border-bottom: 1px solid var(--wtn-border); }
    .wtn-table td { padding: 10px 14px; border-bottom: 1px solid var(--wtn-border); font-size: 13px; color: var(--wtn-text); }
    .mono { font-family: var(--wtn-font-mono, monospace); color: var(--wtn-text-2); } .muted { color: var(--wtn-muted); }
  `],
})
export class RiskCatalogPage implements OnInit {
  private api = inject(ApiService);
  private store = inject(AuthStore);

  readonly threatCats = Object.keys(THREAT_CATEGORY_LABELS);
  readonly vulnCats = Object.keys(VULN_CATEGORY_LABELS);
  readonly tab = signal<'threats' | 'vulns'>('threats');
  readonly threats = signal<Threat[]>([]);
  readonly vulns = signal<Vulnerability[]>([]);
  readonly busy = signal(false);

  tName = ''; tCat = 'technical';
  vName = ''; vCat = 'technical';

  ngOnInit(): void { this.reload(); }

  reload(): void {
    this.api.get<Threat[]>('/risk/threats').subscribe((t) => this.threats.set(t));
    this.api.get<Vulnerability[]>('/risk/vulnerabilities').subscribe((v) => this.vulns.set(v));
  }

  canManage(): boolean { return hasPermission(this.store.currentRole(), 'manage_risk'); }

  adopt(): void {
    this.busy.set(true);
    this.api.post('/risk/threats/adopt', {}).subscribe({
      next: () => this.api.post('/risk/vulnerabilities/adopt', {}).subscribe({
        next: () => { this.busy.set(false); this.reload(); }, error: () => this.busy.set(false),
      }),
      error: () => this.busy.set(false),
    });
  }

  createThreat(): void {
    this.busy.set(true);
    this.api.post('/risk/threats', { name: this.tName, category: this.tCat }).subscribe({
      next: () => { this.busy.set(false); this.tName = ''; this.reload(); }, error: () => this.busy.set(false),
    });
  }

  createVuln(): void {
    this.busy.set(true);
    this.api.post('/risk/vulnerabilities', { name: this.vName, category: this.vCat }).subscribe({
      next: () => { this.busy.set(false); this.vName = ''; this.reload(); }, error: () => this.busy.set(false),
    });
  }

  archiveThreat(t: Threat): void {
    const reason = prompt(`Justificativa para arquivar "${t.name}":`);
    if (!reason) return;
    this.api.post(`/risk/threats/${t.id}/archive`, { reason }).subscribe({ next: () => this.reload() });
  }

  archiveVuln(v: Vulnerability): void {
    const reason = prompt(`Justificativa para arquivar "${v.name}":`);
    if (!reason) return;
    this.api.post(`/risk/vulnerabilities/${v.id}/archive`, { reason }).subscribe({ next: () => this.reload() });
  }

  threatCatLabel(c: string): string { return THREAT_CATEGORY_LABELS[c] ?? c; }
  vulnCatLabel(c: string): string { return VULN_CATEGORY_LABELS[c] ?? c; }
}
