import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { InputMaskModule } from 'primeng/inputmask';

import { ApiService } from '@app/core/api.service';
import { AssignmentStatus, FormAssignment, FormField } from '@app/core/models';

const STATUS_LABELS: Record<AssignmentStatus, string> = {
  pending: 'Pendente',
  in_progress: 'Em preenchimento',
  submitted: 'Enviado',
  signed: 'Assinado',
  completed: 'Concluído',
  cancelled: 'Cancelado',
};

const STATUS_CLASSES: Record<AssignmentStatus, string> = {
  pending: 'wtn-tag--info',
  in_progress: 'wtn-tag--primary',
  submitted: 'wtn-tag--info',
  signed: 'wtn-tag--success',
  completed: 'wtn-tag--success',
  cancelled: 'wtn-tag--danger',
};

const WORKFLOW_STEPS: { key: AssignmentStatus; label: string }[] = [
  { key: 'pending', label: 'Pendente' },
  { key: 'in_progress', label: 'Em preenchimento' },
  { key: 'submitted', label: 'Enviado' },
  { key: 'signed', label: 'Assinado' },
  { key: 'completed', label: 'Concluído' },
];

/** Ordena por `order` e agrupa por `section` (campos sem seção ficam num grupo sem título). */
export function groupFields(fields: FormField[]): { section: string; items: FormField[] }[] {
  const sorted = [...fields].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
  const groups: { section: string; items: FormField[] }[] = [];
  for (const f of sorted) {
    const sec = (f.section ?? '').trim();
    let g = groups.find((x) => x.section === sec);
    if (!g) {
      g = { section: sec, items: [] };
      groups.push(g);
    }
    g.items.push(f);
  }
  return groups;
}

@Component({
  selector: 'app-form-fill',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, ButtonModule, InputMaskModule],
  template: `
    @if (loading()) {
      <div class="form-loading">
        <div class="wtn-spinner"></div>
        <span>Carregando formulário...</span>
      </div>
    } @else if (!assignment()) {
      <div class="wtn-empty">
        <div class="wtn-empty-icon">
          <span class="pi pi-file-edit"></span>
        </div>
        <div class="wtn-empty-title">Formulário não encontrado</div>
        <div class="wtn-empty-desc">Verifique a atribuição ou volte para a lista de formulários.</div>
        <p-button label="Voltar" severity="secondary" (onClick)="goBack()" />
      </div>
    } @else {
      <header class="wtn-page-header fill-page-header">
        <div>
          <div class="fill-title-line">
            <h1 class="wtn-page-title">{{ assignment()!.title }}</h1>
            <span [class]="'wtn-tag ' + statusClass(assignment()!.status)">
              {{ statusLabel(assignment()!.status) }}
            </span>
            @if (assignment()!.overdue) {
              <span class="overdue-badge">Atrasado</span>
            }
          </div>
          <p class="wtn-page-desc">
            Atribuído a {{ respondentLabel() }} · prazo {{ deadlineLabel() }} · {{ channelLabel() }}
          </p>
        </div>
        <div class="wtn-page-actions">
          <p-button
            label="Salvar rascunho"
            severity="secondary"
            (onClick)="saveAnswers()"
            [disabled]="saving() || !canEdit()"
          />
        </div>
      </header>

      <section class="workflow-card" aria-label="Ciclo de vida do formulário">
        @for (step of workflowSteps; track step.key) {
          <div class="workflow-step" [class]="stepState(step.key)">
            <div class="step-dot">
              @if (stepState(step.key) === 'done') {
                <span>✓</span>
              }
            </div>
            @if (!$last) {
              <div class="step-line"></div>
            }
            <div class="step-label">{{ step.label }}</div>
          </div>
        }
      </section>

      @if (assignment()!.status === 'pending') {
        <section class="claim-card">
          <h2>Este formulário está pendente</h2>
          @if (assignment()!.instructions) {
            <p>{{ assignment()!.instructions }}</p>
          } @else {
            <p>Assuma a atribuição para iniciar o preenchimento e liberar o rascunho.</p>
          }
          <p-button label="Assumir formulário" icon="pi pi-play" (onClick)="claim()" [disabled]="saving()" />
        </section>
      } @else {
        <section class="fill-grid">
          <article class="form-section-card">
            @for (group of groups(); track group.section) {
              <section class="field-section">
                <div class="section-title">
                  {{ group.section || 'Seção do formulário' }}
                </div>
                <div class="fields-stack">
                  @for (field of group.items; track field.key) {
                    <div class="field-row">
                      <label>
                        {{ field.label }}
                        @if (field.required) { <span class="req">*</span> }
                      </label>

                      @switch (field.type) {
                        @case ('boolean') {
                          <div class="segmented-options">
                            <button
                              type="button"
                              [class.selected]="answers()[field.key] === true"
                              [disabled]="!canEdit()"
                              (click)="setAnswer(field.key, true)"
                            >Sim</button>
                            <button
                              type="button"
                              [class.selected]="answers()[field.key] === false"
                              [disabled]="!canEdit()"
                              (click)="setAnswer(field.key, false)"
                            >Não</button>
                          </div>
                        }
                        @case ('number') {
                          <input type="number" [(ngModel)]="answers()[field.key]" [disabled]="!canEdit()" />
                        }
                        @case ('textarea') {
                          <textarea rows="3" [(ngModel)]="answers()[field.key]" [disabled]="!canEdit()"></textarea>
                        }
                        @case ('select') {
                          <div class="segmented-options segmented-options--wrap">
                            @for (opt of (field.options ?? []); track opt) {
                              <button
                                type="button"
                                [class.selected]="answers()[field.key] === opt"
                                [disabled]="!canEdit()"
                                (click)="setAnswer(field.key, opt)"
                              >{{ opt }}</button>
                            }
                          </div>
                        }
                        @case ('text') {
                          @if (field.mask) {
                            <p-inputmask
                              [mask]="field.mask"
                              [(ngModel)]="answers()[field.key]"
                              [disabled]="!canEdit()"
                            />
                          } @else {
                            <input type="text" [(ngModel)]="answers()[field.key]" [disabled]="!canEdit()" />
                          }
                        }
                        @default {
                          <input type="text" [(ngModel)]="answers()[field.key]" [disabled]="!canEdit()" />
                        }
                      }

                      @if (field.help_text) {
                        <small class="help">{{ field.help_text }}</small>
                      }
                    </div>
                  }
                </div>
              </section>
            }

            <div class="form-footer-actions">
              <p-button label="Salvar rascunho" severity="secondary" (onClick)="saveAnswers()" [disabled]="saving() || !canEdit()" />
              @if (assignment()!.status === 'in_progress') {
                <p-button label="Enviar" (onClick)="submit()" [disabled]="saving()" />
              }
              <p-button label="Voltar" severity="secondary" (onClick)="goBack()" />
            </div>
          </article>

          <aside class="signature-stack">
            <section class="signature-card">
              <div class="signature-title">
                <div class="signature-icon">
                  <span class="pi pi-shield"></span>
                </div>
                <h2>Assinatura eletrônica avançada</h2>
              </div>

              <div class="signature-checks">
                <div class="signature-check" [class.complete]="identityVerified()">
                  <span class="check-dot">✓</span>
                  <div>
                    <strong>Identidade verificada</strong>
                    <span>{{ identityLabel() }}</span>
                  </div>
                </div>
                <div class="signature-check" [class.complete]="timestamped()">
                  <span class="check-dot">✓</span>
                  <div>
                    <strong>Carimbo de tempo</strong>
                    <span>{{ timestampLabel() }}</span>
                  </div>
                </div>
                <div class="signature-check" [class.pending]="!sealed()">
                  <span class="check-dot check-dot--pulse"></span>
                  <div>
                    <strong>Selo de integridade</strong>
                    <span>SHA-256 · {{ sealed() ? 'registrado' : 'aguardando' }}</span>
                  </div>
                </div>
              </div>

              <button
                type="button"
                class="sign-button"
                (click)="submit()"
                [disabled]="saving() || assignment()!.status !== 'in_progress'"
              >
                {{ signatureActionLabel() }}
              </button>
            </section>

            <section class="signature-info">
              <span class="pi pi-info-circle"></span>
              <p>Ao assinar, o formulário é selado e não pode mais ser editado. Uma trilha de auditoria é registrada.</p>
            </section>
          </aside>
        </section>
      }
    }
  `,
  styles: `
    :host {
      display: block;
    }

    .form-loading {
      align-items: center;
      background: var(--wtn-card);
      border: 1px solid var(--wtn-border);
      border-radius: var(--wtn-r-lg);
      color: var(--wtn-text-2);
      display: flex;
      gap: 12px;
      padding: 24px;
    }

    .fill-title-line {
      align-items: center;
      display: flex;
      flex-wrap: wrap;
      gap: 9px;
      margin-bottom: 5px;
    }

    .overdue-badge {
      background: var(--wtn-danger-soft);
      border-radius: var(--wtn-r-pill);
      color: var(--wtn-danger);
      font-size: 11px;
      font-weight: 700;
      padding: 3px 9px;
      text-transform: uppercase;
    }

    .workflow-card {
      background: var(--wtn-card);
      border: 1px solid var(--wtn-border);
      border-radius: var(--wtn-r-lg);
      box-shadow: var(--wtn-e1);
      display: flex;
      margin-bottom: 18px;
      padding: 18px 28px;
    }

    .workflow-step {
      flex: 1;
      position: relative;
      text-align: center;
    }

    .step-dot {
      align-items: center;
      background: var(--wtn-surface);
      border: 2px solid var(--wtn-border-strong);
      border-radius: 50%;
      color: #fff;
      display: flex;
      font-size: 12px;
      font-weight: 700;
      height: 24px;
      justify-content: center;
      margin: 0 auto 8px;
      position: relative;
      width: 24px;
      z-index: 1;
    }

    .step-line {
      background: var(--wtn-border-strong);
      height: 2px;
      left: 60%;
      position: absolute;
      right: -40%;
      top: 12px;
    }

    .workflow-step.done .step-dot {
      background: var(--wtn-success);
      border-color: var(--wtn-success);
    }

    .workflow-step.done .step-line {
      background: var(--wtn-success);
    }

    .workflow-step.current .step-dot {
      background: var(--wtn-primary);
      border-color: var(--wtn-primary);
      box-shadow: 0 0 0 4px var(--wtn-primary-soft);
    }

    .workflow-step.current .step-line {
      background: var(--wtn-border-strong);
    }

    .step-label {
      color: var(--wtn-muted);
      font-size: 11.5px;
      font-weight: 500;
    }

    .workflow-step.done .step-label {
      color: var(--wtn-text);
      font-weight: 600;
    }

    .workflow-step.current .step-label {
      color: var(--wtn-primary);
      font-weight: 700;
    }

    .claim-card,
    .form-section-card,
    .signature-card {
      background: var(--wtn-card);
      border: 1px solid var(--wtn-border);
      border-radius: var(--wtn-r-lg);
      box-shadow: var(--wtn-e1);
    }

    .claim-card {
      padding: 24px;
    }

    .claim-card h2 {
      color: var(--wtn-text);
      font-size: 17px;
      margin: 0 0 8px;
    }

    .claim-card p {
      color: var(--wtn-text-2);
      margin: 0 0 18px;
    }

    .fill-grid {
      align-items: start;
      display: grid;
      gap: 18px;
      grid-template-columns: minmax(0, 1fr) 360px;
    }

    .form-section-card {
      padding: 24px;
    }

    .field-section + .field-section {
      margin-top: 24px;
    }

    .section-title {
      border-bottom: 1px solid var(--wtn-surface-2);
      color: var(--wtn-muted);
      font-size: 11px;
      font-weight: 600;
      letter-spacing: .06em;
      margin-bottom: 16px;
      padding-bottom: 12px;
      text-transform: uppercase;
    }

    .fields-stack {
      display: flex;
      flex-direction: column;
      gap: 18px;
    }

    .field-row {
      display: flex;
      flex-direction: column;
      gap: 7px;
    }

    .field-row label {
      color: var(--wtn-text);
      font-size: 13px;
      font-weight: 600;
    }

    .req {
      color: var(--wtn-danger);
      margin-left: 2px;
    }

    .field-row input,
    .field-row textarea,
    .field-row select {
      background: var(--wtn-surface);
      border: 1px solid var(--wtn-border-strong);
      border-radius: var(--wtn-r-md);
      color: var(--wtn-text);
      font: inherit;
      font-size: 13.5px;
      padding: 9px 12px;
      width: 100%;
    }

    .field-row textarea {
      resize: vertical;
    }

    .field-row input:focus,
    .field-row textarea:focus,
    .field-row select:focus {
      border-color: var(--wtn-focus);
      box-shadow: 0 0 0 3px color-mix(in srgb, var(--wtn-focus) 26%, transparent);
      outline: 0;
    }

    .field-row input:disabled,
    .field-row textarea:disabled,
    .segmented-options button:disabled {
      cursor: not-allowed;
      opacity: .68;
    }

    .help {
      color: var(--wtn-muted);
      font-size: 11.5px;
    }

    .segmented-options {
      display: flex;
      gap: 8px;
    }

    .segmented-options--wrap {
      flex-wrap: wrap;
    }

    .segmented-options button {
      background: var(--wtn-surface);
      border: 1px solid var(--wtn-border-strong);
      border-radius: var(--wtn-r-md);
      color: var(--wtn-text-2);
      cursor: pointer;
      flex: 1;
      font: inherit;
      font-size: 12.5px;
      min-height: 34px;
      min-width: 120px;
      padding: 8px 10px;
      text-align: center;
    }

    .segmented-options button.selected {
      background: var(--wtn-primary-soft);
      border-color: var(--wtn-primary);
      color: var(--wtn-primary);
      font-weight: 700;
    }

    .form-footer-actions {
      border-top: 1px solid var(--wtn-surface-2);
      display: flex;
      flex-wrap: wrap;
      gap: 9px;
      margin-top: 22px;
      padding-top: 16px;
    }

    .signature-stack {
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .signature-card {
      padding: 20px;
    }

    .signature-title {
      align-items: center;
      display: flex;
      gap: 9px;
      margin-bottom: 14px;
    }

    .signature-icon {
      align-items: center;
      background: var(--wtn-primary-soft);
      border-radius: 8px;
      color: var(--wtn-primary);
      display: flex;
      height: 30px;
      justify-content: center;
      width: 30px;
    }

    .signature-title h2 {
      color: var(--wtn-text);
      font-size: 14px;
      font-weight: 700;
      margin: 0;
    }

    .signature-checks {
      display: flex;
      flex-direction: column;
      gap: 11px;
      margin-bottom: 16px;
    }

    .signature-check {
      align-items: center;
      display: flex;
      gap: 10px;
    }

    .check-dot {
      align-items: center;
      background: var(--wtn-neutral);
      border-radius: 50%;
      color: var(--wtn-primary-contrast);
      display: flex;
      flex: none;
      font-size: 11px;
      font-weight: 700;
      height: 20px;
      justify-content: center;
      width: 20px;
    }

    .signature-check.complete .check-dot {
      background: var(--wtn-success);
    }

    .signature-check.pending .check-dot {
      background: var(--wtn-primary);
      box-shadow: 0 0 0 3px var(--wtn-primary-soft);
      color: transparent;
    }

    .signature-check strong {
      color: var(--wtn-text);
      display: block;
      font-size: 12.5px;
      font-weight: 600;
    }

    .signature-check span:last-child {
      color: var(--wtn-muted);
      display: block;
      font-family: var(--wtn-font-mono);
      font-size: 11px;
      margin-top: 2px;
    }

    .sign-button {
      background: var(--wtn-primary);
      border: 0;
      border-radius: var(--wtn-r-md);
      color: var(--wtn-primary-contrast);
      cursor: pointer;
      font: inherit;
      font-size: 13.5px;
      font-weight: 700;
      padding: 11px;
      width: 100%;
    }

    .sign-button:hover:not(:disabled) {
      background: var(--wtn-primary-hover);
    }

    .sign-button:disabled {
      cursor: not-allowed;
      opacity: .6;
    }

    .signature-info {
      align-items: flex-start;
      background: var(--wtn-info-soft);
      border-radius: var(--wtn-r-md);
      color: var(--wtn-info);
      display: flex;
      gap: 9px;
      padding: 13px 15px;
    }

    .signature-info p {
      font-size: 11.5px;
      line-height: 1.5;
      margin: 0;
    }

    @media (max-width: 980px) {
      .workflow-card {
        overflow-x: auto;
      }

      .workflow-step {
        min-width: 120px;
      }

      .fill-grid {
        grid-template-columns: 1fr;
      }
    }
  `,
})
export class FormFillPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly messages = inject(MessageService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  protected readonly assignment = signal<FormAssignment | null>(null);
  protected readonly loading = signal(true);
  protected readonly saving = signal(false);
  protected readonly fields = signal<FormField[]>([]);
  protected readonly answers = signal<Record<string, unknown>>({});
  protected readonly groups = computed(() => groupFields(this.fields()));
  protected readonly workflowSteps = WORKFLOW_STEPS;

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) {
      this.loading.set(false);
      return;
    }
    this.api.getAssignment(id).subscribe({
      next: (a) => {
        this.assignment.set(a);
        this.fields.set(a.fields_snapshot);
        this.answers.set({ ...a.answers });
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  protected statusLabel(s: AssignmentStatus): string {
    return STATUS_LABELS[s];
  }

  protected statusClass(s: AssignmentStatus): string {
    return STATUS_CLASSES[s];
  }

  protected canEdit(): boolean {
    return this.assignment()?.status === 'in_progress';
  }

  protected respondentLabel(): string {
    const a = this.assignment();
    if (!a) return '—';
    return a.respondent_email ?? a.respondent_user_id ?? 'membro';
  }

  protected channelLabel(): string {
    const a = this.assignment();
    return a?.respondent_email ? 'respondente externo via token' : 'membro da organização';
  }

  protected deadlineLabel(): string {
    const deadline = this.assignment()?.deadline_at;
    if (!deadline) return 'sem prazo';
    return this.formatDate(deadline);
  }

  protected stepState(step: AssignmentStatus): 'done' | 'current' | 'todo' {
    const status = this.assignment()?.status ?? 'pending';
    const currentIndex = this.stepIndex(status);
    const stepIndex = this.stepIndex(step);
    if (stepIndex < currentIndex) return 'done';
    if (stepIndex === currentIndex) return 'current';
    return 'todo';
  }

  protected identityVerified(): boolean {
    const status = this.assignment()?.status;
    return status === 'signed' || status === 'completed';
  }

  protected timestamped(): boolean {
    const status = this.assignment()?.status;
    return status === 'signed' || status === 'completed';
  }

  protected sealed(): boolean {
    const status = this.assignment()?.status;
    return status === 'signed' || status === 'completed';
  }

  protected identityLabel(): string {
    return this.identityVerified() ? `OTP confirmado · ${this.respondentLabel()}` : 'OTP pendente';
  }

  protected timestampLabel(): string {
    const signedAt = this.assignment()?.signed_at;
    return signedAt ? `${this.formatDateTime(signedAt)} BRT` : 'aguardando';
  }

  protected signatureActionLabel(): string {
    const status = this.assignment()?.status;
    if (status === 'in_progress') return 'Assinar e enviar';
    if (status === 'submitted') return 'Enviado para assinatura';
    if (status === 'signed' || status === 'completed') return 'Assinado';
    return 'Assumir para preencher';
  }

  protected setAnswer(key: string, value: unknown): void {
    if (!this.canEdit()) return;
    this.answers.update((current) => ({ ...current, [key]: value }));
  }

  protected claim(): void {
    const id = this.assignment()!.id;
    this.saving.set(true);
    this.api.claimAssignment(id).subscribe({
      next: (a) => {
        this.assignment.set(a);
        this.saving.set(false);
      },
      error: () => this.saving.set(false),
    });
  }

  protected saveAnswers(): void {
    const assignment = this.assignment();
    if (!assignment || !this.canEdit()) return;
    this.saving.set(true);
    this.api.saveAnswers(assignment.id, this.answers()).subscribe({
      next: (a) => {
        this.assignment.set(a);
        this.saving.set(false);
        this.messages.add({ severity: 'success', summary: 'Rascunho salvo', life: 2500 });
      },
      error: () => this.saving.set(false),
    });
  }

  protected submit(): void {
    const assignment = this.assignment();
    if (!assignment || assignment.status !== 'in_progress') return;
    this.saving.set(true);
    this.api.saveAnswers(assignment.id, this.answers()).subscribe({
      next: () => {
        this.api.submitAssignment(assignment.id).subscribe({
          next: (a) => {
            this.assignment.set(a);
            this.saving.set(false);
            this.messages.add({ severity: 'success', summary: 'Formulário enviado!', life: 4000 });
          },
          error: (err) => {
            this.saving.set(false);
            const detail = err?.error?.detail ?? 'Verifique os campos obrigatórios.';
            this.messages.add({ severity: 'error', summary: 'Erro ao enviar', detail, life: 5000 });
          },
        });
      },
      error: () => this.saving.set(false),
    });
  }

  protected goBack(): void {
    void this.router.navigate(['/app', 'form-assignments']);
  }

  private stepIndex(status: AssignmentStatus): number {
    if (status === 'cancelled') return 0;
    const index = WORKFLOW_STEPS.findIndex((step) => step.key === status);
    return index >= 0 ? index : 0;
  }

  private formatDate(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value.slice(0, 10);
    return new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit' }).format(date);
  }

  private formatDateTime(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value.slice(0, 16);
    return new Intl.DateTimeFormat('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  }
}
