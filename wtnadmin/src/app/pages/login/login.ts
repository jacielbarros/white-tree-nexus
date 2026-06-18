import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { PasswordModule } from 'primeng/password';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';

@Component({
  selector: 'app-login',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    CardModule,
    ButtonModule,
    InputTextModule,
    PasswordModule,
    MessageModule,
  ],
  template: `
    <div class="centered">
      <p-card header="White Tree Nexus" styleClass="auth-card">
        <form [formGroup]="form" (ngSubmit)="submit()" class="auth-form">
          <label for="email">E-mail</label>
          <input pInputText id="email" type="email" formControlName="email" autocomplete="username" />

          <label for="password">Senha</label>
          <p-password
            inputId="password"
            formControlName="password"
            [feedback]="false"
            [toggleMask]="true"
            autocomplete="current-password"
          />

          @if (error()) {
            <p-message severity="error" [text]="error()!" />
          }

          <p-button type="submit" label="Entrar" [disabled]="loading()" styleClass="w-full" />
          <a routerLink="/forgot" class="muted-link">Esqueci minha senha</a>
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
export class Login {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly api = inject(ApiService);
  private readonly store = inject(AuthStore);
  private readonly router = inject(Router);

  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly form = this.fb.group({
    email: this.fb.control('', [Validators.required, Validators.email]),
    password: this.fb.control('', Validators.required),
  });

  protected submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.loading.set(true);
    this.error.set(null);
    const { email, password } = this.form.getRawValue();

    this.api.login(email, password).subscribe({
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
            this.error.set('Não foi possível carregar o perfil.');
          },
        });
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Credenciais inválidas.');
      },
    });
  }
}
