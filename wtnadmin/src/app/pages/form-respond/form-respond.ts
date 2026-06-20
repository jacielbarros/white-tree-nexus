import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { InputMaskModule } from 'primeng/inputmask';
import { TagModule } from 'primeng/tag';

import { ApiService } from '@app/core/api.service';
import { AssignmentStatus, FormAssignment, FormField } from '@app/core/models';
import { groupFields } from '@app/pages/form-fill/form-fill';

type Stage = 'loading' | 'error' | 'claim' | 'fill' | 'sign_otp' | 'done';

const STATUS_LABELS: Record<AssignmentStatus, string> = {
  pending: 'Aguardando',
  in_progress: 'Em preenchimento',
  submitted: 'Preenchido',
  signed: 'Assinado',
  completed: 'Concluído',
  cancelled: 'Cancelado',
};

@Component({
  selector: 'app-form-respond',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, CardModule, ButtonModule, TagModule, InputMaskModule],
  template: `
    <div class="respond-wrap">
      @switch (stage()) {
        @case ('loading') {
          <p-card><p class="hint">Carregando formulário...</p></p-card>
        }
        @case ('error') {
          <p-card>
            <h3>Link inválido ou expirado</h3>
            <p class="hint">Verifique o link recebido por e-mail ou entre em contato com quem o enviou.</p>
          </p-card>
        }
        @case ('claim') {
          <p-card>
            <h2>{{ assignment()!.title }}</h2>
            @if (assignment()!.instructions) {
              <p class="instructions">{{ assignment()!.instructions }}</p>
            }
            <p>Clique em "Começar" para iniciar o preenchimento deste formulário.</p>
            <p-button label="Começar" (onClick)="claim()" [disabled]="busy()" />
          </p-card>
        }
        @case ('fill') {
          <p-card>
            <div class="fill-header">
              <h2>{{ assignment()!.title }}</h2>
              <p-tag [value]="statusLabel(assignment()!.status)" />
            </div>
            @if (assignment()!.instructions) {
              <p class="instructions">{{ assignment()!.instructions }}</p>
            }

            @for (group of groups(); track group.section) {
              @if (group.section) { <h3 class="section-h">{{ group.section }}</h3> }
              @for (field of group.items; track field.key) {
                <div class="field-row">
                  <label>
                    {{ field.label }}
                    @if (field.required) { <span class="req">*</span> }
                  </label>
                  @switch (field.type) {
                    @case ('boolean') {
                      <div class="radio-row">
                        <label class="opt"><input type="radio" [name]="field.key" [value]="true" [(ngModel)]="answers()[field.key]" /> Sim</label>
                        <label class="opt"><input type="radio" [name]="field.key" [value]="false" [(ngModel)]="answers()[field.key]" /> Não</label>
                      </div>
                    }
                    @case ('number') {
                      <input type="number" [(ngModel)]="answers()[field.key]" />
                    }
                    @case ('textarea') {
                      <textarea rows="3" [(ngModel)]="answers()[field.key]"></textarea>
                    }
                    @case ('select') {
                      <select [(ngModel)]="answers()[field.key]">
                        <option value="">— Selecione —</option>
                        @for (opt of (field.options ?? []); track opt) {
                          <option [value]="opt">{{ opt }}</option>
                        }
                      </select>
                    }
                    @case ('text') {
                      @if (field.mask) {
                        <p-inputmask [mask]="field.mask" [(ngModel)]="answers()[field.key]" />
                      } @else {
                        <input type="text" [(ngModel)]="answers()[field.key]" />
                      }
                    }
                    @default {
                      <input type="text" [(ngModel)]="answers()[field.key]" />
                    }
                  }
                  @if (field.help_text) { <small class="help">{{ field.help_text }}</small> }
                </div>
              }
            }

            <div class="actions footer">
              <p-button label="Salvar rascunho" severity="secondary" (onClick)="saveAnswers()" [disabled]="busy()" />
              <p-button label="Enviar" (onClick)="submit()" [disabled]="busy()" />
            </div>
          </p-card>
        }
        @case ('sign_otp') {
          <p-card>
            <h2>Assinar formulário</h2>
            <p>
              Para concluir, assine eletronicamente (Lei nº 14.063/2020, nível avançada).
              Um código de verificação (OTP) será enviado ao seu e-mail.
            </p>

            @if (!otpSent()) {
              <div class="field-row">
                <label>Seu nome completo</label>
                <input type="text" [(ngModel)]="signerName" placeholder="Nome como aparecerá na assinatura" />
              </div>
              <p-button label="Enviar código de verificação" (onClick)="requestOtp()" [disabled]="busy() || !signerName.trim()" />
            } @else {
              <p class="hint">Código enviado para seu e-mail. Verifique a caixa de entrada.</p>
              <div class="field-row">
                <label>Código de verificação (6 dígitos)</label>
                <input type="text" [(ngModel)]="otpCode" placeholder="123456" maxlength="6" />
              </div>
              <div class="actions">
                <p-button label="Confirmar assinatura" (onClick)="signWithOtp()" [disabled]="busy() || otpCode.length !== 6" />
                <p-button label="Reenviar código" severity="secondary" (onClick)="requestOtp()" [disabled]="busy()" />
              </div>
            }
          </p-card>
        }
        @case ('done') {
          <p-card>
            <h2>✓ Formulário concluído</h2>
            <p>
              Obrigado! Seu formulário foi {{ assignment()!.status === 'signed' ? 'assinado' : 'concluído' }}
              com sucesso.
            </p>
            @if (contentHash()) {
              <p class="hash-info">
                Selo de integridade (SHA-256):<br />
                <code>{{ contentHash() }}</code>
              </p>
            }
          </p-card>
        }
      }
    </div>
  `,
  styles: `
    .respond-wrap { max-width: 680px; margin: 3rem auto; padding: 0 1rem; }
    h2 { margin-top: 0; }
    .section-h { margin: 1rem 0 0.5rem; font-size: 1rem; border-bottom: 1px solid var(--p-content-border-color, #3a3a3a); padding-bottom: 0.3rem; }
    .fill-header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem; }
    .fill-header h2 { margin: 0; flex: 1; }
    .instructions { opacity: 0.8; font-size: 0.9rem; font-style: italic; border-left: 3px solid var(--p-content-border-color, #444); padding-left: 0.75rem; margin-bottom: 1rem; }
    .field-row { display: flex; flex-direction: column; gap: 0.3rem; margin-bottom: 0.9rem; }
    .field-row label { font-size: 0.88rem; font-weight: 600; opacity: 0.85; }
    .req { color: #e74c3c; margin-left: 0.2rem; }
    .radio-row { display: flex; gap: 1.25rem; }
    .radio-row .opt { display: flex; align-items: center; gap: 0.4rem; font-weight: 400; }
    .help { opacity: 0.6; font-size: 0.8rem; font-weight: 400; }
    input[type='text'], input[type='number'], textarea, select {
      width: 100%; background: var(--p-content-background, #1e1e1e);
      border: 1px solid var(--p-content-border-color, #444); border-radius: 6px;
      padding: 0.4rem 0.55rem; font: inherit; color: inherit;
    }
    input[type='radio'] { width: 1.05rem; height: 1.05rem; }
    .actions { display: flex; gap: 0.5rem; margin-top: 0.5rem; flex-wrap: wrap; }
    .actions.footer { border-top: 1px solid var(--p-content-border-color, #333); padding-top: 0.75rem; margin-top: 1rem; }
    .hint { opacity: 0.75; font-style: italic; }
    .hash-info { font-size: 0.82rem; opacity: 0.7; margin-top: 1rem; }
    .hash-info code { font-family: monospace; word-break: break-all; }
  `,
})
export class FormRespondPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly messages = inject(MessageService);
  private readonly route = inject(ActivatedRoute);

  private token = '';

  protected readonly stage = signal<Stage>('loading');
  protected readonly assignment = signal<FormAssignment | null>(null);
  protected readonly fields = signal<FormField[]>([]);
  protected readonly answers = signal<Record<string, unknown>>({});
  protected readonly busy = signal(false);
  protected readonly otpSent = signal(false);
  protected readonly contentHash = signal('');
  protected readonly groups = computed(() => groupFields(this.fields()));

  protected signerName = '';
  protected otpCode = '';

  ngOnInit(): void {
    this.token = this.route.snapshot.paramMap.get('token') ?? '';
    if (!this.token) { this.stage.set('error'); return; }

    this.api.getFormByToken(this.token).subscribe({
      next: (a) => {
        this.assignment.set(a);
        this.fields.set(a.fields_snapshot);
        this.answers.set({ ...a.answers });
        this.stage.set(this.deriveStage(a));
      },
      error: (err) => {
        this.stage.set('error');
        if (err?.status === 410) {
          this.messages.add({ severity: 'error', summary: 'Link expirado', life: 5000 });
        }
      },
    });
  }

  private deriveStage(a: FormAssignment): Stage {
    if (['signed', 'completed', 'cancelled'].includes(a.status)) return 'done';
    if (a.status === 'submitted') return 'sign_otp';
    if (a.status === 'pending') return 'claim';
    return 'fill';
  }

  protected statusLabel(s: AssignmentStatus): string { return STATUS_LABELS[s]; }

  protected claim(): void {
    this.busy.set(true);
    this.api.claimByToken(this.token).subscribe({
      next: (a) => { this.assignment.set(a); this.busy.set(false); this.stage.set('fill'); },
      error: () => this.busy.set(false),
    });
  }

  protected saveAnswers(): void {
    this.busy.set(true);
    this.api.saveAnswersByToken(this.token, this.answers()).subscribe({
      next: (a) => {
        this.assignment.set(a);
        this.busy.set(false);
        this.messages.add({ severity: 'success', summary: 'Rascunho salvo', life: 2500 });
      },
      error: () => this.busy.set(false),
    });
  }

  protected submit(): void {
    this.busy.set(true);
    this.api.saveAnswersByToken(this.token, this.answers()).subscribe({
      next: () => {
        this.api.submitByToken(this.token).subscribe({
          next: (a) => {
            this.assignment.set(a);
            this.busy.set(false);
            this.stage.set('sign_otp');
          },
          error: (err) => {
            this.busy.set(false);
            const detail = err?.error?.detail ?? 'Verifique os campos obrigatórios.';
            this.messages.add({ severity: 'error', summary: 'Erro ao enviar', detail, life: 5000 });
          },
        });
      },
      error: () => this.busy.set(false),
    });
  }

  protected requestOtp(): void {
    this.busy.set(true);
    this.api.requestOtpByToken(this.token).subscribe({
      next: () => { this.otpSent.set(true); this.busy.set(false); },
      error: (err) => {
        this.busy.set(false);
        const detail = err?.status === 503
          ? 'Não foi possível enviar o código. Tente novamente.'
          : 'Erro ao solicitar código de verificação.';
        this.messages.add({ severity: 'error', summary: 'Erro', detail, life: 5000 });
      },
    });
  }

  protected signWithOtp(): void {
    this.busy.set(true);
    this.api.signByToken(this.token, this.otpCode, this.signerName).subscribe({
      next: (sig) => {
        this.contentHash.set(sig.content_hash);
        this.busy.set(false);
        this.stage.set('done');
        this.messages.add({ severity: 'success', summary: 'Formulário assinado com sucesso!', life: 5000 });
      },
      error: (err) => {
        this.busy.set(false);
        const detail = err?.status === 401
          ? 'Código incorreto ou expirado. Solicite um novo código.'
          : 'Erro ao assinar.';
        this.messages.add({ severity: 'error', summary: 'Falha na assinatura', detail, life: 5000 });
        this.otpCode = '';
      },
    });
  }
}
