import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';

import { ApiService } from '@app/core/api.service';

@Component({
  selector: 'app-forgot-password',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, RouterLink, CardModule, ButtonModule, InputTextModule, MessageModule],
  template: `
    <div class="centered">
      <p-card header="Redefinir senha" styleClass="auth-card">
        @if (sent()) {
          <p-message
            severity="success"
            text="Se o e-mail existir, enviaremos instruções de redefinição."
          />
          <a routerLink="/login" class="muted-link">Voltar ao login</a>
        } @else {
          <form [formGroup]="form" (ngSubmit)="submit()" class="auth-form">
            <label for="email">E-mail</label>
            <input pInputText id="email" type="email" formControlName="email" />
            <p-button type="submit" label="Enviar" [disabled]="loading()" styleClass="w-full" />
            <a routerLink="/login" class="muted-link">Voltar ao login</a>
          </form>
        }
      </p-card>
    </div>
  `,
  styles: `
    .centered { display: flex; justify-content: center; padding: 3rem 1rem; }
    .auth-form { display: flex; flex-direction: column; gap: 0.75rem; min-width: 18rem; }
    .muted-link { font-size: 0.85rem; display: inline-block; margin-top: 0.75rem; }
  `,
})
export class ForgotPassword {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly api = inject(ApiService);

  protected readonly loading = signal(false);
  protected readonly sent = signal(false);

  protected readonly form = this.fb.group({
    email: this.fb.control('', [Validators.required, Validators.email]),
  });

  protected submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.loading.set(true);
    // Resposta genérica: sucesso independentemente de o e-mail existir.
    this.api.forgotPassword(this.form.getRawValue().email).subscribe({
      next: () => {
        this.loading.set(false);
        this.sent.set(true);
      },
      error: () => {
        this.loading.set(false);
        this.sent.set(true);
      },
    });
  }
}
