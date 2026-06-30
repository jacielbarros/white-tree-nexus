import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ActivatedRoute } from '@angular/router';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { hasPermission } from '@app/core/permissions';
import {
  CorrectiveAction,
  CorrectiveActionStatus,
  MembershipRow,
  NCDetail,
  NCVerification,
  VerificationResult,
} from '@app/core/models';
import { EvidencePanel } from '@app/shared/evidence-panel/evidence-panel';
import { TraceabilityTimeline } from '@app/shared/traceability-timeline/traceability-timeline';
import {
  ACTION_STATUS_LABELS,
  NC_ORIGIN_LABELS,
  NC_SEVERITY_LABELS,
  NC_STATUS_LABELS,
  VERIFICATION_LABELS,
} from '../nonconformities/nonconformity-labels';

/** Detalhe da NC: causa raiz, status, ações corretivas, verificação de eficácia, evidências, PDCA. */
@Component({
  selector: 'app-nonconformity-detail',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, RouterLink, ButtonModule, EvidencePanel, TraceabilityTimeline],
  template: `
    <a class="back" routerLink="../nonconformities">← Não conformidades</a>

    @if (nc(); as n) {
      <header class="wtn-page-header">
        <div>
          <h1 class="wtn-page-title">{{ n.code }} · {{ n.title }}</h1>
          <p class="wtn-page-desc">
            {{ originLabel(n.origin) }} · <span class="sev sev--{{ n.severity }}">{{ severityLabel(n.severity) }}</span>
            · <span class="status status--{{ n.status }}">{{ statusLabel(n.status) }}</span>
          </p>
        </div>
      </header>

      <div class="grid">
        <section class="wtn-card pad">
          <div class="wtn-card-title">Tratamento</div>
          <p class="desc">{{ n.description }}</p>

          @if (canManage()) {
            <label class="lbl">Causa raiz</label>
            <textarea [(ngModel)]="rootCause" name="rc" rows="2" placeholder="Causa raiz identificada"></textarea>
            <label class="lbl">Método (5 Porquês, Ishikawa…)</label>
            <input type="text" [(ngModel)]="rootCauseMethod" name="rcm" placeholder="Método de análise" />
            <button type="button" class="btn-primary" (click)="saveRootCause(n)">Salvar causa raiz</button>
          } @else {
            <p class="desc"><strong>Causa raiz:</strong> {{ n.root_cause || '—' }}</p>
          }

          <div class="readiness">
            <span [class.ok]="n.readiness.has_effective_verification">Verificação eficaz: {{ n.readiness.has_effective_verification ? 'sim' : 'não' }}</span>
            <span [class.warn]="n.readiness.open_actions > 0">Ações abertas: {{ n.readiness.open_actions }}</span>
            <span [class.warn]="n.readiness.overdue_actions > 0">Vencidas: {{ n.readiness.overdue_actions }}</span>
          </div>

          @if (canManage()) {
            <div class="transitions">
              @if (n.status === 'open') { <button class="btn-sec" (click)="transition(n, 'start')">Iniciar tratamento</button> }
              @if (n.status === 'in_progress') { <button class="btn-sec" (click)="transition(n, 'send-verify')">Enviar p/ verificação</button> }
              @if (n.status === 'in_verification') {
                <button class="btn-primary" [disabled]="!n.readiness.can_close" (click)="transition(n, 'close')"
                  [title]="n.readiness.can_close ? '' : 'Exige verificação eficaz e nenhuma ação aberta'">Encerrar</button>
              }
              @if (n.status !== 'closed' && n.status !== 'cancelled') { <button class="link-danger" (click)="transition(n, 'cancel')">Cancelar</button> }
            </div>
          }
        </section>

        <section class="wtn-card pad">
          <div class="wtn-card-title">Ações corretivas</div>
          @if (canManage()) {
            <form class="stack-form" (submit)="addAction(n, $event)">
              <input type="text" [(ngModel)]="actDescription" name="ad" placeholder="Descrição da ação" />
              <select [(ngModel)]="actResponsible" name="ar">
                <option value="">Responsável…</option>
                @for (m of members(); track m.user_id) { <option [value]="m.user_id">{{ m.full_name || m.email }}</option> }
              </select>
              <input type="date" [(ngModel)]="actDueDate" name="add" />
              <button type="submit" class="btn-primary" [disabled]="!canAddAction()">Adicionar ação</button>
            </form>
          }
          @if (!actions().length) {
            <p class="muted">Nenhuma ação corretiva.</p>
          } @else {
            @for (a of actions(); track a.id) {
              <div class="act-row" [class.overdue]="a.overdue">
                <div class="act-meta">
                  <strong>{{ a.description }}</strong>
                  <span>{{ statusActionLabel(a.status) }}@if (a.due_date) { · prazo {{ a.due_date }} }@if (a.overdue) { · <em>vencida</em> }</span>
                </div>
                @if (canManage()) {
                  <select [ngModel]="a.status" (ngModelChange)="updateActionStatus(a, $event)" name="as-{{ a.id }}">
                    @for (s of actionStatuses; track s) { <option [value]="s">{{ statusActionLabel(s) }}</option> }
                  </select>
                }
              </div>
            }
          }
        </section>
      </div>

      <section class="wtn-card pad">
        <div class="wtn-card-title">Verificação de eficácia (gate de encerramento)</div>
        @if (canManage()) {
          <form class="inline-form" (submit)="addVerification(n, $event)">
            <select [(ngModel)]="verResult" name="vr">
              @for (r of verResults; track r) { <option [value]="r">{{ verLabel(r) }}</option> }
            </select>
            <input type="text" [(ngModel)]="verNotes" name="vn" placeholder="Observações (opcional)" />
            <button type="submit" class="btn-primary">Registrar verificação</button>
          </form>
        }
        @if (!verifications().length) {
          <p class="muted">Nenhuma verificação registrada.</p>
        } @else {
          @for (v of verifications(); track v.id) {
            <div class="ver-row">
              <span class="ver ver--{{ v.result }}">{{ verLabel(v.result) }}</span>
              <span class="ver-notes">{{ v.notes || '—' }}</span>
              <span class="muted">{{ formatDate(v.verified_at) }}</span>
            </div>
          }
        }
      </section>

      <div class="grid">
        <app-evidence-panel [targetType]="'nonconformity'" [targetId]="n.id" [canManage]="canManageEvidence()" title="Evidências da NC" />
        <app-traceability-timeline [targetType]="'nonconformity'" [targetId]="n.id" title="Linha do tempo (PDCA)" />
      </div>
    } @else {
      <p class="muted">Carregando…</p>
    }
  `,
  styles: `
    :host { display: block; }
    .back { color: var(--wtn-primary); display: inline-block; font-size: 12.5px; margin-bottom: 8px; text-decoration: none; }
    .grid { display: grid; gap: 12px; grid-template-columns: 1fr 1fr; margin-bottom: 12px; }
    @media (max-width: 880px) { .grid { grid-template-columns: 1fr; } }
    .desc { color: var(--wtn-text-2); font-size: 13px; }
    .lbl { color: var(--wtn-text-2); display: block; font-size: 11.5px; margin: 8px 0 3px; }
    .stack-form { display: grid; gap: 8px; margin-bottom: 10px; }
    .inline-form { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
    input, select, textarea {
      background: var(--wtn-surface); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md);
      color: var(--wtn-text); padding: 7px 10px; font: inherit;
    }
    .btn-primary { background: var(--wtn-primary); border: none; border-radius: var(--wtn-r-md); color: #fff; cursor: pointer; padding: 7px 16px; justify-self: start; }
    .btn-primary:disabled { opacity: .5; cursor: not-allowed; }
    .btn-sec { background: var(--wtn-surface); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); color: var(--wtn-text); cursor: pointer; padding: 6px 14px; }
    .link-danger { background: none; border: none; color: #d14343; cursor: pointer; font-size: 12.5px; }
    .muted { color: var(--wtn-text-2); }
    .readiness { display: flex; flex-wrap: wrap; gap: 12px; font-size: 12px; margin: 10px 0; color: var(--wtn-text-2); }
    .readiness .ok { color: #2e9e5b; }
    .readiness .warn { color: #d08a2e; }
    .transitions { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 8px; }
    .act-row { align-items: center; border-top: 1px solid var(--wtn-border); display: flex; gap: 10px; justify-content: space-between; padding: 7px 0; }
    .act-row.overdue strong { color: #d14343; }
    .act-meta { display: flex; flex-direction: column; }
    .act-meta span { color: var(--wtn-text-2); font-size: 11.5px; }
    .ver-row { align-items: center; border-top: 1px solid var(--wtn-border); display: flex; gap: 10px; padding: 7px 0; }
    .ver-notes { flex: 1; font-size: 12.5px; }
    .sev, .status, .ver { border-radius: 999px; font-size: 10.5px; padding: 2px 9px; border: 1px solid var(--wtn-border); }
    .sev--maior { border-color: #d14343; color: #d14343; }
    .sev--menor { border-color: #d08a2e; color: #d08a2e; }
    .status--closed { border-color: #2e9e5b; color: #2e9e5b; }
    .ver--effective { border-color: #2e9e5b; color: #2e9e5b; }
    .ver--ineffective { border-color: #d14343; color: #d14343; }
  `,
})
export class NonconformityDetailPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly store = inject(AuthStore);
  private readonly route = inject(ActivatedRoute);
  private readonly messages = inject(MessageService);

  protected readonly nc = signal<NCDetail | null>(null);
  protected readonly actions = signal<CorrectiveAction[]>([]);
  protected readonly verifications = signal<NCVerification[]>([]);
  protected readonly members = signal<MembershipRow[]>([]);

  protected rootCause = '';
  protected rootCauseMethod = '';
  protected actDescription = '';
  protected actResponsible = '';
  protected actDueDate = '';
  protected verResult: VerificationResult = 'effective';
  protected verNotes = '';

  protected readonly actionStatuses: CorrectiveActionStatus[] = ['planned', 'in_progress', 'done', 'cancelled'];
  protected readonly verResults: VerificationResult[] = ['effective', 'ineffective'];

  protected readonly canManage = computed(() => hasPermission(this.store.currentRole(), 'manage_nonconformity'));
  protected readonly canManageEvidence = computed(() => hasPermission(this.store.currentRole(), 'manage_evidence'));

  private get id(): string {
    return this.route.snapshot.paramMap.get('id') ?? '';
  }

  ngOnInit(): void {
    this.load();
    if (this.canManage()) {
      this.api.listUsers().subscribe({ next: (rows) => this.members.set(rows.filter((m) => m.status === 'active')) });
    }
  }

  protected load(): void {
    this.api.get<NCDetail>(`/nonconformities/${this.id}`).subscribe({
      next: (n) => {
        this.nc.set(n);
        this.rootCause = n.root_cause ?? '';
        this.rootCauseMethod = n.root_cause_method ?? '';
      },
      error: (e) => this.messages.add({ severity: 'error', summary: 'Erro', detail: this.errorDetail(e) }),
    });
    this.api.get<CorrectiveAction[]>(`/nonconformities/${this.id}/actions`).subscribe({ next: (a) => this.actions.set(a) });
    this.api.get<NCVerification[]>(`/nonconformities/${this.id}/verifications`).subscribe({ next: (v) => this.verifications.set(v) });
  }

  protected saveRootCause(n: NCDetail): void {
    this.api.put<NCDetail>(`/nonconformities/${n.id}`, {
      origin: n.origin,
      title: n.title,
      description: n.description,
      severity: n.severity,
      target_type: n.target_type,
      target_id: n.target_id,
      root_cause: this.rootCause.trim() || null,
      root_cause_method: this.rootCauseMethod.trim() || null,
    }).subscribe({
      next: () => {
        this.messages.add({ severity: 'success', summary: 'Causa raiz salva' });
        this.load();
      },
      error: (e) => this.messages.add({ severity: 'error', summary: 'Erro', detail: this.errorDetail(e) }),
    });
  }

  protected transition(n: NCDetail, action: string): void {
    this.api.post(`/nonconformities/${n.id}/transition`, { action }).subscribe({
      next: () => {
        this.messages.add({ severity: 'success', summary: 'Status atualizado' });
        this.load();
      },
      error: (e) => this.messages.add({ severity: 'error', summary: 'Transição inválida', detail: this.errorDetail(e) }),
    });
  }

  protected canAddAction(): boolean {
    return !!(this.actDescription.trim() && this.actResponsible);
  }

  protected addAction(n: NCDetail, event: Event): void {
    event.preventDefault();
    if (!this.canAddAction()) return;
    this.api.post(`/nonconformities/${n.id}/actions`, {
      description: this.actDescription.trim(),
      responsible_member_id: this.actResponsible,
      due_date: this.actDueDate || null,
    }).subscribe({
      next: () => {
        this.messages.add({ severity: 'success', summary: 'Ação adicionada' });
        this.actDescription = '';
        this.actResponsible = '';
        this.actDueDate = '';
        this.load();
      },
      error: (e) => this.messages.add({ severity: 'error', summary: 'Erro', detail: this.errorDetail(e) }),
    });
  }

  protected updateActionStatus(a: CorrectiveAction, status: CorrectiveActionStatus): void {
    this.api.put(`/nonconformities/actions/${a.id}`, {
      description: a.description,
      responsible_member_id: a.responsible_member_id,
      due_date: a.due_date,
      status,
    }).subscribe({
      next: () => this.load(),
      error: (e) => this.messages.add({ severity: 'error', summary: 'Erro', detail: this.errorDetail(e) }),
    });
  }

  protected addVerification(n: NCDetail, event: Event): void {
    event.preventDefault();
    this.api.post(`/nonconformities/${n.id}/verifications`, { result: this.verResult, notes: this.verNotes.trim() || null }).subscribe({
      next: () => {
        this.messages.add({ severity: 'success', summary: 'Verificação registrada' });
        this.verNotes = '';
        this.load();
      },
      error: (e) => this.messages.add({ severity: 'error', summary: 'Erro', detail: this.errorDetail(e) }),
    });
  }

  protected originLabel(o: NCDetail['origin']): string { return NC_ORIGIN_LABELS[o]; }
  protected severityLabel(s: NCDetail['severity']): string { return NC_SEVERITY_LABELS[s]; }
  protected statusLabel(s: NCDetail['status']): string { return NC_STATUS_LABELS[s]; }
  protected statusActionLabel(s: CorrectiveActionStatus): string { return ACTION_STATUS_LABELS[s]; }
  protected verLabel(r: VerificationResult): string { return VERIFICATION_LABELS[r]; }

  protected formatDate(iso: string): string {
    return new Date(iso).toLocaleString('pt-BR');
  }

  private errorDetail(error: unknown): string {
    if (typeof error === 'object' && error && 'error' in error) {
      const payload = (error as { error?: { detail?: string } }).error;
      if (payload?.detail) return payload.detail;
    }
    return 'Operação não concluída.';
  }
}
