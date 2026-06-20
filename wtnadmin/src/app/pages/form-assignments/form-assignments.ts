import { SlicePipe } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { TagModule } from 'primeng/tag';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { hasPermission } from '@app/core/permissions';
import {
  AssignmentEvent,
  AssignmentStatus,
  FormAssignment,
  FormSignature,
  FormTemplate,
  MembershipRow,
} from '@app/core/models';

const STATUS_LABELS: Record<AssignmentStatus, string> = {
  pending: 'Pendente',
  in_progress: 'Em preenchimento',
  submitted: 'Preenchido',
  signed: 'Assinado',
  completed: 'Concluído',
  cancelled: 'Cancelado',
};

const STATUS_SEVERITY: Record<
  AssignmentStatus,
  'info' | 'warn' | 'secondary' | 'success' | 'danger'
> = {
  pending: 'info',
  in_progress: 'warn',
  submitted: 'warn',
  signed: 'success',
  completed: 'success',
  cancelled: 'danger',
};

@Component({
  selector: 'app-form-assignments',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, CardModule, ButtonModule, TagModule, SlicePipe],
  template: `
    <div class="page-header">
      <h2>Atribuições de Formulário</h2>
      @if (canAssign()) {
        <p-button label="Nova atribuição" icon="pi pi-plus" (onClick)="openNew()" />
      }
    </div>

    @if (canAssign()) {
      <div class="policy-bar">
        <label class="policy-label">
          <input type="checkbox" [ngModel]="policyDouble()" (ngModelChange)="togglePolicy($event)" />
          Exigir contra-assinatura do atribuidor (assinatura dupla)
        </label>
        <span class="policy-hint">
          Quando ligado, o formulário só conclui após o preenchedor <em>e</em> o atribuidor assinarem.
        </span>
      </div>
    }

    @if (creating()) {
      <p-card class="creator">
        <h3>Nova atribuição</h3>
        <div class="form-row">
          <label>Template</label>
          <select [(ngModel)]="newTemplateId">
            <option value="">— Selecione —</option>
            @for (t of templates(); track t.id) {
              <option [value]="t.id">{{ t.title }} ({{ t.kind }})</option>
            }
          </select>
        </div>
        <div class="form-row">
          <label>Preenchedor</label>
          <div class="radio-group">
            <label><input type="radio" [(ngModel)]="respondentType" value="member" /> Membro da org</label>
            <label><input type="radio" [(ngModel)]="respondentType" value="external" /> Externo (e-mail)</label>
          </div>
        </div>
        @if (respondentType === 'member') {
          <div class="form-row">
            <label>Membro</label>
            <select [(ngModel)]="newRespondentUserId">
              <option value="">— Selecione o membro —</option>
              @for (m of members(); track m.user_id) {
                <option [value]="m.user_id">{{ m.full_name || m.email }} ({{ m.role }})</option>
              }
            </select>
          </div>
        } @else {
          <div class="form-row">
            <label>E-mail externo</label>
            <input type="email" [(ngModel)]="newRespondentEmail" placeholder="externo@exemplo.com" />
          </div>
        }
        <div class="form-row">
          <label>Prazo (opcional)</label>
          <input type="datetime-local" [(ngModel)]="newDeadline" />
        </div>
        <div class="form-row">
          <label>Instruções (opcional)</label>
          <textarea rows="3" [(ngModel)]="newInstructions" placeholder="Orientações para o preenchedor..."></textarea>
        </div>
        <div class="actions footer">
          <p-button label="Atribuir" (onClick)="assign()" [disabled]="saving()" />
          <p-button label="Cancelar" severity="secondary" (onClick)="creating.set(false)" />
        </div>
      </p-card>
    }

    @if (selected()) {
      <p-card class="detail">
        <div class="detail-header">
          <h3>{{ selected()!.title }}</h3>
          <p-tag [value]="statusLabel(selected()!.status)" [severity]="statusSeverity(selected()!.status)" />
          @if (selected()!.overdue) { <span class="overdue">ATRASADO</span> }
          <p-button icon="pi pi-times" severity="secondary" size="small" (onClick)="selected.set(null)" />
        </div>

        <div class="meta-row">
          <span>Preenchedor: <strong>{{ selected()!.respondent_email ?? selected()!.respondent_user_id ?? '—' }}</strong></span>
          @if (selected()!.deadline_at) {
            <span>Prazo: <strong>{{ selected()!.deadline_at | slice:0:10 }}</strong></span>
          }
        </div>

        @if (selected()!.instructions) {
          <p class="instructions">{{ selected()!.instructions }}</p>
        }

        <!-- Respostas preenchidas (revisão) -->
        @if (showAnswers()) {
          <h4>Respostas</h4>
          @if (answerRows().length) {
            <div class="answers">
              @for (row of answerRows(); track row.label) {
                <div class="answer-row">
                  <span class="a-key">{{ row.label }}</span>
                  <span class="a-val">{{ row.value }}</span>
                </div>
              }
            </div>
          } @else {
            <p class="empty">Sem respostas registradas.</p>
          }
        }

        <!-- Ações do atribuidor -->
        <div class="actions-row">
          @if (canFill() && selected()!.status === 'pending') {
            <p-button label="Assumir e preencher" (onClick)="goFill(selected()!.id)" />
          }
          @if (canFill() && selected()!.status === 'in_progress') {
            <p-button label="Continuar preenchendo" (onClick)="goFill(selected()!.id)" />
          }
          @if (canSign() && selected()!.status === 'submitted') {
            <p-button label="Assinar" severity="success" (onClick)="sign(selected()!.id)" [disabled]="signing()" />
          }
          @if (canAssign() && selected()!.status === 'submitted') {
            <p-button label="Devolver" severity="warn" (onClick)="showReturn.set(true)" />
          }
          @if (canAssign() && !['completed','cancelled'].includes(selected()!.status)) {
            <p-button label="Lembrar" severity="secondary" (onClick)="remind(selected()!.id)" />
            <p-button label="Cancelar" severity="danger" (onClick)="cancelAssignment(selected()!.id)" />
          }
          @if (['signed','completed'].includes(selected()!.status)) {
            <p-button label="Verificar integridade" severity="secondary" (onClick)="verify(selected()!.id)" />
          }
        </div>

        @if (showReturn()) {
          <div class="return-form">
            <input type="text" [(ngModel)]="returnReason" placeholder="Motivo da devolução..." />
            <p-button label="Confirmar devolução" severity="warn" size="small"
              (onClick)="returnAssignment(selected()!.id)" [disabled]="!returnReason.trim()" />
            <p-button label="Cancelar" severity="secondary" size="small" (onClick)="showReturn.set(false)" />
          </div>
        }

        <!-- Assinaturas -->
        @if (signatures().length) {
          <h4>Assinaturas</h4>
          @for (sig of signatures(); track sig.id) {
            <div class="sig-row">
              <span>{{ sig.signer_name }}</span>
              <span class="sig-role">{{ sig.signer_role === 'filler' ? 'Preenchedor' : 'Atribuidor' }}</span>
              <span class="sig-date">{{ sig.signed_at | slice:0:10 }}</span>
              <span class="sig-hash" title="{{ sig.content_hash }}">SHA-256: {{ sig.content_hash | slice:0:12 }}…</span>
            </div>
          }
        }

        <!-- Linha do tempo (wizard) T027 -->
        <h4>Linha do tempo</h4>
        @if (events().length === 0) {
          <p class="empty">Carregando eventos...</p>
        } @else {
          <div class="timeline">
            @for (ev of events(); track ev.id) {
              <div class="tl-item">
                <div class="tl-dot"></div>
                <div class="tl-body">
                  <span class="tl-event">{{ ev.event }}</span>
                  @if (ev.actor_label) { <span class="tl-actor">{{ ev.actor_label }}</span> }
                  @if (ev.note) { <span class="tl-note">{{ ev.note }}</span> }
                  <span class="tl-date">{{ ev.created_at | slice:0:16 }}</span>
                </div>
              </div>
            }
          </div>
        }
      </p-card>
    }

    <!-- Lista de atribuições -->
    <div class="assignment-list">
      @for (a of assignments(); track a.id) {
        <div class="a-row" (click)="select(a)" [class.selected]="selected()?.id === a.id">
          <div class="a-main">
            <span class="a-title">{{ a.title }}</span>
            @if (a.overdue) { <span class="overdue-badge">Atrasado</span> }
          </div>
          <span class="a-respondent">{{ a.respondent_email ?? a.respondent_user_id ?? 'membro' }}</span>
          <p-tag [value]="statusLabel(a.status)" [severity]="statusSeverity(a.status)" />
          @if (a.deadline_at) {
            <span class="a-deadline">{{ a.deadline_at | slice:0:10 }}</span>
          }
        </div>
      } @empty {
        <p class="empty">Nenhuma atribuição encontrada.</p>
      }
    </div>
  `,
  styles: `
    .page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
    h2 { margin: 0; }
    .policy-bar {
      display: flex; flex-direction: column; gap: 0.2rem; margin-bottom: 1rem;
      padding: 0.6rem 0.8rem; border-radius: 8px;
      background: var(--p-surface-hover, rgba(255,255,255,.04));
    }
    .policy-label { display: flex; align-items: center; gap: 0.5rem; font-size: 0.9rem; font-weight: 500; }
    .policy-label input[type='checkbox'] { width: 1.1rem; height: 1.1rem; }
    .policy-hint { font-size: 0.8rem; opacity: 0.65; padding-left: 1.6rem; }
    .creator, .detail { margin-bottom: 1.25rem; }
    h3 { margin-top: 0; }
    h4 { margin: 1rem 0 0.5rem; }
    .form-row { display: flex; flex-direction: column; gap: 0.25rem; margin-bottom: 0.75rem; }
    .form-row label { font-size: 0.85rem; font-weight: 600; opacity: 0.8; }
    .radio-group { display: flex; gap: 1rem; }
    .radio-group label { font-weight: 400; display: flex; gap: 0.3rem; align-items: center; }
    input[type='text'], input[type='email'], input[type='datetime-local'], textarea, select {
      width: 100%; background: var(--p-content-background, #1e1e1e);
      border: 1px solid var(--p-content-border-color, #444); border-radius: 6px;
      padding: 0.4rem 0.5rem; font: inherit; color: inherit;
    }
    .actions { display: flex; gap: 0.5rem; margin-top: 0.75rem; }
    .actions.footer { border-top: 1px solid var(--p-content-border-color, #333); padding-top: 0.75rem; margin-top: 1rem; }
    .detail-header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem; flex-wrap: wrap; }
    .detail-header h3 { margin: 0; flex: 1; }
    .overdue { background: #c0392b; color: #fff; border-radius: 4px; padding: 0.15rem 0.5rem; font-size: 0.75rem; font-weight: 700; }
    .meta-row { display: flex; gap: 1.5rem; font-size: 0.88rem; margin-bottom: 0.5rem; }
    .instructions { opacity: 0.8; font-size: 0.9rem; font-style: italic; border-left: 3px solid var(--p-content-border-color, #444); padding-left: 0.75rem; }
    .answers { display: flex; flex-direction: column; gap: 0.25rem; margin-bottom: 0.5rem; }
    .answer-row { display: grid; grid-template-columns: 1fr 2fr; gap: 1rem; padding: 0.3rem 0; border-bottom: 1px solid var(--p-content-border-color, #2a2a2a); font-size: 0.9rem; }
    .a-key { font-weight: 600; opacity: 0.8; }
    .actions-row { display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 0.75rem 0; }
    .return-form { display: flex; gap: 0.5rem; align-items: center; margin-top: 0.5rem; }
    .return-form input { flex: 1; }
    .sig-row { display: flex; gap: 1rem; align-items: center; font-size: 0.85rem; padding: 0.3rem 0; border-bottom: 1px solid var(--p-content-border-color, #333); }
    .sig-role { opacity: 0.7; }
    .sig-date { opacity: 0.7; }
    .sig-hash { font-family: monospace; font-size: 0.78rem; opacity: 0.6; }
    /* Wizard / Timeline */
    .timeline { padding-left: 1rem; }
    .tl-item { display: flex; gap: 0.75rem; margin-bottom: 0.6rem; position: relative; }
    .tl-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--p-primary-color, #6c63ff); flex-shrink: 0; margin-top: 4px; }
    .tl-item::before { content: ''; position: absolute; left: 4px; top: 14px; bottom: -10px; width: 2px; background: var(--p-content-border-color, #444); }
    .tl-item:last-child::before { display: none; }
    .tl-body { display: flex; flex-direction: column; gap: 0.1rem; }
    .tl-event { font-weight: 600; font-size: 0.88rem; }
    .tl-actor, .tl-note { font-size: 0.82rem; opacity: 0.7; }
    .tl-date { font-size: 0.78rem; opacity: 0.55; font-family: monospace; }
    /* Lista */
    .assignment-list { display: flex; flex-direction: column; gap: 0.4rem; }
    .a-row {
      display: flex; align-items: center; gap: 1rem; padding: 0.6rem 0.8rem;
      border-radius: 8px; border: 1px solid var(--p-content-border-color, #333);
      cursor: pointer; transition: background 0.15s;
    }
    .a-row:hover, .a-row.selected { background: var(--p-surface-hover, rgba(255,255,255,.04)); }
    .a-main { display: flex; gap: 0.5rem; align-items: center; flex: 1; min-width: 0; }
    .a-title { font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .a-respondent { font-size: 0.82rem; opacity: 0.7; white-space: nowrap; }
    .a-deadline { font-size: 0.8rem; opacity: 0.6; white-space: nowrap; }
    .overdue-badge { background: #c0392b; color: #fff; border-radius: 3px; padding: 0.1rem 0.35rem; font-size: 0.7rem; font-weight: 700; flex-shrink: 0; }
    .empty { opacity: 0.7; font-style: italic; }
  `,
})
export class FormAssignmentsPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly messages = inject(MessageService);
  private readonly store = inject(AuthStore);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  protected readonly assignments = signal<FormAssignment[]>([]);
  protected readonly templates = signal<FormTemplate[]>([]);
  protected readonly members = signal<MembershipRow[]>([]);
  protected readonly selected = signal<FormAssignment | null>(null);
  protected readonly events = signal<AssignmentEvent[]>([]);
  protected readonly signatures = signal<FormSignature[]>([]);
  protected readonly creating = signal(false);
  protected readonly saving = signal(false);
  protected readonly signing = signal(false);
  protected readonly showReturn = signal(false);
  protected readonly policyDouble = signal(false);

  protected newTemplateId = '';
  protected respondentType: 'member' | 'external' = 'member';
  protected newRespondentUserId = '';
  protected newRespondentEmail = '';
  protected newDeadline = '';
  protected newInstructions = '';
  protected returnReason = '';

  protected readonly canAssign = computed(() =>
    hasPermission(this.store.currentRole(), 'assign_form'),
  );
  protected readonly canFill = computed(() =>
    hasPermission(this.store.currentRole(), 'fill_form'),
  );
  protected readonly canSign = computed(() =>
    hasPermission(this.store.currentRole(), 'sign_form'),
  );

  protected readonly showAnswers = computed(() => {
    const a = this.selected();
    return !!a && ['submitted', 'signed', 'completed'].includes(a.status);
  });

  protected readonly answerRows = computed(() => {
    const a = this.selected();
    if (!a) return [];
    return (a.fields_snapshot ?? []).map((f) => ({
      label: f.label,
      value: this.fmtAnswer(a.answers?.[f.key]),
    }));
  });

  private fmtAnswer(v: unknown): string {
    if (v === true) return 'Sim';
    if (v === false) return 'Não';
    if (v === null || v === undefined || v === '') return '—';
    return String(v);
  }

  ngOnInit(): void {
    this.loadAssignments();
    if (this.canAssign()) {
      this.api.listTemplates().subscribe({ next: (list) => this.templates.set(list) });
      this.api.listUsers().subscribe({ next: (list) => this.members.set(list) });
      this.api.getSignaturePolicy().subscribe({
        next: (p) => this.policyDouble.set(p.require_assigner_countersignature),
      });
    }
    const tid = this.route.snapshot.queryParamMap.get('template_id');
    if (tid) {
      this.newTemplateId = tid;
      this.creating.set(true);
    }
  }

  private loadAssignments(): void {
    this.api.listAssignments().subscribe({ next: (list) => this.assignments.set(list) });
  }

  protected statusLabel(s: AssignmentStatus): string { return STATUS_LABELS[s]; }
  protected statusSeverity(s: AssignmentStatus) { return STATUS_SEVERITY[s]; }

  protected togglePolicy(value: boolean): void {
    this.api.updateSignaturePolicy({ require_assigner_countersignature: value }).subscribe({
      next: (p) => {
        this.policyDouble.set(p.require_assigner_countersignature);
        this.messages.add({
          severity: 'info',
          summary: 'Política de assinatura atualizada',
          detail: value ? 'Contra-assinatura exigida.' : 'Assinatura única.',
          life: 3000,
        });
      },
      error: () => this.policyDouble.set(!value),
    });
  }

  protected openNew(): void {
    this.newTemplateId = '';
    this.respondentType = 'member';
    this.newRespondentUserId = '';
    this.newRespondentEmail = '';
    this.newDeadline = '';
    this.newInstructions = '';
    this.creating.set(true);
  }

  protected assign(): void {
    if (!this.newTemplateId) {
      this.messages.add({ severity: 'warn', summary: 'Selecione um template', life: 3000 });
      return;
    }
    this.saving.set(true);
    const payload = {
      template_id: this.newTemplateId,
      respondent_user_id: this.respondentType === 'member' ? this.newRespondentUserId || null : null,
      respondent_email: this.respondentType === 'external' ? this.newRespondentEmail || null : null,
      deadline_at: this.newDeadline ? new Date(this.newDeadline).toISOString() : null,
      instructions: this.newInstructions || null,
    };
    this.api.createAssignment(payload).subscribe({
      next: (a) => {
        this.saving.set(false);
        this.creating.set(false);
        this.messages.add({ severity: 'success', summary: 'Atribuição criada', life: 3000 });
        this.assignments.update((list) => [a, ...list]);
        this.select(a);
      },
      error: () => this.saving.set(false),
    });
  }

  protected select(a: FormAssignment): void {
    this.selected.set(a);
    this.showReturn.set(false);
    this.returnReason = '';
    this.events.set([]);
    this.signatures.set([]);
    this.api.getAssignmentEvents(a.id).subscribe({ next: (evs) => this.events.set(evs) });
    if (['signed', 'completed'].includes(a.status)) {
      this.api.getAssignmentSignatures(a.id).subscribe({ next: (sigs) => this.signatures.set(sigs) });
    }
  }

  protected goFill(id: string): void {
    void this.router.navigate(['/app', 'form-fill', id]);
  }

  protected sign(id: string): void {
    this.signing.set(true);
    this.api.signAssignment(id).subscribe({
      next: (sig) => {
        this.signing.set(false);
        this.messages.add({ severity: 'success', summary: 'Formulário assinado', life: 4000 });
        this.api.getAssignment(id).subscribe({
          next: (a) => {
            this.selected.set(a);
            this.signatures.update((list) => [...list, sig]);
            this.api.getAssignmentEvents(id).subscribe({ next: (evs) => this.events.set(evs) });
            this.loadAssignments();
          },
        });
      },
      error: () => this.signing.set(false),
    });
  }

  protected returnAssignment(id: string): void {
    this.api.returnAssignment(id, this.returnReason).subscribe({
      next: (a) => {
        this.selected.set(a);
        this.showReturn.set(false);
        this.returnReason = '';
        this.messages.add({ severity: 'info', summary: 'Formulário devolvido', life: 3000 });
        this.api.getAssignmentEvents(id).subscribe({ next: (evs) => this.events.set(evs) });
        this.loadAssignments();
      },
    });
  }

  protected cancelAssignment(id: string): void {
    this.api.cancelAssignment(id).subscribe({
      next: (a) => {
        this.selected.set(a);
        this.messages.add({ severity: 'info', summary: 'Atribuição cancelada', life: 3000 });
        this.loadAssignments();
      },
    });
  }

  protected remind(id: string): void {
    this.api.remindAssignment(id).subscribe({
      next: () => this.messages.add({ severity: 'info', summary: 'Lembrete enviado', life: 3000 }),
    });
  }

  protected verify(id: string): void {
    this.api.verifyAssignment(id).subscribe({
      next: (r) => {
        this.messages.add({
          severity: r.valid ? 'success' : 'error',
          summary: r.valid ? 'Integridade válida ✓' : 'Falha de integridade ✗',
          detail: `SHA-256: ${r.content_hash.slice(0, 16)}…`,
          life: 6000,
        });
      },
    });
  }
}
