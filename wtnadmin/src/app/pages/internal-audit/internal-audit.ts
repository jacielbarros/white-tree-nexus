import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { hasPermission } from '@app/core/permissions';
import { AuditProgram, AuditSummary, InternalAuditStatus, MembershipRow } from '@app/core/models';
import { AUDIT_STATUS_LABELS } from './internal-audit-labels';

/** Auditoria Interna (Feature 014): programas + auditorias (lista e criação). */
@Component({
  selector: 'app-internal-audit',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, RouterLink, ButtonModule],
  template: `
    <header class="wtn-page-header">
      <div>
        <h1 class="wtn-page-title">Auditoria Interna</h1>
        <p class="wtn-page-desc">Programa de auditoria, auditorias e condução (cláusula 9.2).</p>
      </div>
      <p-button icon="pi pi-refresh" label="Atualizar" severity="secondary" (onClick)="load()" [loading]="loading()" />
    </header>

    <div class="grid">
      <section class="wtn-card pad">
        <div class="wtn-card-title">Programas</div>
        @if (canManage()) {
          <form class="inline-form" (submit)="createProgram($event)">
            <input type="text" [(ngModel)]="newProgramName" name="pn" placeholder="Nome do programa" />
            <input type="text" [(ngModel)]="newProgramObjective" name="po" placeholder="Objetivo (opcional)" />
            <button type="submit" class="btn-primary" [disabled]="!newProgramName.trim()">Criar</button>
          </form>
        }
        @for (p of programs(); track p.id) {
          <div class="prog-row"><strong>{{ p.name }}</strong>@if (p.objective) { <span> · {{ p.objective }}</span> }</div>
        } @empty { <p class="muted">Nenhum programa.</p> }
      </section>

      @if (canManage() && programs().length) {
        <section class="wtn-card pad">
          <div class="wtn-card-title">Nova auditoria</div>
          <form class="stack-form" (submit)="createAudit($event)">
            <select [(ngModel)]="newProgramId" name="prog">
              <option value="">Programa…</option>
              @for (p of programs(); track p.id) { <option [value]="p.id">{{ p.name }}</option> }
            </select>
            <input type="text" [(ngModel)]="newTitle" name="t" placeholder="Título da auditoria" />
            <select [(ngModel)]="newAuditor" name="aud">
              <option value="">Auditor interno…</option>
              @for (m of members(); track m.user_id) { <option [value]="m.user_id">{{ m.full_name || m.email }}</option> }
            </select>
            <textarea [(ngModel)]="newScope" name="sc" rows="2" placeholder="Escopo"></textarea>
            <textarea [(ngModel)]="newCriteria" name="cr" rows="2" placeholder="Critérios (ex.: ISO 27001, políticas)"></textarea>
            <button type="submit" class="btn-primary" [disabled]="!canCreateAudit()">Criar auditoria</button>
          </form>
        </section>
      }
    </div>

    <section class="wtn-card pad">
      <div class="wtn-card-title">Auditorias</div>
      @if (loading()) {
        <p class="muted">Carregando…</p>
      } @else if (!audits().length) {
        <div class="wtn-empty"><div class="wtn-empty-title">Nenhuma auditoria ainda</div></div>
      } @else {
        <div class="aud-list">
          @for (a of audits(); track a.id) {
            <a class="aud-row" [routerLink]="['../internal-audit-detail', a.id]">
              <span class="code">{{ a.code }}</span>
              <span class="title">{{ a.title }}</span>
              <span class="status status--{{ a.status }}">{{ statusLabel(a.status) }}</span>
              @if (a.current_version_id) { <span class="badge">Relatório aprovado</span> }
            </a>
          }
        </div>
      }
    </section>
  `,
  styles: `
    :host { display: block; }
    .grid { display: grid; gap: 12px; grid-template-columns: 1fr 1fr; margin-bottom: 12px; }
    @media (max-width: 880px) { .grid { grid-template-columns: 1fr; } }
    .inline-form { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
    .stack-form { display: grid; gap: 8px; }
    .inline-form input, .stack-form input, .stack-form select, .stack-form textarea {
      background: var(--wtn-surface); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md);
      color: var(--wtn-text); padding: 7px 10px; font: inherit;
    }
    .btn-primary { background: var(--wtn-primary); border: none; border-radius: var(--wtn-r-md); color: #fff; cursor: pointer; padding: 7px 16px; justify-self: start; }
    .btn-primary:disabled { opacity: .5; cursor: not-allowed; }
    .muted { color: var(--wtn-text-2); }
    .prog-row { border-top: 1px solid var(--wtn-border); color: var(--wtn-text); font-size: 12.5px; padding: 6px 0; }
    .prog-row span { color: var(--wtn-text-2); }
    .aud-list { display: grid; gap: 6px; }
    .aud-row { align-items: center; border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); color: var(--wtn-text); display: flex; gap: 10px; padding: 9px 12px; text-decoration: none; }
    .aud-row:hover { border-color: var(--wtn-primary); }
    .aud-row .code { color: var(--wtn-muted); font-weight: 700; font-size: 12px; }
    .aud-row .title { flex: 1; font-size: 13px; }
    .status { border-radius: 999px; font-size: 10.5px; padding: 2px 9px; border: 1px solid var(--wtn-border); color: var(--wtn-text-2); }
    .status--in_progress { border-color: var(--wtn-primary); color: var(--wtn-primary); }
    .status--completed { border-color: #2e9e5b; color: #2e9e5b; }
    .status--cancelled { color: var(--wtn-muted); }
    .badge { background: var(--wtn-primary); border-radius: 999px; color: #fff; font-size: 10px; padding: 2px 8px; }
  `,
})
export class InternalAuditPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly store = inject(AuthStore);
  private readonly messages = inject(MessageService);

  protected readonly loading = signal(false);
  protected readonly programs = signal<AuditProgram[]>([]);
  protected readonly audits = signal<AuditSummary[]>([]);
  protected readonly members = signal<MembershipRow[]>([]);

  protected newProgramName = '';
  protected newProgramObjective = '';
  protected newProgramId = '';
  protected newTitle = '';
  protected newAuditor = '';
  protected newScope = '';
  protected newCriteria = '';

  protected readonly canManage = computed(() => hasPermission(this.store.currentRole(), 'manage_internal_audit'));

  ngOnInit(): void {
    this.load();
    if (this.canManage()) {
      this.api.listUsers().subscribe({ next: (rows) => this.members.set(rows.filter((m) => m.status === 'active')) });
    }
  }

  protected load(): void {
    this.loading.set(true);
    this.api.get<AuditProgram[]>('/internal-audit/programs').subscribe({ next: (p) => this.programs.set(p) });
    this.api.get<AuditSummary[]>('/internal-audit/audits').subscribe({
      next: (a) => {
        this.audits.set(a);
        this.loading.set(false);
      },
      error: (e) => {
        this.messages.add({ severity: 'error', summary: 'Erro ao carregar', detail: this.errorDetail(e) });
        this.loading.set(false);
      },
    });
  }

  protected canCreateAudit(): boolean {
    return !!(this.newProgramId && this.newTitle.trim() && this.newAuditor && this.newScope.trim() && this.newCriteria.trim());
  }

  protected createProgram(event: Event): void {
    event.preventDefault();
    if (!this.newProgramName.trim()) return;
    this.api.post<AuditProgram>('/internal-audit/programs', { name: this.newProgramName.trim(), objective: this.newProgramObjective.trim() || null }).subscribe({
      next: () => {
        this.messages.add({ severity: 'success', summary: 'Programa criado' });
        this.newProgramName = '';
        this.newProgramObjective = '';
        this.load();
      },
      error: (e) => this.messages.add({ severity: 'error', summary: 'Erro', detail: this.errorDetail(e) }),
    });
  }

  protected createAudit(event: Event): void {
    event.preventDefault();
    if (!this.canCreateAudit()) return;
    this.api.post<AuditSummary>('/internal-audit/audits', {
      program_id: this.newProgramId,
      title: this.newTitle.trim(),
      scope: this.newScope.trim(),
      criteria: this.newCriteria.trim(),
      auditor_member_id: this.newAuditor,
    }).subscribe({
      next: () => {
        this.messages.add({ severity: 'success', summary: 'Auditoria criada' });
        this.newTitle = '';
        this.newScope = '';
        this.newCriteria = '';
        this.newAuditor = '';
        this.load();
      },
      error: (e) => this.messages.add({ severity: 'error', summary: 'Erro', detail: this.errorDetail(e) }),
    });
  }

  protected statusLabel(s: InternalAuditStatus): string {
    return AUDIT_STATUS_LABELS[s];
  }

  private errorDetail(error: unknown): string {
    if (typeof error === 'object' && error && 'error' in error) {
      const payload = (error as { error?: { detail?: string } }).error;
      if (payload?.detail) return payload.detail;
    }
    return 'Operação não concluída.';
  }
}
