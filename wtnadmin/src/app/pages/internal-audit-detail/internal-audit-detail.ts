import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { hasPermission } from '@app/core/permissions';
import { EvidencePanel } from '@app/shared/evidence-panel/evidence-panel';
import {
  AuditChecklistItem,
  AuditChecklistResult,
  AuditDetail,
  AuditFinding,
  AuditFindingType,
  AuditReportVersion,
} from '@app/core/models';
import { AUDIT_STATUS_LABELS, CHECKLIST_RESULT_LABELS, FINDING_TYPE_LABELS } from '@app/pages/internal-audit/internal-audit-labels';

/** Condução de uma auditoria interna: checklist, constatações e relatório (Documento Controlado). */
@Component({
  selector: 'app-internal-audit-detail',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, RouterLink, ButtonModule, EvidencePanel],
  template: `
    <a routerLink="../internal-audit" class="back">← Auditoria Interna</a>
    @if (audit(); as a) {
      <header class="wtn-page-header">
        <div>
          <h1 class="wtn-page-title">{{ a.title }} <span class="code">{{ a.code }}</span></h1>
          <p class="wtn-page-desc">{{ statusLabel(a.status) }} · {{ a.readiness.findings_count }} constatação(ões) · {{ a.readiness.pending_items }} item(ns) pendente(s)</p>
        </div>
        @if (canManage()) {
          <div class="actions">
            @if (a.status === 'planned') { <p-button label="Iniciar" (onClick)="transition('start')" [loading]="busy()" /> }
            @if (a.status === 'in_progress') { <p-button label="Concluir" (onClick)="transition('complete')" [loading]="busy()" /> }
            @if (a.status === 'planned' || a.status === 'in_progress') { <p-button label="Cancelar" severity="secondary" (onClick)="transition('cancel')" [loading]="busy()" /> }
          </div>
        }
      </header>

      <section class="wtn-card pad">
        <div class="wtn-card-title">Escopo & critérios</div>
        <p class="block"><b>Escopo:</b> {{ a.scope }}</p>
        <p class="block"><b>Critérios:</b> {{ a.criteria }}</p>
      </section>

      <!-- Checklist -->
      <section class="wtn-card pad">
        <div class="wtn-card-title">Itens auditados</div>
        @if (canManage()) {
          <form class="inline-form" (submit)="addChecklist($event)">
            <input type="text" [(ngModel)]="newCriterion" name="c" placeholder="Critério / pergunta" />
            <button type="submit" class="btn-primary" [disabled]="!newCriterion.trim()">Adicionar</button>
            <button type="button" class="btn-secondary" (click)="importChecklist('soa')">Importar SoA</button>
            <button type="button" class="btn-secondary" (click)="importChecklist('gap')">Importar Gap</button>
          </form>
        }
        @for (it of checklist(); track it.id) {
          <div class="ck-row">
            <span class="ck-crit">{{ it.criterion }}</span>
            @if (canManage()) {
              <select [ngModel]="it.result" (ngModelChange)="updateResult(it, $event)" name="r-{{ it.id }}">
                <option value="pendente">Pendente</option>
                <option value="conforme">Conforme</option>
                <option value="nao_conforme">Não conforme</option>
                <option value="nao_aplicavel">Não aplicável</option>
              </select>
            } @else {
              <span class="ck-result">{{ resultLabel(it.result) }}</span>
            }
          </div>
        } @empty { <p class="muted">Nenhum item de checklist.</p> }
      </section>

      <!-- Constatações -->
      <section class="wtn-card pad">
        <div class="wtn-card-title">Constatações</div>
        @if (canManage()) {
          <form class="stack-form" (submit)="addFinding($event)">
            <div class="row-2">
              <select [(ngModel)]="newType" name="ft">
                <option value="conforme">Conforme</option>
                <option value="nc_maior">NC maior</option>
                <option value="nc_menor">NC menor</option>
                <option value="oportunidade_melhoria">Oportunidade de melhoria</option>
                <option value="observacao">Observação</option>
              </select>
              <input type="text" [(ngModel)]="newFindingTitle" name="ftt" placeholder="Título" />
            </div>
            <textarea [(ngModel)]="newFindingDesc" name="fd" rows="2" placeholder="Descrição do achado"></textarea>
            <button type="submit" class="btn-primary" [disabled]="!newFindingTitle.trim() || !newFindingDesc.trim()">Registrar constatação</button>
          </form>
        }
        @for (f of findings(); track f.id) {
          <div class="fd">
            <div class="fd-head">
              <span class="fd-type fd-type--{{ f.finding_type }}">{{ findingLabel(f.finding_type) }}</span>
              <strong>{{ f.title }}</strong>
              @if (f.promotable) { <span class="fd-promo" title="Promovível a NC formal (Feature 5b)">promovível</span> }
              @if (canManage()) { <button type="button" class="link-danger" (click)="removeFinding(f)">remover</button> }
            </div>
            <p class="fd-desc">{{ f.description }}</p>
            <app-evidence-panel [targetType]="'audit_finding'" [targetId]="f.id" [canManage]="canManageEvidence()" title="Evidências da constatação" />
          </div>
        } @empty { <p class="muted">Nenhuma constatação registrada.</p> }
      </section>

      <!-- Relatório -->
      <section class="wtn-card pad">
        <div class="wtn-card-title">Relatório de auditoria</div>
        <p class="muted block">
          Gate: a auditoria deve estar concluída e sem itens pendentes.
          <b>{{ a.readiness.can_approve_report ? 'Pronto para aprovação.' : 'Bloqueado.' }}</b>
        </p>
        <div class="rep-actions">
          @if (canManage() && a.draft_status === 'draft') {
            <p-button label="Submeter à revisão" (onClick)="submitReview()" [loading]="busy()" />
          }
          @if (canApprove() && a.draft_status === 'in_review') {
            <label class="sign-opt"><input type="checkbox" [(ngModel)]="signReport" /> assinar</label>
            <p-button label="Aprovar relatório" (onClick)="approve()" [loading]="busy()" />
          }
        </div>
        @for (v of versions(); track v.id) {
          <div class="ver-row">
            <span>v{{ v.version_number }} · {{ v.status }} @if (v.signed) { · assinado }</span>
            <button type="button" (click)="exportPdf(v)" title="Exportar PDF"><span class="pi pi-file-pdf"></span> PDF</button>
          </div>
        } @empty { <p class="muted">Nenhuma versão aprovada ainda.</p> }
      </section>
    } @else if (loading()) {
      <div class="wtn-card pad"><div class="wtn-skeleton skeleton-line"></div></div>
    } @else {
      <div class="wtn-empty"><div class="wtn-empty-title">Auditoria não encontrada</div></div>
    }
  `,
  styles: `
    :host { display: block; }
    .back { color: var(--wtn-text-2); display: inline-block; font-size: 12.5px; margin-bottom: 8px; text-decoration: none; }
    .code { color: var(--wtn-muted); font-size: 14px; }
    .actions { display: flex; gap: 8px; }
    .wtn-card { margin-bottom: 12px; }
    .block { color: var(--wtn-text-2); font-size: 12.5px; margin: 4px 0; }
    .inline-form { align-items: center; display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
    .stack-form { display: grid; gap: 8px; margin-bottom: 10px; }
    .row-2 { display: grid; gap: 8px; grid-template-columns: 200px 1fr; }
    input, select, textarea { background: var(--wtn-surface); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); color: var(--wtn-text); padding: 7px 10px; font: inherit; }
    .btn-primary { background: var(--wtn-primary); border: none; border-radius: var(--wtn-r-md); color: #fff; cursor: pointer; padding: 7px 16px; justify-self: start; }
    .btn-primary:disabled { opacity: .5; cursor: not-allowed; }
    .btn-secondary { background: var(--wtn-surface); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); color: var(--wtn-text-2); cursor: pointer; padding: 7px 12px; }
    .muted { color: var(--wtn-text-2); }
    .ck-row { align-items: center; border-top: 1px solid var(--wtn-border); display: flex; gap: 10px; justify-content: space-between; padding: 7px 0; }
    .ck-crit { color: var(--wtn-text); font-size: 12.5px; }
    .ck-result { color: var(--wtn-text-2); font-size: 11.5px; }
    .fd { border-top: 1px solid var(--wtn-border); display: grid; gap: 6px; padding: 10px 0; }
    .fd-head { align-items: center; display: flex; flex-wrap: wrap; gap: 8px; }
    .fd-head strong { color: var(--wtn-text); font-size: 13px; }
    .fd-type { border-radius: 999px; border: 1px solid var(--wtn-border); color: var(--wtn-text-2); font-size: 10.5px; padding: 2px 9px; }
    .fd-type--nc_maior { border-color: #c0392b; color: #c0392b; }
    .fd-type--nc_menor { border-color: #e67e22; color: #e67e22; }
    .fd-type--conforme { border-color: #2e9e5b; color: #2e9e5b; }
    .fd-promo { background: #fdecea; border-radius: 999px; color: #c0392b; font-size: 10px; padding: 2px 8px; }
    .fd-desc { color: var(--wtn-text-2); font-size: 12px; margin: 0; }
    .link-danger { background: none; border: none; color: #c0392b; cursor: pointer; font-size: 11.5px; margin-left: auto; }
    .rep-actions { align-items: center; display: flex; gap: 10px; margin-bottom: 8px; }
    .sign-opt { color: var(--wtn-text-2); font-size: 12px; }
    .ver-row { align-items: center; border-top: 1px solid var(--wtn-border); display: flex; gap: 10px; justify-content: space-between; padding: 7px 0; color: var(--wtn-text-2); font-size: 12px; }
    .ver-row button { background: var(--wtn-surface); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); color: var(--wtn-text-2); cursor: pointer; padding: 4px 10px; }
  `,
})
export class InternalAuditDetailPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly store = inject(AuthStore);
  private readonly route = inject(ActivatedRoute);
  private readonly messages = inject(MessageService);

  protected readonly loading = signal(false);
  protected readonly busy = signal(false);
  protected readonly audit = signal<AuditDetail | null>(null);
  protected readonly checklist = signal<AuditChecklistItem[]>([]);
  protected readonly findings = signal<AuditFinding[]>([]);
  protected readonly versions = signal<AuditReportVersion[]>([]);

  protected newCriterion = '';
  protected newType: AuditFindingType = 'observacao';
  protected newFindingTitle = '';
  protected newFindingDesc = '';
  protected signReport = false;
  protected id = '';

  protected readonly canManage = computed(() => hasPermission(this.store.currentRole(), 'manage_internal_audit'));
  protected readonly canApprove = computed(() => hasPermission(this.store.currentRole(), 'approve_audit_report'));
  protected readonly canManageEvidence = computed(() => hasPermission(this.store.currentRole(), 'manage_evidence'));

  ngOnInit(): void {
    this.id = this.route.snapshot.paramMap.get('id') ?? '';
    this.reload();
  }

  protected reload(): void {
    this.loading.set(true);
    this.api.get<AuditDetail>(`/internal-audit/audits/${this.id}`).subscribe({
      next: (a) => {
        this.audit.set(a);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
    this.api.get<AuditChecklistItem[]>(`/internal-audit/audits/${this.id}/checklist`).subscribe({ next: (c) => this.checklist.set(c) });
    this.api.get<AuditFinding[]>(`/internal-audit/audits/${this.id}/findings`).subscribe({ next: (f) => this.findings.set(f) });
    this.api.get<AuditReportVersion[]>(`/internal-audit/audits/${this.id}/report/versions`).subscribe({ next: (v) => this.versions.set(v) });
  }

  protected transition(action: 'start' | 'complete' | 'cancel'): void {
    this.busy.set(true);
    this.api.post(`/internal-audit/audits/${this.id}/transition`, { action }).subscribe({
      next: () => { this.busy.set(false); this.reload(); },
      error: (e) => { this.busy.set(false); this.toastError(e); },
    });
  }

  protected addChecklist(event: Event): void {
    event.preventDefault();
    if (!this.newCriterion.trim()) return;
    this.api.post(`/internal-audit/audits/${this.id}/checklist`, { criterion: this.newCriterion.trim() }).subscribe({
      next: () => { this.newCriterion = ''; this.reload(); },
      error: (e) => this.toastError(e),
    });
  }

  protected importChecklist(source: 'soa' | 'gap'): void {
    this.api.post(`/internal-audit/audits/${this.id}/checklist/import`, { source }).subscribe({
      next: () => { this.messages.add({ severity: 'success', summary: 'Itens importados' }); this.reload(); },
      error: (e) => this.toastError(e),
    });
  }

  protected updateResult(item: AuditChecklistItem, result: AuditChecklistResult): void {
    this.api.put(`/internal-audit/audits/${this.id}/checklist/${item.id}`, { result }).subscribe({
      next: () => this.reload(),
      error: (e) => this.toastError(e),
    });
  }

  protected addFinding(event: Event): void {
    event.preventDefault();
    if (!this.newFindingTitle.trim() || !this.newFindingDesc.trim()) return;
    this.api.post(`/internal-audit/audits/${this.id}/findings`, {
      finding_type: this.newType, title: this.newFindingTitle.trim(), description: this.newFindingDesc.trim(),
    }).subscribe({
      next: () => { this.newFindingTitle = ''; this.newFindingDesc = ''; this.reload(); },
      error: (e) => this.toastError(e),
    });
  }

  protected removeFinding(f: AuditFinding): void {
    this.api.delete(`/internal-audit/findings/${f.id}`).subscribe({ next: () => this.reload(), error: (e) => this.toastError(e) });
  }

  protected submitReview(): void {
    this.busy.set(true);
    this.api.post(`/internal-audit/audits/${this.id}/report/submit-review`, {}).subscribe({
      next: () => { this.busy.set(false); this.messages.add({ severity: 'success', summary: 'Enviado à revisão' }); this.reload(); },
      error: (e) => { this.busy.set(false); this.toastError(e); },
    });
  }

  protected approve(): void {
    this.busy.set(true);
    this.api.post(`/internal-audit/audits/${this.id}/report/approve`, { sign: this.signReport, classification: 'uso_interno' }).subscribe({
      next: () => { this.busy.set(false); this.messages.add({ severity: 'success', summary: 'Relatório aprovado' }); this.reload(); },
      error: (e) => { this.busy.set(false); this.toastError(e); },
    });
  }

  protected exportPdf(v: AuditReportVersion): void {
    this.api.getBlob(`/internal-audit/audits/${this.id}/report/versions/${v.id}/export`).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `relatorio-auditoria-v${v.version_number}.pdf`;
        link.click();
        URL.revokeObjectURL(url);
      },
      error: (e) => this.toastError(e),
    });
  }

  protected statusLabel(s: AuditDetail['status']): string { return AUDIT_STATUS_LABELS[s]; }
  protected resultLabel(r: AuditChecklistResult): string { return CHECKLIST_RESULT_LABELS[r]; }
  protected findingLabel(t: AuditFindingType): string { return FINDING_TYPE_LABELS[t]; }

  private toastError(error: unknown): void {
    let detail = 'Operação não concluída.';
    if (typeof error === 'object' && error && 'error' in error) {
      const payload = (error as { error?: { detail?: string } }).error;
      if (payload?.detail) detail = payload.detail;
    }
    this.messages.add({ severity: 'error', summary: 'Erro', detail });
  }
}
