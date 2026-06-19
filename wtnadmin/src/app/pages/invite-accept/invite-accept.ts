import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { map } from 'rxjs';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { PasswordModule } from 'primeng/password';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';

@Component({
  selector: 'app-invite-accept',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    CardModule,
    ButtonModule,
    InputTextModule,
    PasswordModule,
    MessageModule,
  ],
  template: `
    <div class="centered">
      <p-card header="Aceitar convite" styleClass="auth-card">
        <form [formGroup]="form" (ngSubmit)="submit()" class="auth-form">
          <label for="name">Nome completo</label>
          <input pInputText id="name" formControlName="fullName" />

          <label for="password">Defina sua senha (mín. 12 caracteres)</label>
          <p-password inputId="password" formControlName="password" [toggleMask]="true" />

          @if (error()) {
            <p-message severity="error" [text]="error()!" />
          }

          <p-button type="submit" label="Aceitar e entrar" [disabled]="loading()" styleClass="w-full" />
        </form>
      </p-card>
    </div>
  `,
  styles: `
    .centered { display: flex; justify-content: center; padding: 3rem 1rem; }
    .auth-form { display: flex; flex-direction: column; gap: 0.75rem; min-width: 18rem; }
  `,
})
export class InviteAccept {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly api = inject(ApiService);
  private readonly store = inject(AuthStore);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  private readonly token = toSignal(
    this.route.queryParamMap.pipe(map((p) => p.get('token') ?? '')),
    { initialValue: '' },
  );

  protected readonly form = this.fb.group({
    fullName: this.fb.control('', [Validators.required]),
    password: this.fb.control('', [Validators.required, Validators.minLength(12)]),
  });

  protected submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const token = this.token();
    if (!token) {
      this.error.set('Convite inválido.');
      return;
    }
    this.loading.set(true);
    this.error.set(null);
    const { fullName, password } = this.form.getRawValue();
    this.api.acceptInvite(token, fullName, password).subscribe({
      next: (res) => {
        this.store.setToken(res.access_token);
        this.api.me().subscribe({
          next: (me) => {
            this.store.setMe(me);
            this.loading.set(false);
            void this.router.navigateByUrl('/app');
          },
          error: () => {
            this.loading.set(false);
            void this.router.navigateByUrl('/login');
          },
        });
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Convite inválido, expirado ou já utilizado.');
      },
    });
  }
}
