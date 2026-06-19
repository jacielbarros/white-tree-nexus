import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { map } from 'rxjs';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { MessageModule } from 'primeng/message';
import { PasswordModule } from 'primeng/password';

import { ApiService } from '@app/core/api.service';

@Component({
  selector: 'app-reset-password',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, RouterLink, CardModule, ButtonModule, PasswordModule, MessageModule],
  template: `
    <div class="centered">
      <p-card header="Definir nova senha" styleClass="auth-card">
        <form [formGroup]="form" (ngSubmit)="submit()" class="auth-form">
          <label for="password">Nova senha (mín. 12 caracteres)</label>
          <p-password inputId="password" formControlName="password" [toggleMask]="true" />

          @if (error()) {
            <p-message severity="error" [text]="error()!" />
          }

          <p-button type="submit" label="Redefinir" [disabled]="loading()" styleClass="w-full" />
          <a routerLink="/login" class="muted-link">Voltar ao login</a>
        </form>
      </p-card>
    </div>
  `,
  styles: `
    .centered { display: flex; justify-content: center; padding: 3rem 1rem; }
    .auth-form { display: flex; flex-direction: column; gap: 0.75rem; min-width: 18rem; }
    .muted-link { font-size: 0.85rem; }
  `,
})
export class ResetPassword {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly api = inject(ApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  private readonly token = toSignal(
    this.route.queryParamMap.pipe(map((p) => p.get('token') ?? '')),
    { initialValue: '' },
  );

  protected readonly form = this.fb.group({
    password: this.fb.control('', [Validators.required, Validators.minLength(12)]),
  });

  protected submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const token = this.token();
    if (!token) {
      this.error.set('Token de redefinição ausente ou inválido.');
      return;
    }
    this.loading.set(true);
    this.error.set(null);
    this.api.resetPassword(token, this.form.getRawValue().password).subscribe({
      next: () => {
        this.loading.set(false);
        void this.router.navigateByUrl('/login');
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Token inválido ou expirado.');
      },
    });
  }
}
